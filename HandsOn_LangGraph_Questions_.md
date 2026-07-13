

| GENAI & AGENTIC AI ENGINEERING  ·  DAY 6 · SESSION 3  ·  HANDS-ON Hands-On: Build an Email Triage Agent with LangGraph Five coding exercises. Write state, nodes, edges, run the graph, and extend it. Learn the framework on a simple problem before building the Recruitment Agent in Session 4\. QUESTIONS      ·      \~45 min      ·      CODE exercises      ·      builds toward Session 4 lab |
| :---- |

| A SIMPLE PROBLEM TO LEARN THE FRAMEWORK The Email Triage Agent has 3 nodes, 1 conditional edge, and 3 state fields. It classifies an email as urgent, normal, or spam, then routes to the appropriate handler. This is small enough to understand in 10 minutes and code in 30\. The Recruitment Agent (Session 4\) is the real challenge — this is the warm-up. |
| :---- |

**Exercise 1 · Define the State and the First Node**

**Focus:** TypedDict state · node function pattern · state-in, update-out

**Your task**

1\. Write the EmailTriageState TypedDict with 3 fields: email\_text (str), classification (Optional\[str\]), output (Optional\[str\]).2. Write the classify\_email node function: reads state\["email\_text"\], calls the LLM to classify as urgent/normal/spam, returns {"classification": result}.3. Mentally trace: after classify\_email runs on "Server down\! APIs returning 500\!", what does the state look like?

|   |
| :---- |

**Exercise 2 · Write the Handler Nodes**

**Focus:** Multiple nodes · same pattern, different behaviour

**Your task**

1\. Write draft\_urgent\_reply: reads state\["email\_text"\], calls LLM to draft a brief urgent reply, returns {"output": "URGENT REPLY: ..."}2. Write summarize\_email: reads state\["email\_text"\], calls LLM to produce a one-sentence summary, returns {"output": "SUMMARY: ..."}3. Write archive\_email: no LLM call needed, just returns {"output": "Archived as spam. No action taken."}

|   |
| :---- |

**Exercise 3 · Write the Routing Function and Wire the Graph**

**Focus:** Conditional edges · graph construction · the full wiring

**Your task**

1\. Write route\_email: reads state\["classification"\], returns "draft\_urgent\_reply" for urgent, "summarize" for normal, "archive" for spam.2. Create the StateGraph(EmailTriageState).3. Add all 4 nodes: classify, draft\_urgent\_reply, summarize, archive.4. Set the entry point to "classify".5. Add the conditional edge from "classify" using route\_email.6. Compile the graph.

|   |
| :---- |

**Exercise 4 · Run the Graph with Three Different Emails**

**Focus:** Invoke · stream · verify routing · trace output

**Your task**

1\. Run the graph with 3 different emails:   • Urgent: "Production database is down. Customer orders are failing. Need immediate fix."   • Normal: "Hi team, here are the meeting notes from today. Please review and add your comments by Friday."   • Spam: "Congratulations\! You have won $1,000,000. Click here to claim your prize now\!\!\!"2. For each: use app.stream() to print which nodes fire.3. Verify: urgent fires classify → draft\_urgent\_reply. Normal fires classify → summarize. Spam fires classify → archive.4. If any email takes the wrong path, the classify\_email prompt needs tightening. Fix it and re-run.

|   |
| :---- |

**Exercise 5 · Rebuild the Email Triage Agent with CrewAI**

**Focus:** CrewAI · role-based agents · same problem, different framework

Rebuild the Email Triage Agent using CrewAI instead of LangGraph. Same 3 classifications, same behaviour, completely different mental model. Compare both frameworks before choosing one for Session 4\.

**Your task**

1\. Define 3 CrewAI agents: a Classifier (classifies emails), an Urgent Responder (drafts urgent replies), and a Summarizer (summarizes normal emails). Each has a role, goal, and backstory.2. Define 3 tasks: classify the email, handle urgent emails, summarize normal emails. Assign each task to the right agent.3. Create a Crew with all 3 agents, set process=Process.sequential, and run crew.kickoff().4. Run the same 3 test emails from Exercise 4 (urgent, normal, spam). Does the output match LangGraph?5. Compare: what is easier in CrewAI? What is easier in LangGraph? Which would you choose for the Session 4 Recruitment Agent lab and why?

|   |
| :---- |

GenAI & Agentic AI Engineering   ·   Day 6 · Session 3   ·   Hands-On: Email Triage Agent