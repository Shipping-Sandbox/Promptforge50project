import json
import os
import urllib.error
import urllib.request


# ---------------------------------------------------------
# LLM CONFIGURATION
# ---------------------------------------------------------

# Groq provides an OpenAI-compatible API.
BASE_URL = os.getenv(
    "LLM_BASE_URL",
    "https://api.groq.com/openai/v1"
).rstrip("/")

# Accept either variable name.
API_KEY = (
    os.getenv("LLM_API_KEY", "").strip()
    or os.getenv("GROQ_API_KEY", "").strip()
)

# Default model.
MODEL = os.getenv(
    "LLM_MODEL",
    "openai/gpt-oss-120b"
)


def llm_configured():
    return bool(API_KEY)


# ---------------------------------------------------------
# CORE LLM REQUEST
# ---------------------------------------------------------

def _call_llm(system_prompt, user_prompt):
    if not llm_configured():
        raise RuntimeError(
            "Groq API key is not configured."
        )

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        "temperature": 0.2,
        "response_format": {
            "type": "json_object"
        }
    }

    request = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "PromptForge/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=60
        ) as response:

            body = json.loads(
                response.read().decode("utf-8")
            )

    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(
            "utf-8",
            errors="replace"
        )

        # Print the real provider response into Render logs.
        print(
            f"Groq HTTP {exc.code}: {detail}"
        )

        raise RuntimeError(
            f"Groq returned HTTP {exc.code}: {detail}"
        ) from exc

    except urllib.error.URLError as exc:
        print(
            f"Groq connection error: {exc}"
        )

        raise RuntimeError(
            f"Could not reach Groq: {exc.reason}"
        ) from exc

    except TimeoutError as exc:
        print(
            "Groq request timed out."
        )

        raise RuntimeError(
            "The Groq request timed out."
        ) from exc

    try:
        content = body["choices"][0]["message"]["content"]

    except (
        KeyError,
        IndexError,
        TypeError
    ) as exc:

        print(
            f"Unexpected Groq response: {body}"
        )

        raise RuntimeError(
            "Groq returned an unexpected response."
        ) from exc

    try:
        return json.loads(content)

    except json.JSONDecodeError as exc:

        print(
            f"Groq returned invalid JSON: {content}"
        )

        raise RuntimeError(
            "Groq returned invalid JSON."
        ) from exc


# ---------------------------------------------------------
# QUESTION NORMALIZATION
# ---------------------------------------------------------

def _normalize_questions(questions):
    normalized = []

    for index, item in enumerate(questions):

        if not isinstance(item, dict):
            continue

        question = str(
            item.get("question", "")
        ).strip()

        if not question:
            continue

        options = item.get(
            "options",
            []
        )

        if not isinstance(
            options,
            list
        ):
            options = []

        options = [
            str(option).strip()
            for option in options
            if str(option).strip()
        ]

        normalized.append({
            "id": str(
                item.get(
                    "id",
                    f"q{index + 1}"
                )
            ),
            "question": question,
            "hint": str(
                item.get(
                    "hint",
                    ""
                )
            ).strip(),
            "options": options[:6],
            "multi": bool(
                item.get(
                    "multi",
                    False
                )
            ),
        })

    return normalized


# ---------------------------------------------------------
# CLARIFYING QUESTIONS
# ---------------------------------------------------------

def generate_clarifying_questions(prompt):

    if not llm_configured():
        return {
            "available": False,
            "message": (
                "The clarifying questions and refined prompt "
                "with tools pipeline will be available in a few months."
            ),
            "questions": [],
        }

    system = """
You are PromptForge's task-analysis engine.

Analyze ONLY the user's exact request.

Your job is NOT to ask generic onboarding questions.

Ask only questions whose answers would materially change:
- the final prompt,
- the implementation approach,
- the recommended AI model,
- the required tools,
- the output,
- or the success criteria.

Do not ask about tone, audience, budget, deadline, format,
technology, or anything else unless it actually matters to
THIS specific request.

Every question must be based on the user's exact request.

Do not reuse a generic questionnaire.

Return JSON only:

{
  "questions": [
    {
      "id": "q1",
      "question": "...",
      "hint": "...",
      "options": [
        "...",
        "...",
        "..."
      ],
      "multi": false
    }
  ]
}

Rules:
- Generate 2 to 5 questions.
- Each question must have 3 to 6 useful options.
- Options must be specific to the user's task.
- Do not repeat information already present.
- Do NOT add an "Other" option.
- PromptForge adds "Other" automatically.
- Avoid generic questions.
""".strip()

    try:

        result = _call_llm(
            system,
            f"""
EXACT USER REQUEST:

{prompt}

Identify only the missing decisions that genuinely
matter for completing this exact task.
"""
        )

        questions = _normalize_questions(
            result.get(
                "questions",
                []
            )
        )

        if (
            2 <= len(questions) <= 5
            and all(
                len(question["options"]) >= 3
                for question in questions
            )
        ):
            return {
                "available": True,
                "questions": questions,
            }

        return {
            "available": False,
            "message": (
                "The connected LLM did not return enough "
                "task-specific questions. Please try again."
            ),
            "questions": [],
        }

    except Exception as exc:

        print(
            f"Clarifying-question error: {exc}"
        )

        return {
            "available": False,
            "message": (
                "The LLM could not generate the "
                "prompt-specific questions right now."
            ),
            "questions": [],
        }


# ---------------------------------------------------------
# FINAL PLAN
# ---------------------------------------------------------

def generate_final_plan(
    prompt,
    questions_json,
    answers
):

    if not llm_configured():
        return {
            "available": False,
            "message": (
                "The clarifying questions and refined prompt "
                "with tools pipeline will be available in a few months."
            ),
            "verdict": None,
            "refined_prompt": None,
            "pipeline": [],
            "suggested_models": [],
            "warnings": [],
        }

    system = """
You are PromptForge's final task-planning engine.

You receive:
1. the user's exact original request,
2. the questions generated specifically for that request,
3. the user's answers.

Your response MUST be specific to this exact task.

Do not produce generic AI advice.

Determine:
- what the user is actually trying to achieve,
- what the user's answers imply,
- what the best execution strategy is,
- which AI capabilities are genuinely needed,
- which tools are genuinely useful,
- which tools are unnecessary,
- what should be verified,
- and what the final executable prompt should say.

Do not recommend tools merely because they are popular.

Every pipeline step must have a clear reason for existing.

Use the user's answers as actual requirements.

Return JSON only:

{
  "task_summary": "...",
  "verdict": "...",
  "refined_prompt": "...",
  "pipeline": [
    {
      "step": "1",
      "tool": "...",
      "purpose": "...",
      "when_to_use": "..."
    }
  ],
  "suggested_models": [
    {
      "name": "...",
      "role": "...",
      "reason": "..."
    }
  ],
  "warnings": [
    "..."
  ]
}

Rules:
- pipeline must contain 1 to 6 steps.
- Include only genuinely useful steps.
- suggested_models must be relevant to this exact task.
- warnings must be specific to this task.
- refined_prompt must be directly usable by another AI.
- Use concrete details from the original request.
- Use the user's answers.
- Never fall back to generic advice.
""".strip()

    try:

        clarifying_questions = json.loads(
            questions_json or "[]"
        )

    except json.JSONDecodeError:

        clarifying_questions = []

    user_payload = {
        "original_prompt": prompt,
        "clarifying_questions": clarifying_questions,
        "answers": answers,
    }

    try:

        result = _call_llm(
            system,
            json.dumps(
                user_payload,
                indent=2
            )
        )

        if (
            isinstance(result, dict)
            and result.get("verdict")
            and result.get("refined_prompt")
        ):
            return {
                "available": True,
                **result
            }

        return {
            "available": False,
            "message": (
                "The LLM returned an incomplete "
                "task-specific result. Please try again."
            ),
            "verdict": None,
            "refined_prompt": None,
            "pipeline": [],
            "suggested_models": [],
            "warnings": [],
        }

    except Exception as exc:
        print(
            f"Final-plan error: {exc}"
        )

        return {
            "available": False,
            "message": (
                f"Final plan error: {exc}"
            ),
            "verdict": None,
            "refined_prompt": None,
            "pipeline": [],
            "suggested_models": [],
            "warnings": [],
        }
