"""LLM audit for stale, orphaned, or duplicate artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timedelta

import structlog
from sqlalchemy.orm import Session

from .db import Artifact, ArtifactVersion, ReconciliationFlag, SourceUnit
from .llm import LLMClient

logger = structlog.get_logger()


class ReconciliationEngine:
    def __init__(self, model: str, require_human_approval: bool, session: Session):
        self.model = model
        self.require_human_approval = require_human_approval
        self.db = session
        self.client = LLMClient(model)

    def audit(self, source_unit: SourceUnit) -> list[ReconciliationFlag]:
        """Audit all artifacts for a source unit for lifecycle issues."""
        artifacts = (
            self.db.query(Artifact)
            .filter_by(source_unit_id=source_unit.id)
            .all()
        )
        if not artifacts:
            return []

        flags = []
        flags.extend(self._check_stale_superseded(artifacts))
        flags.extend(self._check_orphaned(artifacts))
        flags.extend(self._check_duplicates(artifacts, source_unit))
        flags.extend(self._check_never_published(artifacts))

        for flag in flags:
            self.db.add(flag)
        self.db.flush()

        logger.info(
            "reconciliation.audit_done",
            ref=source_unit.sefaria_ref,
            flags=len(flags),
        )
        return flags

    def _check_stale_superseded(self, artifacts: list[Artifact]) -> list[ReconciliationFlag]:
        """Find artifacts whose plans have been superseded but remain published."""
        flags = []
        for a in artifacts:
            if a.status == "published" and a.artifact_plan_id:
                from .db import ArtifactPlan
                plan = self.db.query(ArtifactPlan).get(a.artifact_plan_id)
                if plan and plan.superseded_at:
                    flags.append(ReconciliationFlag(
                        artifact_id=a.id,
                        flag_type="stale_superseded",
                        reason=f"Plan {plan.id} was superseded on {plan.superseded_at}",
                        llm_recommendation="review",
                        requires_human_approval=self.require_human_approval,
                    ))
        return flags

    def _check_orphaned(self, artifacts: list[Artifact]) -> list[ReconciliationFlag]:
        """Find artifacts with no active plan."""
        flags = []
        for a in artifacts:
            if a.artifact_plan_id is None and a.status not in ("hidden", "rejected"):
                flags.append(ReconciliationFlag(
                    artifact_id=a.id,
                    flag_type="orphaned",
                    reason="Artifact has no associated plan",
                    llm_recommendation="review",
                    requires_human_approval=self.require_human_approval,
                ))
        return flags

    def _check_duplicates(
        self, artifacts: list[Artifact], source_unit: SourceUnit
    ) -> list[ReconciliationFlag]:
        """Use LLM to detect semantically duplicate artifacts."""
        active = [a for a in artifacts if a.status in ("published", "approved", "generated")]
        if len(active) < 2:
            return []

        artifact_desc = []
        for a in active:
            version = self.db.query(ArtifactVersion).get(a.current_version_id) if a.current_version_id else None
            prompt_text = version.generation_prompt[:200] if version and version.generation_prompt else "N/A"
            artifact_desc.append({
                "id": a.id,
                "subtype": a.subtype,
                "priority": a.priority,
                "prompt": prompt_text,
            })

        prompt = f"""Review these artifacts for {source_unit.sefaria_ref} and identify
any that are semantically duplicates (covering the same visual concept):

{json.dumps(artifact_desc, ensure_ascii=False, indent=2)}

Return a JSON array of duplicate pairs:
[{{"id_keep": 1, "id_remove": 2, "reason": "both depict..."}}]

Return [] if no duplicates found."""

        duplicates = self._parse_json(self.client.complete(prompt, max_tokens=1024))
        flags = []
        for dup in duplicates:
            flags.append(ReconciliationFlag(
                artifact_id=dup.get("id_remove", active[0].id),
                flag_type="duplicate_type",
                reason=dup.get("reason", "LLM detected duplicate"),
                llm_recommendation="hide",
                requires_human_approval=self.require_human_approval,
            ))
        return flags

    def _check_never_published(self, artifacts: list[Artifact]) -> list[ReconciliationFlag]:
        """Flag artifacts stuck in non-terminal states for too long."""
        threshold = datetime.utcnow() - timedelta(days=7)
        flags = []
        for a in artifacts:
            if a.status in ("planned", "ordered", "generated") and a.created_at and a.created_at < threshold:
                flags.append(ReconciliationFlag(
                    artifact_id=a.id,
                    flag_type="never_published",
                    reason=f"Stuck in '{a.status}' since {a.created_at}",
                    llm_recommendation="review",
                    requires_human_approval=self.require_human_approval,
                ))
        return flags

    def _parse_json(self, text: str) -> list[dict]:
        text = text.strip()
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
        return []
