"""
image_generator.py — Generate images from prompts via DALL-E 3, Stability AI, or Replicate.
"""

from __future__ import annotations

import base64
import time
from pathlib import Path

import requests

from .config import get_secret
from .logger import get_logger

log = get_logger(__name__)


class ImageGenerator:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        self.ig_cfg = cfg["image_generation"]
        self.output_dir = Path(self.ig_cfg["output_dir"])
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, prompt: str, filename_stem: str) -> Path:
        """Generate an image from *prompt* and return the local file path."""
        provider = self.ig_cfg["provider"]
        dest = self.output_dir / f"{filename_stem}.png"

        if dest.exists():
            log.info(f"Image already exists: {dest}")
            return dest

        log.info(f"Generating image via {provider}: {filename_stem}")

        if provider == "openai_dalle":
            return self._dalle(prompt, dest)
        elif provider == "stability_ai":
            return self._stability(prompt, dest)
        elif provider == "replicate":
            return self._replicate(prompt, dest)
        else:
            raise ValueError(f"Unknown image generation provider: '{provider}'")

    # ------------------------------------------------------------------
    # DALL-E 3
    # ------------------------------------------------------------------

    def _dalle(self, prompt: str, dest: Path) -> Path:
        from openai import OpenAI
        c = self.ig_cfg["openai_dalle"]
        client = OpenAI(api_key=get_secret("OPENAI_API_KEY"))

        response = client.images.generate(
            model=c.get("model", "dall-e-3"),
            prompt=prompt,
            size=c.get("size", "1792x1024"),
            quality=c.get("quality", "hd"),
            style=c.get("style", "vivid"),
            n=1,
            response_format="b64_json",
        )

        image_data = base64.b64decode(response.data[0].b64_json)
        dest.write_bytes(image_data)
        log.info(f"Image saved: {dest}")
        return dest

    # ------------------------------------------------------------------
    # Stability AI
    # ------------------------------------------------------------------

    def _stability(self, prompt: str, dest: Path) -> Path:
        c = self.ig_cfg["stability_ai"]
        api_key = get_secret("STABILITY_API_KEY")
        model = c.get("model", "stable-diffusion-xl-1024-v1-0")
        url = f"https://api.stability.ai/v1/generation/{model}/text-to-image"

        payload = {
            "text_prompts": [{"text": prompt, "weight": 1.0}],
            "cfg_scale": c.get("cfg_scale", 7),
            "steps": c.get("steps", 40),
            "width": c.get("width", 1344),
            "height": c.get("height", 768),
            "samples": 1,
        }

        resp = requests.post(
            url,
            headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

        image_data = base64.b64decode(data["artifacts"][0]["base64"])
        dest.write_bytes(image_data)
        log.info(f"Image saved: {dest}")
        return dest

    # ------------------------------------------------------------------
    # Replicate
    # ------------------------------------------------------------------

    def _replicate(self, prompt: str, dest: Path) -> Path:
        import replicate as rep
        c = self.ig_cfg["replicate"]

        output = rep.run(
            c.get("model", "black-forest-labs/flux-1.1-pro"),
            input={
                "prompt": prompt,
                "width": c.get("width", 1344),
                "height": c.get("height", 768),
                "num_inference_steps": c.get("num_inference_steps", 28),
                "guidance": c.get("guidance", 3.5),
                "output_format": "png",
            },
        )

        image_url = str(output)
        resp = requests.get(image_url)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        log.info(f"Image saved: {dest}")
        return dest
