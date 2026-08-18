import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")


# --- GCP / Firestore ---
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "chain-of-title-hackathon")
# Explicitly named, not "(default)" -- typing "(default)" into the GCP
# console's Database ID field creates a real custom-named database, it does
# NOT select Firestore's actual default-database slot.
FIRESTORE_DATABASE = "chain-of-title-hackathon"

# --- IBM track ---
# IBM Bob: dev-time tool only (bob.ibm.com), no runtime credentials needed.
# Event pipeline: local Kafka via Redpanda (Docker), no external account or billing.
KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.environ.get("KAFKA_TOPIC", "chain-of-title.decisions")

# --- Gemini / Vertex AI ---
GCP_LOCATION = os.environ.get("GCP_LOCATION", "us-central1")

NOTIFY_HOLD_URL = os.environ.get(
    "NOTIFY_HOLD_URL",
    "https://us-central1-chain-of-title-hackathon.cloudfunctions.net/notify-hold",
)
