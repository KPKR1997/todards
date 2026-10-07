import json
import logging
from typing import Optional, Dict, Any

from backend.core.ollama_client import OllamaClient
from backend.core.schemas import ArticleAnalysisResponse
from config.settings import OLLAMA_BASE_URL, OLLAMA_MODEL

logger = logging.getLogger("todards.analyzer")


class ArticleAnalyzer:
    """
    Uses Ollama to analyze the importance of a news article.

    Ollama does NOT decide the final ranking score.
    It only extracts structured importance signals.
    """

    def __init__(
        self,
        url=None,
        model=None,
        timeout=120,
        client: Optional[OllamaClient] = None,
    ):
        self.url = (url or OLLAMA_BASE_URL).rstrip("/")
        self.model = model or OLLAMA_MODEL
        self.timeout = timeout
        self.client = client or OllamaClient(
            base_url=self.url,
            model=self.model,
            timeout=self.timeout,
        )

    def _build_prompt(self, article: Dict[str, Any]) -> str:
        title = article.get("title", "")
        content = article.get("content", "")
        category = article.get("category", "")

        prompt = f"""
You are a professional global news editor.

Your job is to evaluate the IMPORTANCE of this news article for
an ordinary user who wants to know the most important news TODAY.

Do NOT judge importance based merely on popularity or sensationalism.

Prioritize:
- Events that affect everyday life
- Events that people should not miss
- Major economic consequences
- Major political consequences
- Major public health consequences
- Large disasters and casualties
- Wars and major geopolitical events
- Major elections
- Major government changes
- Major international events
- Extraordinary or unprecedented events
- Important scientific discoveries
- Major technological developments
- Major cultural events
- Major awards
- Death of globally significant public figures
- Events with significant global consequences

Category:
{category}

TITLE:
{title}

ARTICLE:
{content}

Return ONLY valid JSON.

Use integers from 0 to 100 for every score.

Return exactly this structure:

{{
    "everyday_impact": 0,
    "dont_miss": 0,
    "human_consequence": 0,
    "economic_impact": 0,
    "political_significance": 0,
    "health_significance": 0,
    "scientific_significance": 0,
    "entertainment_significance": 0,
    "remarkability": 0,
    "global_reach": 0,
    "urgency": 0,

    "severity_tier": 1,

    "events": {{
        "major_disaster": false,
        "mass_casualties": false,
        "pandemic": false,
        "election": false,
        "major_political_change": false,
        "major_economic_event": false,
        "major_award": false,
        "celebrity_death": false,
        "record_breaking": false,
        "unprecedented_event": false,
        "major_scientific_discovery": false,
        "major_technology_event": false
    }},

    "reason": ""
}}

Severity tier:

1 = ordinary news
2 = notable news
3 = significant event
4 = major national/international event
5 = extremely important global event

The "reason" must be a short explanation of why this article matters.
"""
        return prompt

    def _extract_json(self, text: str) -> dict:
        text = text.strip()

        if text.startswith("```"):
            lines = text.splitlines()
            if lines:
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end == -1:
            raise ValueError("No JSON object found in Ollama response.")

        text = text[start:end + 1]
        return json.loads(text)

    def analyze(self, article: Dict[str, Any]) -> dict:
        prompt = self._build_prompt(article)

        try:
            res = self.client.generate(
                prompt=prompt,
                response_model=ArticleAnalysisResponse,
                role="user",
            )
            return res.model_dump()
        except Exception as e:
            logger.warning(
                f"Structured article analysis failed: {e}. Falling back to raw response."
            )

        try:
            raw = self.client.generate_raw(prompt=prompt, role="user")
            parsed = self._extract_json(raw)
            return self._validate(parsed)
        except Exception as e:
            logger.error(f"Article analysis failed completely: {e}")
            # Return baseline fallback dict
            return self._default_analysis()

    def _default_analysis(self) -> dict:
        return {
            "everyday_impact": 0,
            "dont_miss": 0,
            "human_consequence": 0,
            "economic_impact": 0,
            "political_significance": 0,
            "health_significance": 0,
            "scientific_significance": 0,
            "entertainment_significance": 0,
            "remarkability": 0,
            "global_reach": 0,
            "urgency": 0,
            "severity_tier": 1,
            "events": {
                "major_disaster": False,
                "mass_casualties": False,
                "pandemic": False,
                "election": False,
                "major_political_change": False,
                "major_economic_event": False,
                "major_award": False,
                "celebrity_death": False,
                "record_breaking": False,
                "unprecedented_event": False,
                "major_scientific_discovery": False,
                "major_technology_event": False,
            },
            "reason": "Default fallback analysis due to LLM error.",
        }

    def _validate(self, analysis: dict) -> dict:
        score_fields = [
            "everyday_impact",
            "dont_miss",
            "human_consequence",
            "economic_impact",
            "political_significance",
            "health_significance",
            "scientific_significance",
            "entertainment_significance",
            "remarkability",
            "global_reach",
            "urgency",
        ]

        for field in score_fields:
            value = analysis.get(field, 0)
            try:
                value = int(value)
            except (ValueError, TypeError):
                value = 0
            value = max(0, min(100, value))
            analysis[field] = value

        try:
            tier = int(analysis.get("severity_tier", 1))
        except (ValueError, TypeError):
            tier = 1

        analysis["severity_tier"] = max(1, min(5, tier))

        default_events = {
            "major_disaster": False,
            "mass_casualties": False,
            "pandemic": False,
            "election": False,
            "major_political_change": False,
            "major_economic_event": False,
            "major_award": False,
            "celebrity_death": False,
            "record_breaking": False,
            "unprecedented_event": False,
            "major_scientific_discovery": False,
            "major_technology_event": False,
        }

        events = analysis.get("events", {})
        if not isinstance(events, dict):
            events = {}

        for key, default in default_events.items():
            events[key] = bool(events.get(key, default))

        analysis["events"] = events

        reason = analysis.get("reason", "")
        if not isinstance(reason, str):
            reason = str(reason)
        analysis["reason"] = reason.strip()

        return analysis