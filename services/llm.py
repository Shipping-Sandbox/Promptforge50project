import json
import os
import urllib.error
import urllib.request

# Groq uses an OpenAI-compatible API.
BASE_URL = os.getenv(
    "LLM_BASE_URL",
    "https://api.groq.com/openai/v1"
).rstrip("/")

# Accept either our app's variable or the conventional Groq variable.
API_KEY = (
    os.getenv("LLM_API_KEY", "").strip()
    or os.getenv("GROQ_API_KEY", "").strip()
)

# Strong general-purpose reasoning model available through Groq.
MODEL = os.getenv(
    "LLM_MODEL",
    "openai/gpt-oss-120b"
)


def llm_configured():
    return bool(API_KEY)


def _call_llm(system_prompt, user_prompt):
    if not llm_configured():
        raise RuntimeError("Groq API key is not configured.")

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
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(
                response.read().decode("utf-8")
            )

    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(
            "utf-8",
            errors="replace"
        )
        raise RuntimeError(
            f"Groq returned HTTP {exc.code}: {detail}"
        ) from exc

    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Could not reach Groq: {exc.reason}"
        ) from exc

    except TimeoutError as exc:
        raise RuntimeError(
            "The Groq request timed out."
        ) from exc

    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(
            "Groq returned an unexpected response."
        ) from exc

    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Groq returned invalid JSON."
        ) from exc


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

        options = item.get("options", [])

        if not isinstance(options, list):
            options = []

        options = [
            str(option).strip()
            for option in options
            if str(option).strip()
        ]

        normalized.append({
            "id": str(
                item.get("id") or f"q{index + 1}"
            ),
            "question": question,
            "hint": str(
                item.get("hint", "")
            ).strip(),
            "options": options[:6],
            "multi": bool(
                item.get("multi", False)
            ),
        })

    return normalized


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

The questions must be tailored to the exact task.

Return JSON only in this format:

{
  "questions": [
    {
      "id": "q1",
      "question": "...",
      "hint": "...",
      "options": [
        "...",
        "...",
        "... "
      ],
      "multi": false
    }
  ]
}

Rules:
- Generate 2 to 5 questions.
- Each question must have 3 to 6 useful options.
- Options must be specific to the user's request.
- Avoid repeating information already present.
- Do NOT add an "Other" option.
- PromptForge adds "Other" automatically as the final option.
- Never reuse a generic questionnaire.
""".strip()

    try:
        result = _call_llm(
            system,
            f"""
EXACT USER REQUEST:

{prompt}

Now identify only the missing decisions that genuinely
matter for completing this specific request.
"""
        )

        questions = _normalize_questions(
            result.get("questions", [])
        )

        if (
            2 <= len(questions) <= 5
            and all(
                len(q["options"]) >= 3
                for q in questions
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
        print(f"Clarifying-question error: {exc}")

        return {
            "available": False,
            "message": (
                "The LLM could not generate the "
                "prompt-specific questions right now."
            ),
            "questions": [],
        }


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

You are given:
1. the user's exact original request,
2. the questions generated specifically for that request,
3. the user's answers.

Your entire response must be specific to THIS request.

Do not produce generic AI advice.

Determine:
- what the user is actually trying to achieve,
- what information matters,
- what the best execution strategy is,
- which tools or AI capabilities are actually needed,
- which tools are unnecessary,
- what should be verified,
- and what the final prompt should say.

Do not recommend tools merely because they are popular.

Every recommended step must have a clear purpose for THIS task.

Use the user's answers as requirements.

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
- pipeline: 1 to 6 steps
- only include genuinely useful steps
- suggested_models must be relevant to this task
- warnings must be specific to this task
- refined_prompt must be directly executable by another AI
- use concrete details from the original request
- do not use vague phrases such as "your project"
  when a specific noun is available
""".strip()

    user_payload = {
        "original_prompt": prompt,
        "clarifying_questions": json.loads(
            questions_json or "[]"
        ),
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
        print(f"Final-plan error: {exc}")

        return {
            "available": False,
            "message": (
                "The LLM could not produce the "
                "task-specific plan right now."
            ),
            "verdict": None,
            "refined_prompt": None,
            "pipeline": [],
            "suggested_models": [],
            "warnings": [],
        }
