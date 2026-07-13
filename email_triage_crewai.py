import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM

load_dotenv()

# CrewAI LLM via LiteLLM Azure OpenAI provider
llm = LLM(
    model=f"azure/{os.getenv('AZURE_OPENAI_DEPLOYMENT')}",
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_base=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    temperature=0.3,
)

# ─── Agents ───────────────────────────────────────────────────────────────────

classifier_agent = Agent(
    role="Email Classifier",
    goal="Classify an incoming email as exactly one of: urgent, normal, or spam.",
    backstory=(
        "You are a senior triage specialist at a tech company. "
        "You read emails and immediately decide their priority level. "
        "You reply with a single word: urgent, normal, or spam."
    ),
    llm=llm,
    verbose=True,
)

urgent_responder_agent = Agent(
    role="Urgent Responder",
    goal="Draft a brief, professional reply to an urgent email that requires immediate action.",
    backstory=(
        "You are an on-call engineer who handles critical incidents. "
        "When an urgent email arrives you craft a concise reply acknowledging the issue "
        "and outlining the immediate next steps."
    ),
    llm=llm,
    verbose=True,
)

summarizer_agent = Agent(
    role="Email Summarizer",
    goal="Summarize a normal (non-urgent, non-spam) email in one clear sentence.",
    backstory=(
        "You are a busy product manager who needs to quickly understand what every "
        "routine email is about. You produce crisp one-sentence summaries so your "
        "team can act without reading the full message."
    ),
    llm=llm,
    verbose=True,
)

# ─── Task factory ─────────────────────────────────────────────────────────────

def classify_email(email_text: str) -> str:
    """Step 1: Run only the classifier crew and return the classification label."""
    classify_task = Task(
        description=(
            f"Classify the following email as urgent, normal, or spam.\n\n"
            f"Email:\n{email_text}\n\n"
            "Rules:\n"
            "- urgent: requires immediate attention (outages, critical errors, emergencies)\n"
            "- normal: routine business communication\n"
            "- spam: unsolicited promotional or scam content\n\n"
            "Respond with a single word only: urgent, normal, or spam."
        ),
        expected_output="A single word: urgent, normal, or spam.",
        agent=classifier_agent,
    )

    crew = Crew(
        agents=[classifier_agent],
        tasks=[classify_task],
        process=Process.sequential,
        verbose=True,
    )
    crew.kickoff()
    return classify_task.output.raw.strip().lower() if classify_task.output else "unknown"


def handle_urgent(email_text: str) -> str:
    """Step 2a: Draft an urgent reply (only for urgent emails)."""
    task = Task(
        description=(
            f"Draft a brief professional reply for this urgent email.\n\n"
            f"Email:\n{email_text}\n\n"
            "Start your reply with: URGENT REPLY:"
        ),
        expected_output="A short urgent reply starting with 'URGENT REPLY:'",
        agent=urgent_responder_agent,
    )
    crew = Crew(
        agents=[urgent_responder_agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )
    crew.kickoff()
    return task.output.raw.strip() if task.output else "URGENT REPLY: (no output)"


def handle_normal(email_text: str) -> str:
    """Step 2b: Summarize a normal email (only for normal emails)."""
    task = Task(
        description=(
            f"Summarize the following email in one sentence.\n\n"
            f"Email:\n{email_text}\n\n"
            "Start your summary with: SUMMARY:"
        ),
        expected_output="A one-sentence summary starting with 'SUMMARY:'",
        agent=summarizer_agent,
    )
    crew = Crew(
        agents=[summarizer_agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )
    crew.kickoff()
    return task.output.raw.strip() if task.output else "SUMMARY: (no output)"


def handle_spam() -> str:
    """Step 2c: Archive spam — no LLM call needed."""
    return "Archived as spam. No action taken."


def run_triage(email_text: str) -> dict:
    """
    Two-phase triage that mirrors the LangGraph conditional-edge pattern:
      classify → route → urgent_responder | summarizer | archive
    """
    print(f"\n{'='*60}")
    print(f"[CLASSIFY] Running classifier...")
    classification = classify_email(email_text)
    print(f"[CLASSIFY] Result: {classification}")

    if classification == "urgent":
        print("[ROUTE] → draft_urgent_reply")
        output = handle_urgent(email_text)
    elif classification == "normal":
        print("[ROUTE] → summarize_email")
        output = handle_normal(email_text)
    else:
        print("[ROUTE] → archive (spam)")
        output = handle_spam()

    return {
        "email": email_text,
        "classification": classification,
        "output": output,
    }


# ─── CLI test run ─────────────────────────────────────────────────────────────

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
