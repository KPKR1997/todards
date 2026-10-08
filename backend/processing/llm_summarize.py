import json
import logging
import re
from typing import Optional

from backend.core.ollama_client import OllamaClient
from backend.core.schemas import SummaryResponse
from config.settings import OLLAMA_BASE_URL, OLLAMA_MODEL

logger = logging.getLogger("todards.summarize")


class LlmSummarizer:

    def __init__(
        self,
        base_url=None,
        model=None,
        client: Optional[OllamaClient] = None
    ):
        self.base_url = base_url or OLLAMA_BASE_URL
        self.model = model or OLLAMA_MODEL
        self.client = client or OllamaClient(
            base_url=self.base_url,
            model=self.model,
            options={
                "num_predict": 300,
            }
        )
    def _clean_summary(self, summary: str) -> str:
        """
        Clean accidental formatting returned by the LLM.

        Final output must contain only the summary text.
        """

        if not summary:
            return ""

        summary = summary.strip()

        # Remove markdown code fences
        summary = re.sub(
            r"^```(?:json|text|markdown)?\s*",
            "",
            summary,
            flags=re.IGNORECASE
        )

        summary = re.sub(
            r"\s*```$",
            "",
            summary
        )

        summary = summary.strip()

        # ---------------------------------------------------------
        # Handle JSON object accidentally returned by the LLM
        # ---------------------------------------------------------
        if summary.startswith("{") and summary.endswith("}"):
            try:
                parsed = json.loads(summary)

                if isinstance(parsed, dict):
                    value = parsed.get("summary")

                    if isinstance(value, str):
                        summary = value.strip()

            except (json.JSONDecodeError, TypeError):
                pass

        # ---------------------------------------------------------
        # Handle simple Python/JSON-style wrapper:
        #
        # {"summary": "...."}
        # ---------------------------------------------------------
        if summary.lower().startswith('"summary"'):
            match = re.match(
                r'^["\']?summary["\']?\s*:\s*["\']?(.*?)["\']?$',
                summary,
                flags=re.IGNORECASE | re.DOTALL
            )

            if match:
                summary = match.group(1).strip()

        # ---------------------------------------------------------
        # Remove accidental surrounding quotation marks
        # ---------------------------------------------------------
        if (
            len(summary) >= 2
            and summary[0] in ('"', "'")
            and summary[-1] == summary[0]
        ):
            summary = summary[1:-1].strip()

        # ---------------------------------------------------------
        # Remove accidental labels
        # ---------------------------------------------------------
        prefixes = [
            "summary:",
            "summary -",
            "summary —",
            "here is the summary:",
            "here's the summary:",
        ]

        lower_summary = summary.lower()


        for prefix in prefixes:
            if lower_summary.startswith(prefix):
                summary = summary[len(prefix):].strip()
                break

        summary = summary.translate(str.maketrans("", "", "}{[]=,:;"))



        return summary.strip()

    def summarize(
        self,
        content: str,
        historical_context: Optional[str] = None
    ) -> str:

        context_block = ""

        if historical_context:
            context_block = f"""
HISTORICAL CONTEXT:
{historical_context}

Use this context only when it helps explain the current
development. Do not treat historical context as part of
today's article unless the current article supports it.
"""

        prompt = f"""
You are a professional news journalist writing for Todards.

Summarize the news article below in ONE natural paragraph.

The summary must:

- Use short, direct sentences.
- Prefer common everyday words over formal or academic language.
- Avoid phrases such as "amid", "underscores", "significant test",
  "economic implications", "move ahead with", "sparked debate",
  "faces uncertainty", and similar formal wording when simpler
  alternatives are available.
- Keep most sentences under 20 words.
- Explain one idea at a time.
- Write as if explaining the news to an intelligent 15-year-old
  who has no specialist knowledge.
- Prefer active voice.
- Do not make the writing sound like a newspaper editorial.

If historical context is provided, use it only when it genuinely
helps explain the current development.

Do not use bullet points, headings, labels, or commentary.

IMPORTANT:
The output value must contain ONLY the summary paragraph.
Do not output JSON.
Do not output braces.
Do not output the word "summary".
Do not output quotation marks.
Do not output markdown or code fences.
Do not write "Here is the summary" or similar text.

NEWS ARTICLE:
{content}

{context_block}
"""

        try:
            res = self.client.generate(
                prompt=prompt,
                response_model=SummaryResponse,
                role="system"
            )

            if res and res.summary:
                return self._clean_summary(res.summary)

        except Exception as e:
            logger.warning(
                f"Structured summary extraction failed: {e}. "
                "Falling back to raw response."
            )

        try:
            raw = self.client.generate_raw(
                prompt=prompt,
                role="system"
            )

            return self._clean_summary(raw)

        except Exception as e:
            logger.error(
                f"All summary extraction attempts failed: {e}"
            )
            raise