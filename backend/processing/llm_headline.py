import logging
from typing import Optional

from backend.core.ollama_client import OllamaClient
from backend.core.schemas import HeadlineResponse
from config.settings import OLLAMA_BASE_URL, OLLAMA_MODEL

logger = logging.getLogger("todards.headline")


class LlmHeadlineEditor:

    def __init__(self, base_url=None, model=None, client: Optional[OllamaClient] = None):
        self.base_url = base_url or OLLAMA_BASE_URL
        self.model = model or OLLAMA_MODEL
        self.client = client or OllamaClient(
            base_url=self.base_url,
            model=self.model
        )

    def _chat(self, system_prompt: str) -> str:
        """
        Send a request to Ollama and return the generated headline.
        Uses Pydantic structured output with fallback.
        """
        try:
            res = self.client.generate(
                prompt=system_prompt,
                response_model=HeadlineResponse,
                role="system"
            )

            if res and res.headline:
                return self._clean_headline(res.headline)

        except Exception as e:
            logger.warning(
                f"Structured headline generation failed: {e}. "
                "Falling back to raw response."
            )

        try:
            raw = self.client.generate_raw(
                prompt=system_prompt,
                role="system"
            )
            return self._clean_headline(raw)

        except Exception as e:
            logger.error(f"Headline generation failed: {e}")
            raise

    def _clean_headline(self, headline: str) -> str:
        """
        Final programmatic cleanup.
        """
        if not headline:
            return ""

        headline = headline.strip()

        # Remove markdown code fences
        headline = headline.replace("```json", "")
        headline = headline.replace("```text", "")
        headline = headline.replace("```", "")
        headline = headline.strip()

        # Remove surrounding quotation marks
        if (
            len(headline) >= 2
            and headline[0] in ('"', "'")
            and headline[-1] == headline[0]
        ):
            headline = headline[1:-1].strip()

        return headline

    def write_headline(self, content: str, remarks: str) -> str:
        """
        Generate the initial headline.
        """

        system_prompt = f"""
You are a professional news headline writer for Todards.

Write ONE clear headline for the news article below.

EDITORIAL CONTEXT:
{remarks}

Follow these principles:

- Clearly tell the reader what happened or what was discovered.
- Use simple, everyday English that a general reader can understand.
- Avoid jargon, complicated words, vague phrases, and unnecessary details.
- Focus only on the main news development.
- Include important names, places, organizations, or numbers when they help explain the story.
- Be factual and do not add anything that is not supported by the article.
- Keep the tone neutral and professional.
- Do not use clickbait, sensational language, questions, or teaser phrases.
- Keep the headline natural and concise.
- The headline MUST contain 14 words or fewer.

The headline should make sense to someone who reads ONLY the headline.

OUTPUT:
Return exactly one headline in the "headline" field.
Do not provide explanations, alternatives, labels, or quotation marks.

NEWS ARTICLE:
{content}
"""

        return self._chat(system_prompt)

    def validate_headline(self, content: str, headline: str) -> str:
        """
        Review and improve an existing headline only when necessary.
        """

        system_prompt = f"""
You are a professional news headline editor for Todards.

Review the existing headline against the news article.

If the headline is already clear, accurate, natural, and within
14 words, return it EXACTLY as it is.

Otherwise, make only the changes needed to improve it.

Use these principles:

- Make the main news development immediately clear.
- Use simple, everyday English.
- Avoid jargon, complicated words, vague wording, and unnecessary words.
- Keep important names, places, organizations, and numbers when useful.
- Do not add facts or change the meaning of the article.
- Keep the tone neutral and professional.
- Remove clickbait, sensational, emotional, or teaser language.
- Keep the final headline natural and concise.
- The final headline MUST contain 14 words or fewer.

Do not rewrite a good headline just to make it different.

OUTPUT:
Return exactly one headline in the "headline" field.
Return no explanation, comments, alternatives, labels, or quotation marks.

NEWS ARTICLE:
{content}

EXISTING HEADLINE:
{headline}
"""

        return self._chat(system_prompt)