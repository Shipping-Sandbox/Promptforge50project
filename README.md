# PromptForge

PromptForge is a web application that helps a user turn a rough idea into a more useful AI task plan.

The user starts with a natural-language request. PromptForge is designed to ask task-specific clarifying questions, use the answers to produce a refined prompt, and recommend a practical pipeline of AI tools for the task.

## Live Demo

**https://promptforge50project.onrender.com**

The deployed application currently demonstrates the core interface and workflow. The LLM-powered clarification and refinement layer is designed so it can be enabled through a backend API when the project is connected to a model provider.

## Problem

People often know what they want an AI to do, but their first prompt leaves out important information.

For example:

> "Make a website that turns PDFs into podcasts."

That describes the idea, but not the requirements that an AI needs to produce a strong result. Important decisions may include the target users, supported PDF types, whether OCR is required, how long the podcast should be, which voices to use, how files should be stored, and how the finished audio should be delivered.

PromptForge addresses this by treating prompting as a small decision process rather than a single text rewrite.

## How It Works

The intended flow is:

```text
Rough Prompt
     |
     v
Task Understanding
     |
     v
Prompt-Specific Questions
     |
     v
User Answers
     |
     v
Refined Prompt
     |
     v
AI / Tool Pipeline
     |
     v
Recommended Execution Plan
```

The important design rule is that the questions and recommendations should depend on the actual prompt. PromptForge should not display the same generic questionnaire for every task.

## Main Features

### 1. Rough prompt input

The user describes the task in their own words.

### 2. Prompt-specific clarification

The backend LLM can generate a small set of questions based on the exact task.

Questions can use selectable answer options, with an **Other** option that allows the user to enter a custom answer.

### 3. Refined prompt

The user's answers are combined with the original request to produce a more precise prompt suitable for the intended work.

### 4. Tool pipeline

PromptForge can recommend a sequence of tools or model capabilities for different stages of the task.

For example:

```text
Extract source
      ↓
Understand / reason
      ↓
Generate
      ↓
Convert / process
      ↓
Store
      ↓
Deploy
```

The recommended pipeline should explain why each step is useful rather than simply listing popular AI tools.

### 5. Demo mode

A built-in demonstration shows a worked example based on a rough request to create a website that turns PDFs into podcasts.

### 6. History

PromptForge stores prompt sessions in SQLite and associates them with an anonymous browser user identifier so different users do not see one another's history.

## Technology

The project intentionally uses a small and understandable stack.

- **Python**
- **Flask**
- **SQLite**
- **HTML**
- **CSS**
- **JavaScript**
- **LLM API integration**
- **GitHub**
- **Render**

No frontend framework is required.

## Project Structure

```text
promptforge/
├── app.py
├── services/
│   ├── __init__.py
│   └── llm.py
├── static/
│   ├── app.js
│   └── style.css
├── templates/
│   └── index.html
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
└── design.md
```

### `app.py`

Contains the Flask application, routes, request handling, user/session identification, and SQLite access.

### `services/llm.py`

Contains the LLM-facing logic. Keeping this separate from the Flask routes makes the application easier to understand and change.

### `templates/index.html`

The main interface rendered by Flask.

### `static/app.js`

Handles client-side interaction such as prompt submission, question selection, demo behavior, history loading, and result display.

### `static/style.css`

Contains the visual design and responsive layout.

## Running Locally

Clone the repository:

```bash
git clone https://github.com/blackirron/promptforge50-project.git
cd promptforge50-project
```

Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
python app.py
```

Then open:

```text
http://127.0.0.1:5000
```

## Environment Variables

Create a `.env` file from `.env.example`.

The LLM integration is intentionally server-side so an API key is not exposed to the browser.

Example:

```env
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=your_model
```

When the LLM API is not configured, the application should not invent questions or pretend that a refined result came from an AI model. The interface instead explains that the clarifying-question, refined-prompt, and tools-pipeline functionality will become available when the API layer is connected.

## Deployment

The current application is deployed on Render:

**https://promptforge50-project.onrender.com/**

Typical Render settings are:

```text
Build Command:
pip install -r requirements.txt

Start Command:
gunicorn app:app
```

The GitHub repository is used as the source for deployment.

## Data Model

The current application uses SQLite because it is simple to understand and appropriate for a small project.

Conceptually, the data looks like:

```text
User
 |
 +-- Prompt Session
       |
       +-- Original prompt
       +-- Clarifying questions
       +-- Answers
       +-- Final result
       +-- Created timestamp
```

The browser receives an anonymous user identifier through a cookie. That identifier is used to associate future sessions with the same user.

## Scope and Simplicity

The project deliberately avoids unnecessary complexity.

It does not require:

- React
- a large frontend framework
- microservices
- a separate authentication platform
- a vector database
- a multi-agent orchestration framework
- a custom model
- a complex cloud infrastructure

The goal is to solve one clear problem with a small full-stack application.

## AI Assistance Disclosure

The README.md and design.md documentation were created with assistance from AI. 

The project itself, including its implementation, structure, and design decisions, was developed and reviewed as part of the project work.

AI assistance was used primarily to help organize, document, and communicate the project clearly.

## Limitations

The current implementation is a prototype.

The most important production limitation is persistence. SQLite is useful for local development and a small application, but a hosted application with durable multi-user history should eventually use a managed database such as PostgreSQL.

The LLM integration is also intentionally isolated so a provider can be connected later without redesigning the whole application.

## Future Improvements

Possible future improvements include:

- real user accounts
- persistent PostgreSQL storage
- multiple LLM providers
- stronger prompt-quality scoring
- more detailed tool selection
- saved/refined prompt versions
- export and sharing
- richer pipeline visualization
- execution of selected pipeline steps

These are deliberately kept outside the minimum core.

## Author

Built as a small full-stack web application focused on improving how people formulate and execute AI tasks.
