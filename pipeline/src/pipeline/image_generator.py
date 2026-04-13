"""Image generation with style rotation via Replicate or DALL-E."""

from __future__ import annotations

import random
from pathlib import Path

import replicate
import structlog
import yaml
from sqlalchemy.orm import Session

from .config import ImageGenerationConfig
from .db import Artifact, ArtifactVersion

logger = structlog.get_logger()


class ImageGenerator:
    def __init__(self, config: ImageGenerationConfig, session: Session):
        self.config = config
        self.db = session
        self.style_prompts = self._load_style_prompts()

    def generate(
        self,
        artifact: Artifact,
        context: str,
        prompt_focus: str,
        style_name: str | None = None,
        pipeline_run_id: int | None = None,
    ) -> ArtifactVersion:
        """Generate an image for an artifact, creating an ArtifactVersion."""
        if style_name is None:
            style_name = self._pick_style()

        full_prompt = self._build_prompt(context, prompt_focus, style_name)

        url = self._generate_image(full_prompt, artifact.subtype or "illustration")

        # Determine version number
        max_version = (
            self.db.query(ArtifactVersion)
            .filter_by(artifact_id=artifact.id)
            .count()
        )

        version = ArtifactVersion(
            artifact_id=artifact.id,
            version_number=max_version + 1,
            pipeline_run_id=pipeline_run_id,
            url=url,
            generation_prompt=full_prompt,
            context_mode=self.config.styles.default,
            style_name=style_name,
            style_source="random_rotation" if style_name != self.config.styles.default else "config_default",
            image_model=self._get_model_for_subtype(artifact.subtype),
            status="generated",
        )
        self.db.add(version)
        self.db.flush()

        artifact.current_version_id = version.id
        artifact.status = "generated"
        self.db.flush()

        logger.info(
            "image_gen.created",
            artifact_id=artifact.id,
            version=version.version_number,
            style=style_name,
        )
        return version

    def _build_prompt(self, context: str, prompt_focus: str, style_name: str) -> str:
        base = self.style_prompts.get("base", "")
        style = self.style_prompts.get("styles", {}).get(style_name, "")

        return f"""{base}

{style}

Content context: {context}

Visual focus: {prompt_focus}"""

    def _pick_style(self) -> str:
        enabled = self.config.styles.enabled
        rotation = self.config.styles.rotation

        if rotation == "random_per_image":
            return random.choice(enabled)
        return self.config.styles.default

    def _get_model_for_subtype(self, subtype: str | None) -> str:
        return self.config.replicate.model

    def _generate_image(self, prompt: str, subtype: str) -> str:
        """Call Replicate API to generate the image."""
        model = self._get_model_for_subtype(subtype)

        output = replicate.run(
            model,
            input={
                "prompt": prompt,
                "aspect_ratio": "16:9",
                "output_quality": 90,
            },
        )

        # Replicate returns a URL or list of URLs
        if isinstance(output, list):
            return str(output[0])
        return str(output)

    def _load_style_prompts(self) -> dict:
        prompts_path = Path(__file__).parent.parent.parent / "prompts" / "image_system_prompt.yaml"
        if prompts_path.exists():
            with open(prompts_path) as f:
                return yaml.safe_load(f) or {}
        return {}
