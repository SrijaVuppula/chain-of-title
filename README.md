# Chain of Title

An Authorized AI Compliance Agent for film and media production.

## The problem

Productions now use AI tools throughout post-production — background generation, de-aging, voice synthesis, upscaling — supplied by dozens of vendors, each with different training-data provenance. Completion bond insurers and distributors are starting to require proof that these tools were trained on licensed data with a documented chain of title. Today that verification is manual and ad hoc, often discovered too late — right before a distribution deal closes. No dedicated tooling exists for this yet.

## What this does

Chain of Title is a four-agent pipeline, built on Google Agent Builder / Gemini Enterprise, that:

1. **Director** — receives a production's AI-tool manifest and orchestrates the pipeline
2. **Verification Agent** — checks each tool against a registry of known licensing status (cleared / flagged / needs review)
3. **Remediation Agent** — for anything not cleared, autonomously holds the affected shot, triggers a notification, and suggests a cleared substitute
4. **Governance Agent** — logs every decision via the **IBM watsonx MCP server**, producing an immutable audit trail suitable for an insurer or distributor

## Stack

Flask · React · Firestore · Google Agent Builder (Gemini) · IBM watsonx MCP · GCP Cloud Functions

## Getting started

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python app.py

# Frontend
cd frontend
npm install
npm start
```

Environment variables needed (see `backend/config.py`): `GCP_PROJECT_ID`, `IBM_WATSONX_APIKEY`, `IBM_WATSONX_REGION`.

## Demo

_Video link goes here once recorded (see BUILD_PLAN.md Day 33)._

## Build log

See [`BUILD_PLAN.md`](./BUILD_PLAN.md) for the full day-by-day build history.

## License

MIT — see [`LICENSE`](./LICENSE).
