"""
Todards Pipeline — Content Guardrails

Evaluates scraped articles using Ollama to filter out:
1. NSFW / Adult / Explicit content
2. Toxicity, abuse, violence glorification, hate speech
3. Gossip, unverified rumors, clickbait misinformation
4. Propaganda and spam

Articles failing guardrails are removed from the pipeline before ranking.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple

from backend.core.ollama_client import OllamaClient
from backend.core.schemas import GuardrailResponse
from config.settings import OLLAMA_BASE_URL, OLLAMA_MODEL, GUARDRAIL_ENABLED

logger = logging.getLogger("todards.guardrails")


class ContentGuardrails:
    """
    Automated content moderation and editorial quality gate.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        client: Optional[OllamaClient] = None,
        enabled: bool = GUARDRAIL_ENABLED,
    ):
        self.enabled = enabled
        self.client = client or OllamaClient(
            base_url=base_url or OLLAMA_BASE_URL,
            model=model or OLLAMA_MODEL,
        )

    def check_article(self, article: Dict[str, Any]) -> GuardrailResponse:
        """
        Evaluate a single article for safety, factuality, and quality.
        """
        if not self.enabled:
            return GuardrailResponse(
                is_safe=True,
                is_factual=True,
                is_neutral=True,
                flags=[],
                reason="Guardrails disabled",
            )

        title = article.get("title", "")
        content = article.get("content", "")

        prompt = f"""
You are an editorial standards and safety reviewer for Todards, a reputable global news digest.

Your task is to screen the following news piece for editorial safety, factual integrity, and decency.

Evaluate against these criteria:

1. SAFETY (is_safe):
- Is it free from NSFW, adult, sexually explicit material, graphic violence, extreme abuse, or hate speech?
- Set is_safe to FALSE if it contains explicit adult content, vulgarity, or gratuitous graphic gore.

2. FACTUALITY (is_factual):
- Is this legitimate news or informative reporting, rather than unverified celebrity gossip, unfounded conspiracy theories, or pure sensational rumors?
- Set is_factual to FALSE if the text is pure tabloid gossip, unverified wild rumors, or obvious fake news.

3. NEUTRALITY (is_neutral):
- Is this informative journalism rather than spam, commercial advertorial disguise, or extreme toxic propaganda?
- Set is_neutral to FALSE if it is blatant spam or toxic hate propaganda.

TITLE:
{title}

CONTENT:
{content}

Analyze the article and return structured JSON matching the schema.
If any criterion fails, provide clear flags (e.g. "nsfw_content", "gossip_rumor", "toxic_propaganda") and a brief reason.
"""

        try:
            res = self.client.generate(
                prompt=prompt,
                response_model=GuardrailResponse,
                role="system",
            )
            return res
        except Exception as e:
            logger.warning(
                f"Guardrail evaluation error for article '{title[:40]}...': {e}. Defaulting to safe pass."
            )
            return GuardrailResponse(
                is_safe=True,
                is_factual=True,
                is_neutral=True,
                flags=[],
                reason="Default pass due to evaluation timeout/error",
            )

    def filter_articles(
        self,
        articles: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Filter a list of articles.
        Returns:
            (passed_articles, rejected_articles_with_reasons)
        """
        if not self.enabled:
            return articles, []

        passed = []
        rejected = []

        for art in articles:
            evaluation = self.check_article(art)

            is_acceptable = evaluation.is_safe and evaluation.is_factual and evaluation.is_neutral

            if is_acceptable:
                passed.append(art)
            else:
                art_with_reason = dict(art)
                art_with_reason["guardrail_flags"] = evaluation.flags
                art_with_reason["guardrail_reason"] = evaluation.reason
                rejected.append(art_with_reason)
                logger.info(
                    f"Guardrail REJECTED: '{art.get('title', '')[:50]}' | "
                    f"Flags: {evaluation.flags} | Reason: {evaluation.reason}"
                )

        return passed, rejected
