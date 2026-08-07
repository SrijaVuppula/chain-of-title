import os

# --- GCP / Firestore ---
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "chain-of-title-hackathon")
FIRESTORE_DATABASE = "chain-of-title-hackathon"  # see CLAUDE.md — never "(default)"

# --- IBM track ---
# IBM Bob: dev-time tool only (bob.ibm.com), no runtime credentials needed.
# Event pipeline: local Kafka via Redpanda (Docker), no external account or billing.
KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.environ.get("KAFKA_TOPIC", "chain-of-title.decisions")

# --- Gemini / Vertex AI ---
GCP_LOCATION = os.environ.get("GCP_LOCATION", "us-central1")
