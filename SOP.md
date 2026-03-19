# SOP — Slack Ad Script AI Review System

## Overview
An automated system that reviews ad scripts posted in Slack, scores them using AI, and lets admins approve, revise, or reject directly in Slack. All decisions are logged to Google Sheets.

---

## How It Works (Quick Summary)
1. Copywriter posts a script in **#scripts**
2. AI automatically scores it (0–100) across 5 criteria
3. Review is posted in **#review** with score, verdict, and buttons
4. Admin clicks **Approve / Revise / Reject**
5. Everything logs to Google Sheets automatically

---

## For Copywriters

### How to Submit a Script
1. Open Slack → go to **#scripts** channel
2. Type or paste your ad script and send
3. The AI review will appear in **#review** within ~15 seconds
4. Wait for admin feedback there

### Rules
- Script must be **at least 50 characters** or it will be ignored
- One script per message — don't combine multiple scripts in one post
- Plain text only — no formatting needed

---

## For Admins

### Reviewing a Script in #review
Each review message shows:
- **Score** (0–100) with color indicator: 🟢 80–100 STRONG | 🟡 60–79 NEEDS WORK | 🟠 40–59 MAJOR REVISION | 🔴 0–39 REJECT
- **Full breakdown** across 5 criteria (Hook, Clarity, CTA, Emotional Appeal, Flow)
- **AI Summary** — 2–3 sentence overall assessment
- **3 buttons** at the bottom: ✅ Approve | ✏️ Revise | ❌ Reject

### Approving a Script
- Click **✅ Approve**
- Done — sheet logs APPROVE + your name automatically

### Rejecting a Script
- Click **❌ Reject**
- Done — sheet logs REJECT + your name automatically

### Requesting Revisions
1. Click **✏️ Revise**
2. A bot message appears in the thread: *"Revision requested. Reply here with your notes."*
3. Click **Reply** on that thread message
4. Type your notes (e.g. `needs a stronger hook and clearer CTA`)
5. Send — notes save to Google Sheets automatically

---

## Google Sheets Log

**Sheet:** [Script Reviews](https://docs.google.com/spreadsheets/d/14CQGHa_Bhzpck_jm2O8kkBPY5nRNV4q2TiIPvFeVosk)

| Column | Field | Description |
|--------|-------|-------------|
| A | Timestamp | When the script was submitted |
| B | Submitted By | Slack user ID of copywriter |
| C | Script | Full script text |
| D | AI Score | Score out of 100 |
| E | AI Verdict | STRONG / NEEDS WORK / MAJOR REVISION / REJECT |
| F | Full AI Review | Complete breakdown with all 5 criteria |
| G | Review Message TS | Internal Slack timestamp (do not edit) |
| H | Admin Decision | APPROVE / REVISE / REJECT |
| I | Admin Notes | Revision notes from admin |
| J | Reviewed By | Name of admin who made the decision |

---

## AI Scoring Criteria
Each criterion is scored out of 20 points (total = 100):

1. **Hook Strength** — Does it grab attention immediately?
2. **Clarity of Offer** — Is the product/service clearly explained?
3. **Call to Action** — Is the CTA specific and compelling?
4. **Emotional Appeal** — Does it connect emotionally with the audience?
5. **Flow and Readability** — Is it easy to read and well-paced?

### Verdict Thresholds
| Score | Verdict |
|-------|---------|
| 80–100 | 🟢 STRONG — Ready to run |
| 60–79 | 🟡 NEEDS WORK — Minor improvements needed |
| 40–59 | 🟠 MAJOR REVISION — Significant rework required |
| 0–39 | 🔴 REJECT — Start over |

---

## Technical Setup

### Stack
- **Backend:** Python + FastAPI hosted on Railway
- **AI:** OpenAI GPT-4o
- **Sheets:** Google Sheets via Service Account
- **Hosting:** Railway (`slack-review-backend-production.up.railway.app`)
- **Code:** [github.com/brygaming121/slack-review-backend](https://github.com/brygaming121/slack-review-backend)

### Slack App Settings (api.slack.com/apps)
Both URLs must point to:
```
https://slack-review-backend-production.up.railway.app/slack
```
- Event Subscriptions → Request URL
- Interactivity & Shortcuts → Request URL

### Environment Variables (set in Railway dashboard)
| Variable | Description |
|----------|-------------|
| OPENAI_API_KEY | OpenAI API key for GPT-4o |
| SLACK_BOT_TOKEN | Slack bot token (xoxb-...) |
| SERVICE_ACCOUNT_JSON | Full Google service account JSON (one line) |

---

## Maintenance

### Updating the AI Scoring Prompt
1. Open `C:\Users\bryan\slack-review-backend\main.py`
2. Find `SCORING_PROMPT` near the top
3. Edit the prompt text
4. Run: `git add main.py && git commit -m "Update scoring prompt" && git push`
5. Railway auto-deploys in ~30 seconds

### Running Locally (for testing)
```bash
cd C:\Users\bryan\slack-review-backend
python -m uvicorn main:app --port 8090 --reload
ngrok http 8090
```
Then update both Slack URLs to the ngrok URL.

### If Something Breaks
1. Check Railway logs: Railway dashboard → slack-review-backend → Deployments → View Logs
2. Common issues:
   - **Bot not responding:** Check Railway service is Active (not Crashed)
   - **Sheets not updating:** Check SERVICE_ACCOUNT_JSON env var is valid JSON
   - **Buttons not working:** Verify Interactivity URL is set correctly in Slack app
   - **No reviews posting:** Verify Event Subscriptions URL is set and verified

### Restarting the Service
Railway dashboard → slack-review-backend → click **Restart**

---

## Key Files
| File | Purpose |
|------|---------|
| `main.py` | Main backend code |
| `requirements.txt` | Python dependencies |
| `railway.toml` | Railway deployment config |
| `main_backup_20260319_final.py` | Last known working backup |
| `.env` | Local credentials (never commit this) |

---

*Last updated: 2026-03-19*
