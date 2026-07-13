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


@app.post("/triage/stream")
async def triage_email_stream(request: EmailRequest):
    email_text = request.email_text

    async def event_stream():
        try:
            yield f"data: {json.dumps({'step': 'received', 'message': 'Email received by triage system.'})}\n\n"
            yield f"data: {json.dumps({'step': 'classifying', 'message': 'Classifier agent is analysing the email...'})}\n\n"

            # Run blocking crew in thread pool so we don't block the event loop
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
