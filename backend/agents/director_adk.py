"""
Director (ADK) -- ADK-native replacement for director.run_pipeline().

Per shot, runs a real ADK SequentialAgent of three deterministic custom
BaseAgent steps: VerificationStep -> RemediationStep -> PublishStep. Each
step is a plain Python function call, not an LLM-driven tool selection --
verification and remediation are compliance-critical and must never be
subject to model judgment about whether to run.

Reuses the existing, independently-tested verify_tool/write_hold functions
and director.py's _get_db/_publish_decision/_aggregate_verdict, so no
Verification/Remediation/Kafka logic is duplicated here.

Same input/output contract as director.run_pipeline(manifest_id) -- this
is a drop-in replacement once parity-tested against it.
"""
import sys
import asyncio
import logging
from pathlib import Path
from typing import AsyncGenerator

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.adk.agents import BaseAgent, SequentialAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.adk.sessions import InMemorySessionService
from google.adk import Runner
from google.genai import types

from agents.verification_agent import verify_tool
from agents.remediation_agent import write_hold
from agents.director import _get_db, _publish_decision, _aggregate_verdict

logging.basicConfig(
    level=logging.INFO,
    format="[director_adk] %(levelname)s %(message)s",
    force=True,
)
logger = logging.getLogger(__name__)


class VerificationStep(BaseAgent):
    """Deterministically checks the current shot's tool against the registry.
    Not an LlmAgent -- verification must never be subject to model judgment."""

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        tool_name = ctx.session.state.get("tool_name")
        result = verify_tool(tool_name)
        yield Event(
            author=self.name,
            actions=EventActions(state_delta={"verification_result": result}),
        )


class RemediationStep(BaseAgent):
    """Writes a hold (+ notification + substitute) if the shot didn't clear.
    No-ops for cleared shots -- keeps this a plain SequentialAgent instead
    of needing custom branching control flow."""

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        verification_result = state.get("verification_result", {})
        status = verification_result.get("status")

        hold = None
        if status != "cleared":
            hold = write_hold(
                state.get("manifest_id"),
                state.get("shot_id"),
                state.get("tool_name"),
                verification_result,
            )

        yield Event(
            author=self.name,
            actions=EventActions(state_delta={"hold": hold}),
        )


class PublishStep(BaseAgent):
    """Publishes the shot's decision to Kafka for the Governance Agent to
    consume. Best-effort -- publish failures are logged, not raised, same
    as the original director.py."""

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        verification_result = state.get("verification_result", {})

        _publish_decision({
            "decision": verification_result.get("status"),
            "tool": verification_result.get("matched_name") or state.get("tool_name"),
            "manifest_id": state.get("manifest_id"),
            "shot_id": state.get("shot_id"),
            "reasoning": verification_result.get("evidence"),
            "agent": "verification",
            "confidence": verification_result.get("match_confidence"),
        })

        yield Event(author=self.name)


shot_pipeline = SequentialAgent(
    name="chain_of_title_shot_pipeline",
    description="Verifies, remediates, and publishes a decision for one shot, in strict order.",
    sub_agents=[
        VerificationStep(name="verification_step"),
        RemediationStep(name="remediation_step"),
        PublishStep(name="publish_step"),
    ],
)

_session_service = InMemorySessionService()
_kickoff = types.Content(role="user", parts=[types.Part(text="run")])


async def _run_shot_async(manifest_id: str, shot_id: str, tool_name: str) -> dict:
    session = await _session_service.create_session(
        app_name="chain_of_title",
        user_id="director",
        state={
            "manifest_id": manifest_id,
            "shot_id": shot_id,
            "tool_name": tool_name,
        },
    )
    runner = Runner(
        app_name="chain_of_title",
        agent=shot_pipeline,
        session_service=_session_service,
    )
    async for _event in runner.run_async(
        user_id="director", session_id=session.id, new_message=_kickoff
    ):
        pass  # side effects happen via state_delta; we just need it to finish

    final_session = await _session_service.get_session(
        app_name="chain_of_title", user_id="director", session_id=session.id
    )
    return final_session.state


def run_pipeline_adk(manifest_id: str) -> dict:
    """
    ADK-native replacement for director.run_pipeline(). Same contract, same
    return shape -- runs each shot through a real ADK SequentialAgent
    (VerificationStep -> RemediationStep -> PublishStep) instead of a plain
    Python loop calling the three functions directly.

    Raises:
        ValueError: if no manifest with this id exists.
    """
    db = _get_db()
    manifest_doc = db.collection("manifests").document(manifest_id).get()
    if not manifest_doc.exists:
        raise ValueError(f"Manifest '{manifest_id}' not found.")

    manifest = manifest_doc.to_dict()
    shots = manifest.get("shots", [])

    shot_results = []
    statuses = []

    for shot in shots:
        shot_id = shot.get("shot_id")
        tool_name = shot.get("ai_tool")

        final_state = asyncio.run(_run_shot_async(manifest_id, shot_id, tool_name))

        verification_result = final_state.get("verification_result", {})
        status = verification_result.get("status")
        hold = final_state.get("hold")
        statuses.append(status)

        shot_results.append({
            "shot_id": shot_id,
            "tool_name": tool_name,
            "status": status,
            "evidence": verification_result.get("evidence"),
            "hold_id": hold["hold_id"] if hold else None,
            "suggested_substitute": hold["suggested_substitute"] if hold else None,
        })

        logger.info("shot=%s tool=%s status=%s", shot_id, tool_name, status)

    verdict = _aggregate_verdict(statuses)

    db.collection("manifests").document(manifest_id).update({"status": "processed"})

    result = {
        "manifest_id": manifest_id,
        "verdict": verdict,
        "shots": shot_results,
    }
    logger.info("ADK pipeline complete for manifest=%s verdict=%s", manifest_id, verdict)
    return result


if __name__ == "__main__":
    import json
    if len(sys.argv) < 2:
        print("Usage: python director_adk.py <manifest_id>")
        sys.exit(1)

    result = run_pipeline_adk(sys.argv[1])
    print(json.dumps(result, indent=2))
