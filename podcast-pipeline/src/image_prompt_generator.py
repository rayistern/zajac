"""
image_prompt_generator.py — Use an LLM to convert a chapter into a rich image generation prompt.
"""

from __future__ import annotations

from .chapter_splitter import Chapter
from .config import get_secret, load_prompts, format_prompt
from .logger import get_logger

log = get_logger(__name__)


class ImagePromptGenerator:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        self.ip_cfg = cfg["image_prompt"]
        self.prompts = load_prompts()
        self.max_length = self.ip_cfg.get("max_length", 800)
        self.style_suffix = self.ip_cfg.get("style_suffix", "")

    def generate(
        self,
        chapter: Chapter,
        episode_title: str,
        podcast_title: str,
        total_chapters: int,
    ) -> str:
        """Generate an image prompt for the given chapter."""
        log.info(f"Generating image prompt for chapter {chapter.number}: '{chapter.title}'")

        prompt_tmpl = self.prompts["image_prompt"]

        user_prompt = format_prompt(
            prompt_tmpl["user"],
            podcast_title=podcast_title,
            episode_title=episode_title,
            chapter_number=chapter.number,
            chapter_total=total_chapters,
            chapter_title=chapter.title,
            chapter_summary=chapter.summary,
            chapter_excerpt=chapter.excerpt,
            style_suffix=self.style_suffix,
        )
        system_prompt = prompt_tmpl["system"]

        raw = self._call_llm(system_prompt, user_prompt)
        prompt = raw.strip()

        if len(prompt) > self.max_length:
            prompt = prompt[: self.max_length].rsplit(" ", 1)[0]

        log.debug(f"Image prompt: {prompt[:120]}…")
        return prompt

    def _call_llm(self, system: str, user: str) -> str:
        llm_cfg = self.ip_cfg["llm"]
        provider = llm_cfg.get("provider", "anthropic")
        model = llm_cfg.get("model", "claude-sonnet-4-6")

        if provider == "anthropic":
            from anthropic import Anthropic
            client = Anthropic(api_key=get_secret("ANTHROPIC_API_KEY"))
            response = client.messages.create(
                model=model,
                max_tokens=1024,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return response.content[0].text

        elif provider == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=get_secret("OPENAI_API_KEY"))
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            return response.choices[0].message.content

        elif provider == "google":
            import google.generativeai as genai
            genai.configure(api_key=get_secret("GOOGLE_API_KEY"))
            model_obj = genai.GenerativeModel(model, system_instruction=system)
            response = model_obj.generate_content(user)
            return response.text

        else:
            raise ValueError(f"Unknown LLM provider: '{provider}'")
