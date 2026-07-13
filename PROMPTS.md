# Email Triage AI — Live Build Guide
### BVRIT Hyderabad · Day 6 Agentic AI · 2026-07-08

**Stack:** CrewAI · Azure OpenAI GPT-4.1 · FastAPI · SSE Streaming · Vanilla HTML/CSS/JS · Python 3.11 · uv

**Rule:** Build in order. Each prompt depends on the one before it. Do not skip ahead.

---

## Architecture

```
Browser UI  →  FastAPI (/triage/stream SSE)  →  Classifier Agent
                                                      ↓
                                          urgent → Urgent Responder Agent
                                          normal → Summarizer Agent
                                          spam   → Archive (discard)
```

---

## Phase 1 — Project Setup

---

### Prompt 01 — Scaffold the project with uv

**What it creates:** Project directory, `pyproject.toml`, Python 3.11 virtual environment, all dependencies.

**Paste into Claude Code:**

```
Create a new Python project using uv with these exact steps:

1. Run: uv init email-classification-crew-ai
2. Run: cd email-classification-crew-ai
3. Run: uv python pin 3.11
4. Run: uv add crewai[azure-ai-inference] fastapi uvicorn python-dotenv langchain-openai

All remaining work in this session must happen inside the email-classification-crew-ai folder.
Set your working directory to email-classification-crew-ai now and confirm before continuing.

Create a .gitignore inside email-classification-crew-ai/ that ignores:
  __pycache__/, *.py[oc], build/, dist/, wheels/, *.egg-info, .venv, .env

Make sure .env is explicitly in .gitignore — confirm this before moving on.

List all files inside email-classification-crew-ai/ to confirm setup is complete.
```

**Files created:** `pyproject.toml`, `.python-version`, `.gitignore`, `uv.lock`

**Key points:**
- `uv` manages both the venv and lockfile — no separate `pip install` needed
- `crewai[azure-ai-inference]` includes LiteLLM so CrewAI can speak to Azure OpenAI

---

### Prompt 02 — Create the .env credentials file

**What it creates:** Local secrets file — never committed to source control.

**Paste into Claude Code:**

```
Inside the email-classification-crew-ai folder, create a file called .env with these contents:

AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/
AZURE_OPENAI_API_KEY=<your-key>
AZURE_OPENAI_DEPLOYMENT=gpt-4.1
AZURE_OPENAI_CHEAP_DEPLOYMENT=gpt-4.1
AZURE_OPENAI_API_VERSION=2024-10-21

Confirm the file exists inside email-classification-crew-ai/ and is listed in .gitignore.
```

**Files created:** `.env`

**Key points:**
- Replace `<your-resource>` and `<your-key>` with your actual Azure deployment values
- The `python-dotenv` package reads this file automatically when `load_dotenv()` is called

---

## Phase 2 — CrewAI Agent Pipeline

---

### Prompt 03 — LLM config + three CrewAI agents

**What it creates:** `email_triage_crewai.py` with Azure LLM configuration and three module-level agents.

**Paste into Claude Code:**

```
Inside email-classification-crew-ai/, create email_triage_crewai.py with the following:

1. Imports:
   import os
   from dotenv import load_dotenv
   from crewai import Agent, Task, Crew, Process, LLM

   load_dotenv()

2. Configure the LLM:
   llm = LLM(
       model=f"azure/{os.getenv('AZURE_OPENAI_DEPLOYMENT')}",
       api_key=os.getenv("AZURE_OPENAI_API_KEY"),
       api_base=os.getenv("AZURE_OPENAI_ENDPOINT"),
       api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
       temperature=0.3,
   )

3. Define three module-level agents, all with verbose=True and llm=llm:

   classifier_agent
     role: "Email Classifier"
     goal: "Classify an incoming email as exactly one of: urgent, normal, or spam."
     backstory: "You are a senior triage specialist at a tech company. You read emails
       and immediately decide their priority level. You reply with a single word:
       urgent, normal, or spam."

   urgent_responder_agent
     role: "Urgent Responder"
     goal: "Draft a brief, professional reply to an urgent email that requires immediate action."
     backstory: "You are an on-call engineer who handles critical incidents. When an urgent
       email arrives you craft a concise reply acknowledging the issue and outlining
       the immediate next steps."

   summarizer_agent
     role: "Email Summarizer"
     goal: "Summarize a normal (non-urgent, non-spam) email in one clear sentence."
     backstory: "You are a busy product manager who needs to quickly understand what every
       routine email is about. You produce crisp one-sentence summaries so your team
       can act without reading the full message."

Do not add any tasks or functions yet.
Confirm the file is saved inside email-classification-crew-ai/.
```

**Files created:** `email_triage_crewai.py` (partial)

**Key points:**
- LiteLLM inside CrewAI handles the `azure/` prefix routing automatically
- Agents are module-level singletons — the crew reuses them across calls without re-initialising
- Do **not** add `if __name__ == "__main__"` yet — that comes in Prompt 04

---

### Prompt 04 — Two-phase triage pipeline + run_triage() function

**What it creates:** Wires the three agents into a **two-phase conditional pipeline** that mirrors the LangGraph conditional edge: classify first, then route to exactly one handler. Adds a CLI test block.

**Paste into Claude Code:**

```
Inside email-classification-crew-ai/email_triage_crewai.py,
add the following after the agent definitions:

1. A function classify_email(email_text: str) -> str that:
   - Creates a single classify_task (Task) with:
       agent: classifier_agent
       description:
         f"Classify the following email as urgent, normal, or spam.\n\n"
         f"Email:\n{email_text}\n\n"
         "Rules:\n"
         "- urgent: requires immediate attention (outages, critical errors, emergencies)\n"
         "- normal: routine business communication\n"
         "- spam: unsolicited promotional or scam content\n\n"
         "Respond with a single word only: urgent, normal, or spam."
       expected_output: "A single word: urgent, normal, or spam."
   - Creates a Crew with agents=[classifier_agent], tasks=[classify_task],
     Process.sequential, verbose=True
   - Calls crew.kickoff()
   - Returns: classify_task.output.raw.strip().lower()

2. A function handle_urgent(email_text: str) -> str that:
   - Creates a Task with:
       agent: urgent_responder_agent
       description:
         f"Draft a brief professional reply for this urgent email.\n\n"
         f"Email:\n{email_text}\n\n"
         "Start your reply with: URGENT REPLY:"
       expected_output: "A short urgent reply starting with 'URGENT REPLY:'"
   - Creates a Crew with agents=[urgent_responder_agent], tasks=[task],
     Process.sequential, verbose=True
   - Calls crew.kickoff()
   - Returns: task.output.raw.strip()

3. A function handle_normal(email_text: str) -> str that:
   - Creates a Task with:
       agent: summarizer_agent
       description:
         f"Summarize the following email in one sentence.\n\n"
         f"Email:\n{email_text}\n\n"
         "Start your summary with: SUMMARY:"
       expected_output: "A one-sentence summary starting with 'SUMMARY:'"
   - Creates a Crew with agents=[summarizer_agent], tasks=[task],
     Process.sequential, verbose=True
   - Calls crew.kickoff()
   - Returns: task.output.raw.strip()

4. A function handle_spam() -> str that:
   - No LLM call — just returns the string:
     "Archived as spam. No action taken."

5. A function run_triage(email_text: str) -> dict that:
   - Phase 1: calls classification = classify_email(email_text)
   - Phase 2: routes based on classification:
       if classification == "urgent"  →  output = handle_urgent(email_text)
       elif classification == "normal" →  output = handle_normal(email_text)
       else (spam)                    →  output = handle_spam()
   - Returns:
     {
       "email": email_text,
       "classification": classification,
       "output": output,
     }

6. A CLI test block at the bottom:
   if __name__ == "__main__":
       test_emails = [
           "Production database is down. Customer orders are failing. Need immediate fix.",
           "Hi team, here are the meeting notes from today. Please review and add your comments by Friday.",
           "Congratulations! You have won $1,000,000. Click here to claim your prize now!!!",
       ]
       for email in test_emails:
           result = run_triage(email)
           print(f"\nEmail         : {result['email']}")
           print(f"Classification: {result['classification']}")
           print(f"Output        : {result['output']}")
           print("-" * 60)

Then run: uv run python email_triage_crewai.py
All three emails must classify correctly AND route to the right handler before moving to Prompt 05.
Expected routing:
  - urgent email  → handle_urgent()  → output starts with "URGENT REPLY:"
  - normal email  → handle_normal()  → output starts with "SUMMARY:"
  - spam email    → handle_spam()    → output is "Archived as spam. No action taken."
```

**Files created:** `email_triage_crewai.py` (complete)

**Key points:**
- **Two-phase design is critical:** classify first (one crew), then run only the matching handler crew — never all three at once
- Spam gets no LLM call at all — `handle_spam()` is a plain Python function, matching the LangGraph `archive` node
- This mirrors the LangGraph conditional edge exactly: `classify → route → urgent_responder | summarizer | archive`
- If the LLM responds with more than one word, tighten the `expected_output` constraint in `classify_email()`
- **Test now:** run `uv run python email_triage_crewai.py` — verify routing is correct for all three emails before building the API

---

## Phase 3 — FastAPI Layer

---

### Prompt 05 — FastAPI app + /triage endpoint

**What it creates:** `api.py` wrapping `run_triage()` in an HTTP POST endpoint, plus a static file server.

**Paste into Claude Code:**

```
Inside email-classification-crew-ai/, create api.py with the following exact code:

import asyncio
import json
import traceback
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from email_triage_crewai import run_triage

app = FastAPI(title="Email Triage Agent", version="1.0.0")
app.mount("/static", StaticFiles(directory="static"), name="static")

class EmailRequest(BaseModel):
    email_text: str

class TriageResult(BaseModel):
    email: str
    classification: str
    output: str

@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/triage", response_model=TriageResult)
async def triage_email(request: EmailRequest):
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, run_triage, request.email_text)
        return TriageResult(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

Also create the folder email-classification-crew-ai/static/ and inside it
a placeholder index.html containing just: <h1>UI coming soon</h1>

Do not add the streaming endpoint yet.
Confirm both api.py and static/index.html exist inside email-classification-crew-ai/.
```

**Files created:** `api.py` (partial), `static/index.html` (placeholder)

**Key points:**
- `run_in_executor(None, run_triage, ...)` pushes the blocking crew call to a thread pool so FastAPI's event loop stays responsive
- Test with: `uv run uvicorn api:app --reload` then POST to `http://localhost:8000/triage` using curl or Postman

---

### Prompt 06 — /triage/stream SSE endpoint

**What it creates:** Server-Sent Events endpoint so the UI can show pipeline steps appearing in real time.

**Paste into Claude Code:**

```
In email-classification-crew-ai/api.py, add this endpoint after the existing /triage route:

@app.post("/triage/stream")
async def triage_email_stream(request: EmailRequest):
    email_text = request.email_text

    async def event_stream():
        try:
            yield f"data: {json.dumps({'step': 'received', 'message': 'Email received by triage system.'})}\n\n"
            yield f"data: {json.dumps({'step': 'classifying', 'message': 'Classifier agent is analysing the email...'})}\n\n"

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, run_triage, email_text)

            classification = result.get("classification", "unknown")

            yield f"data: {json.dumps({'step': 'classified', 'message': f'Email classified as: {classification.upper()}'})}\n\n"

            if "urgent" in classification:
                yield f"data: {json.dumps({'step': 'routing', 'message': 'Routing to Urgent Responder agent...'})}\n\n"
            elif "normal" in classification:
                yield f"data: {json.dumps({'step': 'routing', 'message': 'Routing to Summarizer agent...'})}\n\n"
            else:
                yield f"data: {json.dumps({'step': 'routing', 'message': 'Routing to archive (spam detected)...'})}\n\n"

            yield f"data: {json.dumps({'step': 'done', 'result': result})}\n\n"

        except Exception as e:
            error_msg = traceback.format_exc()
            yield f"data: {json.dumps({'step': 'error', 'message': str(e), 'detail': error_msg})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

Confirm api.py is saved inside email-classification-crew-ai/.
```

**Files created:** `api.py` (complete)

**Key points:**
- The `\n\n` double-newline after each event is required by the SSE spec — the browser won't fire without it
- The UI uses `fetch` + `ReadableStream`, not `EventSource`, so POST bodies work fine
- **Test now:** restart uvicorn and POST to `/triage/stream` with curl — you should see events printing one by one

---

## Phase 4 — Frontend UI

---

### Prompt 07 — Complete UI (HTML + CSS + JS)

**What it creates:** Full single-file frontend — header, two-column layout, streaming pipeline display, triage history.

**Paste into Claude Code:**

```
Inside email-classification-crew-ai/static/, replace index.html with a complete
single-file UI. Use Segoe UI font, #f1f5f9 light slate background, #6366f1 indigo accent.
All styles go in a <style> block in the <head>. No external CSS frameworks.

--- HEADER ---
A white bar with a bottom border (#e2e8f0). Inside: envelope emoji logo (✉️),
an h1 "Email Triage Agent" in indigo (#4f46e5), and a small grey subtitle span
"powered by CrewAI + GPT-4.1".

--- MAIN LAYOUT ---
A CSS grid with two equal columns, 24px gap, 32px padding on all sides.

LEFT COLUMN — flex column, 20px gap, two white panels with 12px border-radius:

  Panel 1 — heading "QUICK TEST EMAILS" (uppercase, grey, small caps style)
    Three buttons (class: quick-btn), each as a flex row with a colored badge on the
    left and preview text on the right. Hover turns the border indigo and background
    light indigo (#eef2ff).
      Button 1 — badge text "URGENT", badge colors: dark red bg (#7f1d1d),
                 light red text (#fca5a5). Preview: "CRITICAL - Payment Service Down
                 (P0) — 340 transactions failing..."
                 onclick: loadSample('urgent')
      Button 2 — badge text "NORMAL", badge colors: dark blue bg (#1e3a5f),
                 light blue text (#93c5fd). Preview: "Meeting Notes - Q3 Roadmap
                 Review (July 7)..."
                 onclick: loadSample('normal')
      Button 3 — badge text "SPAM", badge colors: dark yellow bg (#3b2f00),
                 light yellow text (#fde68a). Preview: "You Have Been Selected -
                 Claim Your Rs. 50,00,000 Prize!..."
                 onclick: loadSample('spam')

  Panel 2 — heading "COMPOSE EMAIL"
    A textarea (id: emailInput) — light grey bg, indigo border on focus,
    min-height 120px, resizable vertically, inherits font.
    A button (id: sendBtn, onclick: submitEmail()) — "Run Triage", indigo bg,
    white text, full width, darkens on hover, grey disabled state.

RIGHT COLUMN — flex column, 20px gap, two white panels:

  Panel 3 — heading "PROCESSING PIPELINE"
    A div (id: stepsFeed) — flex column, 10px gap, min-height 80px.
    Default content: a centred grey empty-state message
    "Submit an email to see the agent pipeline run."

    Each step item (class: step-item) is a flex row with:
      A circular icon div (class: step-icon) — 28px, three states:
        pending — light grey bg, grey icon
        active  — light indigo bg (#eef2ff), indigo icon, pulse opacity animation
        done    — light green bg (#f0fdf4), green icon (#22c55e)
      A text div (class: step-text) — 0.85rem grey; turns indigo when state is active
      The whole item fades in with a translateY(6px) → 0 animation on insertion.

    Below stepsFeed: a result card div (id: resultCard, class: result-card) —
    hidden by default (display:none), shown by adding class "visible" (display:flex).
    Inside: a div (id: resultClassification) for the emoji + coloured classification label,
    and a div (id: resultOutput) for the agent output text — pre-wrap, left indigo border.

  Panel 4 — heading "TRIAGE HISTORY"
    A div (id: historyList) — flex column, 10px gap, max-height 420px, scrollable.
    Default content: centred grey empty-state "No emails triaged yet."
    Each history item (class: history-item) is a flex column card — shows a truncated
    single-line email preview (hi-email) and a meta row (hi-meta) with a coloured
    badge and a timestamp. Border turns indigo on hover. Clicking replays the result.

--- LOADING STATE ---
A spinner class: 16px circle, 2px border, indigo top-border, spinning CSS animation.
Used inside sendBtn while processing: '<span class="spinner"></span> Processing...'

--- JAVASCRIPT ---

1. SAMPLES constant — object with three keys: urgent, normal, spam.
   Each value is a multiline template literal email with realistic From/To/Subject/Date
   headers followed by a body. Use these exact subjects and senders:
     urgent — From: ops-alerts@techvestglobal.com
               Subject: CRITICAL - Payment Service Down (P0)
               Body: payment service returning 503 errors for 12 minutes, ~340 failed
               transactions, connection pool exhaustion on prod-db-payments-01,
               on-call engineer Ravi unavailable, P0 severity, est. Rs. 8.5L/hr impact,
               signed "Automated alert from PagerDuty / TechVest Ops"
     normal — From: priya.sharma@techvestglobal.com
               Subject: Meeting Notes - Q3 Roadmap Review (July 7)
               Body: attendees Priya/Arjun/Neha/Vishal/Rohit, three key decisions
               (feature freeze July 25, AI triage prioritised, design review July 14),
               three action items with owners and deadlines, next meeting July 14 11AM IST
     spam   — From: noreply@lucky-winner-claims.net
               Subject: You Have Been Selected - Claim Your Rs. 50,00,000 Prize!
               Body: grand prize winner announcement, claim link
               (http://claim-your-prize-now.lucky-winner-claims.net/redeem?id=VV20260707),
               requires bank details and Rs. 2,500 processing fee, 48-hour deadline,
               signed "Mr. James Okonkwo, International Prize Committee"

2. history array — module-level, holds past results for replay.

3. loadSample(type) — sets emailInput.value to SAMPLES[type].

4. classificationStyle(cls) — returns {emoji, color, badge} by checking if cls includes:
   "urgent" → emoji 🔴, color #fca5a5, badge class badge-urgent
   "normal" → emoji 🔵, color #93c5fd, badge class badge-normal
   anything else (spam) → emoji 🟡, color #fde68a, badge class badge-spam

5. addStep(icon, text, state="done") — creates a step-item div, appends to stepsFeed,
   returns the element so the caller can update it in place later.

6. async submitEmail():
   - Return early if emailInput is empty.
   - Disable sendBtn, set innerHTML to spinner + "Processing..."
   - Clear stepsFeed innerHTML, remove "visible" from resultCard.
   - Immediately add two steps manually:
       addStep("📨", "Email received by triage system.", "done")
       classifyStep = addStep("🤖", "Classifier agent is analysing the email...", "active")
   - POST to /triage/stream with JSON body {email_text: emailText}.
   - Read the response body with getReader() + TextDecoder in a while(true) loop.
   - For each chunk: split on "\n", keep lines starting with "data:", JSON.parse each.
   - Handle each parsed event by step value:
       "classified" → set classifyStep's icon class to "step-icon done", icon text to "✓",
                      update step-text content to data.message, remove "active" class
       "routing"    → addStep("⚡", data.message, "active")
       "done"       → store data.result as finalResult; find any remaining active icon
                      in the feed and mark it done with "✓"; addStep("✓", "Triage complete.", "done")
       "error"      → addStep("✗", data.message, "pending")
   - After the loop: if finalResult exists, call showResult(finalResult) and addToHistory(finalResult).
   - In finally: re-enable sendBtn, reset text to "Run Triage".

7. showResult(result):
   - Get cls from result.classification or "unknown".
   - Call classificationStyle(cls) to get style.
   - Set resultClassification innerHTML to: emoji + coloured span with cls.toUpperCase().
   - Set resultOutput textContent to result.output.
   - Add class "visible" to resultCard.

8. addToHistory(result):
   - Unshift result into history array.
   - If historyList contains an empty-state div, clear it.
   - Create a history-item div with hi-email (result.email text) and hi-meta row
     (badge with classification + new Date().toLocaleTimeString()).
   - Set onclick to call showResult(result).
   - Prepend the item to historyList.

Use exact IDs: emailInput, sendBtn, stepsFeed, resultCard, resultClassification,
resultOutput, historyList. Use exact classes: quick-btn, badge, badge-urgent,
badge-normal, badge-spam, panel, step-item, step-icon, step-text, result-card,
result-classification, result-output, history-item, hi-email, hi-meta, empty-state,
spinner, send-btn, steps-feed, history-list, quick-emails.

Confirm the file is saved at email-classification-crew-ai/static/index.html.
```

**Files created:** `static/index.html` (complete — HTML + CSS + JS)

**Key points:**
- All styles go in a single `<style>` block — no external CSS files or frameworks needed
- Do not modify any element IDs or class names — the JavaScript depends on them exactly
- The step-icon states (pending / active / done) drive the live pipeline animation in the browser

---

## Phase 5 — Final Wiring & Run

---

### Prompt 08 — Update main.py + run the app

**What it creates:** Replaces the placeholder `main.py` with a uvicorn launcher. Full end-to-end verification.

**Paste into Claude Code:**

```
Inside email-classification-crew-ai/, replace the contents of main.py with:

import uvicorn
from api import app

def main():
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()

Then start the server by running these two commands in order:
  cd email-classification-crew-ai
  uv run python main.py

Open http://localhost:8000 in your browser (not http://0.0.0.0:8000 — that is invalid on Windows).

Verify the following in order:

1. The UI loads — header shows "Email Triage Agent powered by CrewAI + GPT-4.1"
2. Click URGENT sample → Run Triage → pipeline steps appear one by one → URGENT result shown
3. Click NORMAL sample → Run Triage → NORMAL + one-sentence SUMMARY: shown
4. Click SPAM sample → Run Triage → SPAM result shown
5. All three entries appear in Triage History and clicking each replays the result

Report any errors with the full terminal traceback.
```

**Files created:** `main.py` (complete)

**Key points:**
- If the server fails to start, check that `static/index.html` exists — FastAPI throws at startup if the directory is missing
- CrewAI verbose logs appear in the **terminal**, not the browser — keep both visible during demo
- If `classification` comes back empty, check that `classify_task.output.raw.strip().lower()` is in `run_triage()`

---

## File Map (final state)

```
email-classification-crew-ai/
├── .env                        ← secrets (never commit)
├── .gitignore
├── .python-version             ← 3.11
├── pyproject.toml
├── uv.lock
├── email_triage_crewai.py      ← CrewAI agents + tasks + run_triage()
├── api.py                      ← FastAPI + /triage + /triage/stream
├── main.py                     ← uvicorn launcher
└── static/
    └── index.html              ← full UI (HTML + CSS + JS)
```

## Run Command

```bash
uv run python main.py
# open http://localhost:8000
```
