# Chain of Title

An Authorized AI Compliance Agent for film and media production.

## The Problem

AI tools are now embedded throughout film and media production - de-aging, voice synthesis, background generation, upscaling - but the industry has no systematic way to verify that the AI tools used on a given shot were trained on properly licensed data with a clean chain of title.

This isn't a hypothetical risk. Completion bond insurers, who guarantee that a production will finish and deliver, are beginning to require proof of "Authorized AI" usage before they'll bond a project. At the same time, several widely-used generative tools are under active litigation over training data provenance, and the tools considered safe can change without warning - OpenAI's Sora, for example, was a cleared partner tool until its shutdown in March 2026, illustrating that a one-time compliance check is not enough. Licensing status has to be re-verified continuously, not signed off once at the start of production.

Today, that verification happens manually, if it happens at all - a VFX supervisor or production counsel spot-checking tool credits against whatever they remember reading. On a production with dozens of vendors and hundreds of shots, that doesn't scale, and it leaves productions exposed to bond disputes, E&O insurance gaps, and last-minute delivery holds discovered far too late to fix cheaply.

**Chain of Title** closes that gap: an autonomous compliance agent that checks every AI tool named in a production's shot manifest against a maintained licensing registry, flags anything unverified or newly-risky in real time, and keeps a full audit trail of every decision - so "was this shot cleared, and why" has an answer a bond insurer or studio counsel can actually check.

## What this does

Chain of Title is a four-agent pipeline that:

1. **Director** - receives a production's AI-tool manifest and orchestrates the pipeline for each shot
2. **Verification Agent** - checks each tool against a registry of known licensing status (cleared / flagged / needs review / discontinued / unknown)
3. **Remediation Agent** - for anything not cleared, autonomously holds the affected shot, triggers a notification, and suggests a cleared substitute
4. **Governance Agent** - consumes decision events from a local Kafka (Redpanda) pipeline and writes each one to an immutable audit trail in Firestore, suitable for an insurer or distributor to review

Per-shot compliance checks run through a real Google ADK `SequentialAgent` (Director) composed of deterministic `BaseAgent` steps -- not LLM-driven tool selection, since verification and remediation must never be subject to model judgment about whether to run.

## Stack

Flask · React · Firestore · Google ADK · Gemini (Vertex AI) · IBM Bob (development) · Kafka/Redpanda (event pipeline) · GCP Cloud Functions

**Built with IBM Bob** as part of the development process (IBM track requirement).

## Getting started

### Prerequisites
- Python 3.10+, Node 18+, Docker Desktop
- A GCP project with Firestore and Vertex AI enabled
- `gcloud auth application-default login` run once, for local Firestore/Vertex AI access

### 1. Start the event pipeline
```bash
docker-compose up -d
```
Starts Redpanda (Kafka-compatible), used by the Governance Agent for the audit-log event stream.

### 2. Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```
Create `backend/.env`:
```
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=us-central1
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC=chain-of-title.decisions
GRPC_ENABLE_FORK_SUPPORT=false
```
```bash
python app.py
```
Runs at `http://localhost:5001` (not 5000 - macOS AirPlay Receiver uses that port).

### 3. Frontend
```bash
cd frontend
npm install
npm run start
```
Runs at `http://localhost:5173`.

## Demo

- **Live project URL:** _link goes here once deployed_
- **Demo video:** _link goes here once recorded_

## License

MIT - see [`LICENSE`](./LICENSE).
