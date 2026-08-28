# PromptForge

A small Flask + SQLite application that turns a user's rough request into a task-specific AI workflow.

## Current behavior

When an LLM API key is configured, PromptForge:

1. Receives the user's exact request.
2. Generates 2–5 clarifying questions tailored to that request.
3. Presents Claude-like selectable answer cards plus an `Other` choice with a custom text field.
4. Generates a task-specific verdict, refined prompt, pipeline, model roles, and warnings.
5. Saves the full session in SQLite.

When the LLM API is **not** configured, PromptForge saves the request and clearly tells the user that the clarifying questions and refined prompt with tools pipeline will be available in a few months.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

## Backend configuration

Put the API key only in `.env`:

```env
LLM_API_KEY=your_key_here
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=openai/gpt-oss-120b
```

The browser never receives the API key.


## History isolation

PromptForge assigns each browser a private anonymous user ID in an HTTP-only cookie and stores that ID in SQLite. History and saved sessions are filtered by that user ID, so separate browser users do not see each other’s history. This is intentionally simple for the MVP and is not a full account/authentication system.

## Navigation and user-specific history

The main page has no back button. Once the user enters the clarification/API/result flow, a small floating **Back** button appears at the bottom-left. The history remains in the main page flow rather than competing with that navigation control.

Each browser receives an anonymous, persistent user ID in an HTTP-only cookie. SQLite associates every saved session with that ID, so different users have separate histories. This is lightweight user separation for the MVP; it is not an account/login system.
