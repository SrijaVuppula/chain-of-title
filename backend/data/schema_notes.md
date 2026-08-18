# Firestore Data Model — Chain of Title

Three top-level collections.

## `manifests`
One document per production submission.
manifests/{manifest_id}
production: string
submitted_by: string
submitted_at: timestamp
shots: array of {
shot_id: string
description: string
ai_tool: string # must match a tool_registry.name
}
status: "pending" | "processed"

## `tool_registry`
One document per known AI tool. Seeded from `seed_registry.json`.
tool_registry/{tool_id}
name: string
vendor: string
category: string
status: "cleared" | "flagged" | "needs_review" | "discontinued"
evidence: string # required -- never write a status with no evidence
source_note: string # "per public reporting -- not a legal determination"

## `audit_log`
One document per decision, written only by the Governance Agent, consumed
from a local Kafka (Redpanda) topic. Append-only — never update or delete
an entry.
audit_log/{entry_id}
manifest_id: string # references manifests/{manifest_id}
shot_id: string
tool_name: string
agent: "verification" | "remediation"
decision: string
reasoning: string # evidence text behind the decision
confidence: number # 0-1, present for verification-driven entries
timestamp: timestamp

## Why three collections, not one

`manifests` is write-heavy and per-production. `tool_registry` is read-heavy
and shared across every production. `audit_log` is append-only and must
never be edited by anything except the Governance Agent — keeping it a
separate collection makes that guarantee easy to enforce with Firestore
security rules later, rather than relying on application code discipline
alone.
