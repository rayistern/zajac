"""Image generation with style rotation via OpenRouter (default) or Replicate."""

from __future__ import annotations

import base64
import os
import random
from pathlib import Path

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
        self._openai_client = None
        self._replicate_imported = False

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
        url_or_data = self._generate_image(full_prompt)
        model_id = self._active_model()

        max_version = (
            self.db.query(ArtifactVersion)
            .filter_by(artifact_id=artifact.id)
            .count()
        )

        version = ArtifactVersion(
            artifact_id=artifact.id,
            version_number=max_version + 1,
            pipeline_run_id=pipeline_run_id,
            url=url_or_data,
            generation_prompt=full_prompt,
            context_mode=self.config.styles.default,
            style_name=style_name,
            style_source="random_rotation" if style_name != self.config.styles.default else "config_default",
            image_model=model_id,
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
            model=model_id,
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

    def _active_model(self) -> str:
        if self.config.provider == "openrouter":
            return self.config.openrouter.model
        return self.config.replicate.model

    def _generate_image(self, prompt: str) -> str:
        """Dispatch to the configured provider. Returns URL or data URI."""
        if self.config.provider == "openrouter":
            return self._generate_via_openrouter(prompt)
        if self.config.provider == "replicate":
            return self._generate_via_replicate(prompt)
        raise ValueError(f"Unknown image provider: {self.config.provider}")

    def _generate_via_openrouter(self, prompt: str) -> str:
        """OpenRouter chat completions with image output. Returns data URI."""
        if self._openai_client is None:
            from openai import OpenAI
            api_key = os.environ.get("OPENROUTER_API_KEY", "")
            if not api_key:
                raise RuntimeError("OPENROUTER_API_KEY not set — cannot call OpenRouter")
            self._openai_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
            )

        model = self.config.openrouter.model
        resp = self._openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            modalities=["image", "text"],
        )

        # OpenRouter returns images in message.images[] as data URIs
        message = resp.choices[0].message
        images = getattr(message, "images", None) or []
        if images:
            first = images[0]
            # Image may be {"type": "image_url", "image_url": {"url": "data:image/..;base64,..."}}
            if isinstance(first, dict):
                url = first.get("image_url", {}).get("url") or first.get("url")
                if url:
                    return url
        # Fallback: some models put the image in content as a data URI
        content = message.content or ""
        if isinstance(content, str) and content.startswith("data:image"):
            return content

        logger.warning("image_gen.no_image_in_response", model=model)
        return ""

    def _generate_via_replicate(self, prompt: str) -> str:
        """Legacy: call Replicate API. Requires REPLICATE_API_TOKEN."""
        if not self._replicate_imported:
            import replicate  # noqa: F401
            self._replicate_imported = True
        import replicate

        output = replicate.run(
            self.config.replicate.model,
            input={
                "prompt": prompt,
                "aspect_ratio": "16:9",
                "output_quality": 90,
            },
        )
        if isinstance(output, list):
            return str(output[0])
        return str(output)

    def _load_style_prompts(self) -> dict:
        prompts_path = Path(__file__).parent.parent.parent / "prompts" / "image_system_prompt.yaml"
        if prompts_path.exists():
            with open(prompts_path) as f:
                return yaml.safe_load(f) or {}
        return {}
