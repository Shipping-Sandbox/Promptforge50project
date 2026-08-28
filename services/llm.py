import json
import os
import urllib.error
import urllib.request

BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
API_KEY = os.getenv("LLM_API_KEY", "")
MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")


def llm_configured():
    return bool(API_KEY.strip())


def _call_llm(system_prompt, user_prompt):
    if not llm_configured():
        raise RuntimeError("LLM_API_KEY is not configured")

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM provider returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach LLM provider: {exc.reason}") from exc

    content = body["choices"][0]["message"]["content"]
    return json.loads(content)


def _normalize_questions(questions):
    normalized = []
    for index, item in enumerate(questions):
        if not isinstance(item, dict):
            continue
        question = str(item.get("question", "")).strip()
        if not question:
            continue
        options = item.get("options", [])
        if not isinstance(options, list):
            options = []
        options = [str(option).strip() for option in options if str(option).strip()]
        normalized.append({
            "id": str(item.get("id") or f"q{index + 1}"),
            "question": question,
            "hint": str(item.get("hint", "")).strip(),
            "options": options[:7],
            "multi": bool(item.get("multi", False)),
        })
    return normalized


def generate_clarifying_questions(prompt):
    if not llm_configured():
        return {
            "available": False,
            "message": "Clarifying questions are unavailable because the LLM API is not connected yet.",
            "questions": [],
        }

    system = """
You are PromptForge's first-stage task analyst.

The user has supplied ONE specific request. Your job is to ask only the questions
that materially change the best way to execute THAT request.

Your questions MUST be derived from details, ambiguities, hidden decisions, output
requirements, audience, constraints, technical context, or success criteria found
(or missing) in the user's exact prompt. Never use a generic questionnaire.
Do not ask about audience, tone, format, deadline, tools, etc. unless that specific
information actually matters for this task.

Return JSON only:
{"questions":[...]}

Provide 2 to 5 questions. Each question object must have:
- id
- question
- hint
- options: 3 to 6 concise, mutually useful options tailored to this exact request
- multi: true only when multiple answers legitimately apply

Do NOT include an "Other" option. The application adds "Other" as the final option.
Avoid repeating information already present in the prompt.
""".strip()

    try:
        result = _call_llm(system, f"EXACT USER REQUEST:\n{prompt}")
        questions = _normalize_questions(result.get("questions", []))
        if 2 <= len(questions) <= 5 and all(len(q["options"]) >= 3 for q in questions):
            return {"available": True, "questions": questions}
    except (RuntimeError, json.JSONDecodeError, KeyError, TypeError):
        pass

    return {
        "available": False,
        "message": "Prompt-specific clarifying questions could not be generated. Connect a working LLM API and try again.",
        "questions": [],
    }


def generate_final_plan(prompt, questions_json, answers):
    if not llm_configured():
        return {
            "available": False,
            "message": "Prompt refinement is unavailable because the LLM API is not connected yet.",
            "verdict": None,
            "refined_prompt": None,
            "pipeline": [],
            "suggested_models": [],
            "warnings": [],
        }

    system = """
You are PromptForge's final task-planning engine.

You receive one exact user request plus answers to questions that were generated
specifically for that request. Your output must be specific to THIS request.
Never produce a generic verdict, generic workflow, or reusable boilerplate that
would make equal sense for an unrelated prompt.

Reason about:
1. What the user is actually trying to accomplish.
2. Which parts require reasoning, retrieval/browsing, coding, image/audio work,
   structured generation, domain expertise, or verification.
3. Which steps are unnecessary. Do not recommend multiple AI systems just to look
   sophisticated.
4. What could go wrong for THIS task and how to verify it.
5. Which model category or provider is appropriate for EACH recommended step.

Use the answers—including custom "Other" text—as hard requirements.

Return JSON only with:
- task_summary: 1-2 sentences describing this exact task
- verdict: a specific recommendation explaining the best approach for this request
- refined_prompt: the final prompt tailored to the user's exact goal and answers
- pipeline: 1 to 6 steps, each with step, tool, purpose, and when_to_use
- suggested_models: objects with name, role, and reason; only include models that
  make sense for this exact task
- warnings: task-specific caveats or verification requirements

A strong answer should contain concrete nouns from the user's task, not vague
phrases such as "your project", "the user's goal", or "the task" when specificity
is possible.
""".strip()

    user = {
        "original_prompt": prompt,
        "clarifying_questions": json.loads(questions_json or "[]"),
        "answers": answers,
    }

    try:
        result = _call_llm(system, json.dumps(user, indent=2))
        if isinstance(result, dict) and result.get("verdict") and result.get("refined_prompt"):
            return {"available": True, **result}
    except (RuntimeError, json.JSONDecodeError, KeyError, TypeError):
        pass

    return {
        "available": False,
        "message": "The connected LLM could not produce a reliable prompt-specific result. Try again.",
        "verdict": None,
        "refined_prompt": None,
        "pipeline": [],
        "suggested_models": [],
        "warnings": [],
    }
