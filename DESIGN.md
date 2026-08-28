# PromptForge Design Document

## 1. Overview

PromptForge is designed as a calm, focused interface for turning an incomplete AI request into a clearer execution plan.

The product is based on a simple idea:

> A good AI result often depends on first understanding what the user actually wants.

Instead of asking the user to learn prompt-engineering techniques, PromptForge performs part of that reasoning for them.

## 2. Product Goal

The primary goal is:

**Help a user move from "I know roughly what I want" to "I know exactly what to ask and which AI tools should perform each part."**

The interface should feel more like a thoughtful assistant than a form.

## 3. Core User Flow

```text
                     ┌───────────────────┐
                     │   Rough prompt    │
                     └─────────┬─────────┘
                               |
                               v
                     ┌───────────────────┐
                     │ Understand task   │
                     └─────────┬─────────┘
                               |
                    ┌──────────┴──────────┐
                    |                     |
                    v                     v
             Clarification needed?     No
                    |                     |
                    v                     |
          ┌────────────────────┐          |
          │ Task-specific      │          |
          │ questions          │          |
          └─────────┬──────────┘          |
                    |                     |
                    v                     |
          ┌────────────────────┐          |
          │ User answers       │          |
          └─────────┬──────────┘          |
                    |                     |
                    └──────────┬──────────┘
                               |
                               v
                     ┌───────────────────┐
                     │ Refined prompt    │
                     └─────────┬─────────┘
                               |
                               v
                     ┌───────────────────┐
                     │ Tool / AI plan    │
                     └─────────┬─────────┘
                               |
                               v
                     ┌───────────────────┐
                     │ Final verdict     │
                     └───────────────────┘
```

## 4. Design Principles

### Specific, not generic

Every generated question should be justified by the user's prompt.

For example:

**User prompt**

> Build me a website that converts PDFs into podcasts.

Useful questions might concern:

- PDF length
- scanned vs text PDFs
- desired podcast format
- number of speakers
- voice style
- output formats
- user privacy

A question such as "What is your preferred tone?" should only appear when tone materially affects the task.

### Progressive disclosure

Do not show every possible decision at once.

The interface reveals information in stages:

```text
Prompt
  ↓
Questions
  ↓
Answers
  ↓
Pipeline
  ↓
Details
```

This keeps cognitive load low.

### Explain decisions

A recommendation should not simply say:

> Use Claude.

It should explain:

> Use a reasoning-capable model here because this step converts extracted source material into a coherent conversational structure.

The user should understand the role of every stage.

### Clean visual hierarchy

Primary actions should be visually obvious.

Secondary information should remain quiet until needed.

## 5. Visual Language

PromptForge uses a restrained visual system.

### Background

A warm, slightly off-white background provides separation from pure-white cards without looking like a traditional enterprise dashboard.

### Cards

Cards use:

- large rounded corners
- subtle borders
- very light shadows
- generous padding

The goal is to make the interface feel approachable without creating excessive visual noise.

### Typography

Large headings establish the purpose of each screen.

Body text stays comfortably readable.

Uppercase small labels such as:

```text
PROMPTFORGE
01
02
03
```

act as orientation markers rather than decoration.

## 6. Interaction Model

### Prompt entry

The initial screen contains one dominant input.

The user's attention should immediately go toward:

> What are you trying to accomplish?

The primary action is:

**Analyze my request**

A secondary action allows the user to explore the product through:

**See demo**

### Clarifying questions

Questions appear as selectable cards.

This is intentionally closer to a conversational UI than a traditional HTML form.

Each answer option should feel like a possible decision, not a checkbox from an administration panel.

The last option is:

**Other**

When selected, an inline text field appears.

### Back navigation

The main screen does not display a back button.

After entering the workflow, a small floating back button appears in the lower-left area.

The control stays visually out of the way while still being available during longer scrolling states.

## 7. Demo Design

The demo is a deterministic example and does not require an LLM connection.

Example rough prompt:

> Create a website that turns PDFs into podcasts.

The demo then presents:

1. rough prompt
2. clarification questions
3. example answers
4. refined objective
5. complete tool pipeline

The pipeline uses recognizable tool icons.

Selecting a tool opens its detailed explanation:

```text
Tool
Purpose
Why it is used
Instruction / prompt
Official link
```

The intent is educational: the user should understand not only **what** tool is selected, but **what to ask the tool to do**.

## 8. Pipeline Visualization

A pipeline should read from left to right on wide screens and become vertically stacked on small screens.

Conceptually:

```text
[Input]
   |
   v
[Extract]
   |
   v
[Understand]
   |
   v
[Write]
   |
   v
[Voice]
   |
   v
[Assemble]
   |
   v
[Store]
   |
   v
[Deploy]
```

Explanatory descriptions should live around the pipeline instead of inside every node.

This prevents the central flow from becoming visually dense.

## 9. Frontend Architecture

The frontend uses standard browser technologies:

```text
HTML
 |
 +-- structure
CSS
 |
 +-- visual system
JavaScript
 |
 +-- interactions
 +-- API requests
 +-- demo state
```

No frontend framework is necessary for the current project.

## 10. Backend Architecture

Flask acts as the application layer:

```text
Browser
   |
   v
Flask
   |
   +---- SQLite
   |
   +---- LLM service
```

`app.py` handles HTTP requests and persistence.

`services/llm.py` isolates model-provider logic.

This separation keeps the application readable.

## 11. LLM Architecture

The LLM is not responsible for the entire application.

The application controls the structure.

Conceptually:

```text
Flask
  |
  +--> task input
  |
  +--> structured LLM request
  |
  +--> validate response
  |
  +--> store result
  |
  +--> send structured result to browser
```

This is preferable to sending an enormous prompt and rendering arbitrary text everywhere.

## 12. Clarification Contract

The LLM should return structured questions containing:

```text
question
type
options
required
```

For example:

```json
{
  "question": "What kind of podcast should the PDF become?",
  "type": "single",
  "options": [
    "A concise 5–10 minute summary",
    "A detailed 20–30 minute discussion",
    "A chapter-by-chapter deep dive",
    "Other"
  ],
  "required": true
}
```

The final `Other` option is part of the UI contract.

## 13. Final Result Contract

A completed plan should contain, conceptually:

```text
summary
verdict
refined_prompt
pipeline[]
models[]
warnings[]
```

Each pipeline step should contain:

```text
step
tool
purpose
reason
instruction
link
```

This creates predictable data for the frontend.

## 14. History

History is associated with an anonymous browser user identifier.

Conceptually:

```text
Browser
   |
   | user_id cookie
   v
Flask
   |
   v
SQLite
```

The application therefore avoids showing a shared global history.

Future authentication can replace the anonymous identifier without changing the broader data model.

## 15. Data Model

A simple conceptual schema:

```text
users
-----
id
created_at


sessions
--------
id
user_id
original_prompt
questions_json
answers_json
result_json
created_at
```

Relationship:

```text
users 1 ─────────── * sessions
```

## 16. Deployment

The application is currently suitable for a simple Python web-service deployment.

```text
GitHub
   |
   v
Render
   |
   v
Gunicorn
   |
   v
Flask
```

The live deployment is:

**https://promptforge50-project.onrender.com/**

Environment-specific configuration such as an LLM API key stays outside the source code.

## 17. Error Philosophy

The application should never present generated-looking content when the required LLM service is unavailable.

Instead, it should clearly explain the current state.

This is important for trust.

For example:

```text
LLM connection required

The clarifying questions and refined prompt with tools
pipeline will be available in a few months.
```

The demo remains available because it is a prebuilt product demonstration rather than a fabricated live LLM response.

## 18. Accessibility and Responsive Behavior

The application should remain usable on:

- desktop
- laptop
- tablet
- mobile

Interactive controls should have:

- sufficient target size
- visible focus states
- meaningful text labels
- clear selected/unselected states

Pipeline elements should stack vertically on narrow screens.

## 19. Security

The LLM API key must never be placed in:

- HTML
- JavaScript
- public GitHub code
- client-side environment variables

The key belongs on the server.

The application should also validate incoming JSON before passing values to the LLM layer or database.

## 20. Deliberate Scope

The system intentionally remains small.

The current architecture is enough to demonstrate:

- web application design
- routing
- forms
- JavaScript interaction
- API integration
- database persistence
- structured data
- deployment

More advanced infrastructure can be added later, but it is not required for the core product.

## 21. Success Criteria

PromptForge succeeds when a user can:

1. enter a rough task;
2. understand what information is missing;
3. answer a small number of relevant questions;
4. receive a task-specific refined prompt;
5. understand why different AI tools are recommended;
6. see the instructions for each pipeline stage;
7. return later and find their own history.

The central quality metric is therefore not the number of features.

It is:

**How much clearer and more actionable is the user's task after using PromptForge?**
