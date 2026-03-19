#!/usr/bin/env python3
"""
Slack Ad Script AI Review — FastAPI Backend
Replaces n8n workflow with direct Python implementation
"""

from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import json, re, os, httpx, gspread
from google.oauth2 import service_account
from datetime import datetime

load_dotenv()

app = FastAPI()

# ── Config ─────────────────────────────────────────────────────────────────────
OPENAI_API_KEY     = (os.getenv("OPENAI_API_KEY") or "").strip()
SLACK_BOT_TOKEN    = (os.getenv("SLACK_BOT_TOKEN") or "").strip()
SCRIPTS_CHANNEL_ID = os.getenv("SCRIPTS_CHANNEL_ID", "C0ALXAY43AP")
REVIEW_CHANNEL_ID  = os.getenv("REVIEW_CHANNEL_ID",  "C0AM7ABG9EY")
GOOGLE_SHEET_ID    = os.getenv("GOOGLE_SHEET_ID",    "14CQGHa_Bhzpck_jm2O8kkBPY5nRNV4q2TiIPvFeVosk")
SERVICE_ACCOUNT_JSON = os.getenv("SERVICE_ACCOUNT_JSON")  # full JSON string as env var

SCORING_PROMPT = """You are an expert advertising copywriter and script evaluator. Score the following ad script using this framework:

1. HOOK STRENGTH (0-20 pts)
Does the opening immediately grab attention and stop the scroll?

2. CLARITY OF OFFER (0-20 pts)
Is the product/service and its value proposition crystal clear?

3. CALL TO ACTION (0-20 pts)
Is the CTA specific, urgent, and easy to follow?

4. EMOTIONAL APPEAL (0-20 pts)
Does it connect emotionally or psychologically with the target audience?

5. FLOW AND READABILITY (0-20 pts)
Is it natural to read aloud? Good pacing, rhythm, and appropriate length?

For EACH criterion provide:
- Score: X/20
- Why: 1-2 sentences
- Fix: One specific actionable improvement

End with:
====================
TOTAL SCORE: X/100
VERDICT: STRONG / NEEDS WORK / MAJOR REVISION / REJECT
TOP PRIORITY FIX: [Single most important change]
SUMMARY: [2-3 sentences summarizing the overall quality, strongest point, and most critical weakness]
====================

Thresholds:
80-100 -> STRONG - Ready to run
60-79  -> NEEDS WORK - Fix before running
40-59  -> MAJOR REVISION - Rewrite key sections
0-39   -> REJECT - Start over"""


# ── Google Sheets ──────────────────────────────────────────────────────────────
def get_sheet():
    info = json.loads(SERVICE_ACCOUNT_JSON)
    creds = service_account.Credentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    gc = gspread.authorize(creds)
    return gc.open_by_key(GOOGLE_SHEET_ID).worksheet("Script Reviews")


def find_row_by_ts(ws, target_ts: str) -> int:
    """Returns 1-based row index or -1 if not found."""
    col_g = ws.col_values(7)  # column G = Review Message TS
    try:
        target_norm = str(round(float(target_ts)))
    except (ValueError, TypeError):
        return -1
    for i, val in enumerate(col_g[1:], start=2):  # skip header row
        try:
            if str(round(float(val))) == target_norm:
                return i
        except (ValueError, TypeError):
            continue
    return -1


# ── Slack helpers ──────────────────────────────────────────────────────────────
async def slack_post(client: httpx.AsyncClient, method: str, payload: dict) -> dict:
    r = await client.post(
        f"https://slack.com/api/{method}",
        json=payload,
        headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
    )
    return r.json()


async def get_user_real_name(user_id: str) -> str:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"https://slack.com/api/users.info?user={user_id}",
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
        )
        data = r.json()
        if data.get("ok"):
            return data["user"].get("real_name") or data["user"].get("name", user_id)
    return user_id


# ── AI Review ──────────────────────────────────────────────────────────────────
async def get_ai_review(script: str) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            "https://api.openai.com/v1/chat/completions",
            json={
                "model": "gpt-4o",
                "max_tokens": 1500,
                "messages": [
                    {"role": "system", "content": SCORING_PROMPT},
                    {"role": "user",   "content": f"Review this ad script:\n\n{script}"}
                ]
            },
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"}
        )
        return r.json()["choices"][0]["message"]["content"]


def parse_review(review: str):
    score_m   = re.search(r'TOTAL SCORE[:\s]+(\d+)/100', review, re.I)
    score     = score_m.group(1) if score_m else "?"
    verdict_m = re.search(r'VERDICT[:\s]+(.+)', review, re.I)
    verdict   = verdict_m.group(1).strip().split('\n')[0] if verdict_m else "REVIEW NEEDED"
    summary_m = re.search(r'SUMMARY[:\s]+([\s\S]+?)(?:={4,}|$)', review, re.I)
    summary   = summary_m.group(1).strip() if summary_m else ""
    review_clean = re.sub(r'SUMMARY[:\s]+[\s\S]+$', '', review, flags=re.I).strip()
    return score, verdict, summary, review_clean


# ── Slack blocks ───────────────────────────────────────────────────────────────
def build_review_blocks(user_id, script, score, verdict, review_clean, summary):
    score_num = int(score) if str(score).isdigit() else 0
    if score_num >= 80:   emoji = ":large_green_circle:"
    elif score_num >= 60: emoji = ":large_yellow_circle:"
    elif score_num >= 40: emoji = ":large_orange_circle:"
    else:                 emoji = ":red_circle:"

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"Ad Script Review — {score}/100", "emoji": True}},
        {"type": "section", "fields": [
            {"type": "mrkdwn", "text": f"*Submitted by:*\n<@{user_id}>"},
            {"type": "mrkdwn", "text": f"*Verdict:*\n{emoji} {verdict}"}
        ]},
        {"type": "divider"},
        {"type": "section", "text": {"type": "mrkdwn", "text": f":memo: *Script:*\n{script[:2000]}"}},
        {"type": "divider"},
        {"type": "section", "text": {"type": "mrkdwn", "text": f":robot_face: *Full AI Review:*\n{review_clean[:2900]}"}},
        {"type": "divider"},
    ]
    if summary:
        blocks += [
            {"type": "section", "text": {"type": "mrkdwn", "text": f":bulb: *AI Summary:*\n{summary}"}},
            {"type": "divider"},
        ]
    blocks.append({"type": "actions", "elements": [
        {"type": "button", "text": {"type": "plain_text", "text": ":white_check_mark: Approve", "emoji": True},
         "style": "primary", "action_id": "approve", "value": "approve"},
        {"type": "button", "text": {"type": "plain_text", "text": ":pencil2: Revise", "emoji": True},
         "action_id": "revise", "value": "revise"},
        {"type": "button", "text": {"type": "plain_text", "text": ":x: Reject", "emoji": True},
         "style": "danger", "action_id": "reject", "value": "reject"},
    ]})
    return blocks


# ── Handlers ───────────────────────────────────────────────────────────────────
async def handle_script_message(event: dict):
    script  = (event.get("text") or "").strip()
    user_id = event.get("user", "unknown")

    if len(script) < 50:
        return

    review = await get_ai_review(script)
    score, verdict, summary, review_clean = parse_review(review)
    blocks = build_review_blocks(user_id, script, score, verdict, review_clean, summary)

    async with httpx.AsyncClient() as client:
        resp = await slack_post(client, "chat.postMessage", {
            "channel": REVIEW_CHANNEL_ID,
            "blocks":  blocks,
            "text":    f"New ad script from <@{user_id}> — Score: {score}/100"
        })

    review_ts = resp.get("ts", "")
    ws = get_sheet()
    ws.append_row([
        datetime.utcnow().isoformat(),
        user_id, script, score, verdict, review, review_ts, "", "", ""
    ])


async def handle_button_click(payload: dict):
    action     = payload["actions"][0]
    action_id  = action["action_id"]
    message_ts = payload["container"]["message_ts"]
    channel_id = payload["channel"]["id"]
    user_id    = payload["user"]["id"]

    real_name  = await get_user_real_name(user_id)
    decision   = action_id.upper()

    label_map  = {"approve": "Approved", "revise": "Revision Requested", "reject": "Rejected"}
    emoji_map  = {"approve": ":white_check_mark:", "revise": ":pencil2:", "reject": ":x:"}
    label      = label_map[action_id]
    emoji      = emoji_map[action_id]

    # Replace buttons with status line in Slack message
    orig_blocks = payload["message"]["blocks"]
    new_blocks  = [b for b in orig_blocks if b["type"] != "actions"]
    new_blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"{emoji} *{label}* by <@{user_id}>"}
    })

    async with httpx.AsyncClient() as client:
        await slack_post(client, "chat.update", {
            "channel": channel_id,
            "ts":      message_ts,
            "blocks":  new_blocks,
            "text":    f"{label} by <@{user_id}>"
        })
        if action_id == "revise":
            await slack_post(client, "chat.postMessage", {
                "channel":   REVIEW_CHANNEL_ID,
                "thread_ts": message_ts,
                "text":      ":speech_balloon: Revision requested. Reply in this thread with your notes and they will be saved automatically."
            })

    ws  = get_sheet()
    row = find_row_by_ts(ws, message_ts)
    if row > 0:
        ws.update(f"H{row}:J{row}", [[decision, "", real_name]])


async def handle_admin_reply(event: dict):
    text      = (event.get("text") or "").strip()
    thread_ts = event.get("thread_ts", "")

    if not text:
        return

    decision = ""
    notes    = text

    if re.match(r'^APPROVE', text, re.I):
        decision = "APPROVE"
        notes    = re.sub(r'^APPROVE[:\s]*', '', text, flags=re.I).strip()
    elif re.match(r'^REVISE', text, re.I):
        decision = "REVISE"
        notes    = re.sub(r'^REVISE[:\s]*', '', text, flags=re.I).strip()
    elif re.match(r'^REJECT', text, re.I):
        decision = "REJECT"
        notes    = re.sub(r'^REJECT[:\s]*', '', text, flags=re.I).strip()

    ws  = get_sheet()
    row = find_row_by_ts(ws, thread_ts)
    if row < 0:
        return

    if decision:
        ws.update(f"H{row}:I{row}", [[decision, notes]])
    else:
        ws.update(f"I{row}", [[notes]])


# ── Main webhook ───────────────────────────────────────────────────────────────
@app.post("/slack")
async def slack_webhook(request: Request, background_tasks: BackgroundTasks):
    content_type = request.headers.get("content-type", "")

    # Button click (interactivity payload — form encoded)
    if "application/x-www-form-urlencoded" in content_type:
        form    = await request.form()
        payload = json.loads(form.get("payload", "{}"))
        background_tasks.add_task(handle_button_click, payload)
        return JSONResponse({"ok": True})

    # Event callback (JSON)
    body = await request.body()
    data = json.loads(body)

    # Slack URL verification challenge
    if data.get("type") == "url_verification":
        return JSONResponse({"challenge": data["challenge"]})

    event   = data.get("event", {})
    subtype = event.get("subtype", "")
    channel = event.get("channel", "")
    thread_ts = event.get("thread_ts", "")

    # Ignore bot messages and non-message events
    if subtype or event.get("bot_id") or event.get("type") != "message":
        return JSONResponse({"ok": True})

    if channel == SCRIPTS_CHANNEL_ID:
        background_tasks.add_task(handle_script_message, event)
    elif channel == REVIEW_CHANNEL_ID and thread_ts:
        background_tasks.add_task(handle_admin_reply, event)

    return JSONResponse({"ok": True})


@app.get("/")
def health():
    return {"status": "ok", "service": "Slack Ad Script AI Review"}
