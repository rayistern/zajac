"""LLM-driven artifact planning: generates manifest per source unit."""

from __future__ import annotations

import json
from datetime import datetime

import structlog
from sqlalchemy.orm import Session

from .config import ArtifactPlanningConfig
from .db import Artifact, ArtifactPlan, ArtifactType, SourceUnit
from .llm import LLMClient

logger = structlog.get_logger()


class ArtifactPlanner:
    def __init__(self, config: ArtifactPlanningConfig, session: Session):
        self.config = config
        self.db = session
        self.client = LLMClient(config.llm.model)
        self.model = config.llm.model

    def plan(
        self,
        source_unit: SourceUnit,
        context: str,
        class_id: int | None = None,
        existing_artifacts: list[Artifact] | None = None,
    ) -> ArtifactPlan:
        """Generate artifact manifest for a source unit."""
        # Check for existing active plan
        active_plan = (
            self.db.query(ArtifactPlan)
            .filter_by(source_unit_id=source_unit.id)
            .filter(ArtifactPlan.superseded_at.is_(None))
            .first()
        )
        if active_plan and not self._should_replan(active_plan, class_id):
            logger.info("planner.cached", ref=source_unit.sefaria_ref)
            return active_plan

        # Build existing artifacts context
        existing_context = None
        if existing_artifacts:
            existing_context = [
                {
                    "type": a.artifact_type.name if a.artifact_type else "unknown",
                    "subtype": a.subtype,
                    "priority": a.priority,
                    "status": a.status,
                }
                for a in existing_artifacts
            ]

        prompt = f"""You are planning visual artifacts for a Torah learning platform.

Source unit: {source_unit.sefaria_ref}
Source text: {source_unit.hebrew_text[:500]}

Context (synthesized): {context}

{"Existing artifacts: " + json.dumps(existing_context, ensure_ascii=False) if existing_context else "No existing artifacts."}

Plan up to {self.config.max_artifacts_per_source_unit} visual artifacts. For each, specify:
- type: always "image" (only implemented type)
- subtype: "illustration" | "diagram" | "infographic" | "chart" | "timeline"
- priority: 1 (highest) to 5 (lowest)
- position: 0.0 to 1.0 (where within the halacha's discussion this should appear)
- reason: why this artifact helps comprehension
- prompt_focus: the specific visual concept to depict
- context_mode: "FULL" or "SYNTHESIZED"

Do NOT duplicate existing artifacts. Focus on what would genuinely help a learner
understand this halacha visually.

Return JSON array:
[{{"type": "image", "subtype": "illustration", "priority": 1, "position": 0.3,
   "reason": "...", "prompt_focus": "...", "context_mode": "SYNTHESIZED"}}]"""

        plan_items = self._parse_json_response(self.client.complete(prompt, max_tokens=2048))

        # Supersede old plan if exists
        if active_plan:
            active_plan.superseded_at = datetime.utcnow()

        plan = ArtifactPlan(
            source_unit_id=source_unit.id,
            origin_class_id=class_id,
            is_override=active_plan is not None,
            plan_items=plan_items,
            llm_model=self.model,
            existing_artifacts_context=existing_context,
        )
        self.db.add(plan)
        self.db.flush()

        logger.info(
            "planner.created",
            ref=source_unit.sefaria_ref,
            plan_id=plan.id,
            items=len(plan_items),
        )
        return plan

    def create_artifacts_from_plan(
        self,
        plan: ArtifactPlan,
        source_unit: SourceUnit,
        class_id: int | None = None,
        pipeline_run_id: int | None = None,
    ) -> list[Artifact]:
        """Create Artifact records from a plan's items."""
        image_type = self.db.query(ArtifactType).filter_by(name="image").first()
        if not image_type:
            image_type = ArtifactType(name="image", is_implemented=True, description="Generated image")
            self.db.add(image_type)
            self.db.flush()

        artifacts = []
        for item in plan.plan_items or []:
            artifact = Artifact(
                source_unit_id=source_unit.id,
                class_id=class_id,
                artifact_type_id=image_type.id,
                artifact_plan_id=plan.id,
                pipeline_run_id=pipeline_run_id,
                subtype=item.get("subtype", "illustration"),
                priority=item.get("priority", 1),
                position=item.get("position", 0.5),
                status="planned",
            )
            self.db.add(artifact)
            artifacts.append(artifact)

        self.db.flush()
        logger.info("planner.artifacts_created", count=len(artifacts), plan_id=plan.id)
        return artifacts

    def _should_replan(self, plan: ArtifactPlan, class_id: int | None) -> bool:
        """Determine if replanning is needed (e.g. different class context)."""
        if class_id and plan.origin_class_id != class_id:
            return True
        return False

    def _parse_json_response(self, text: str) -> list[dict]:
        text = text.strip()
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
        logger.warning("planner.json_parse_failed", text=text[:200])
        return []
