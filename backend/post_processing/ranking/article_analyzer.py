import json
import logging
from typing import Optional, Dict, Any

from backend.core.ollama_client import OllamaClient
from backend.core.schemas import ArticleAnalysisResponse
from config.settings import OLLAMA_BASE_URL, OLLAMA_MODEL


logger = logging.getLogger("todards.analyzer")


class ArticleAnalyzer:
    """
    Analyzes whether a news article deserves inclusion in Todards
    and extracts structured public-interest signals.

    The analyzer performs two separate tasks:

    1. EDITORIAL GATE
       Determines whether the article is genuinely worth publishing.

    2. IMPORTANCE ANALYSIS
       Scores the article across multiple public-interest dimensions.

    The LLM does NOT calculate the final ranking score.

    Ranking is handled by the ranking layer.

    Important:
        An article that is not editorially relevant should have
        publishable=False and should be removed before ranking.
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

    # ============================================================
    # PROMPT
    # ============================================================

    def _build_prompt(self, article: Dict[str, Any]) -> str:

        title = article.get("title", "")
        content = article.get("content", "")
        category = article.get("category", "")

        prompt = f"""
You are Todards' senior news editor. Evaluate whether an article deserves publication based on public importance, then score its significance.

## EDITORIAL MISSION

Todards publishes a limited number of substantive news stories that help ordinary people understand important developments.

**PRIORITIZE**
- Major economic, financial, political, geopolitical or government developments.
- Major scientific discoveries, space missions, technological breakthroughs and environmental developments.
- Wars, major conflicts, disasters, terrorist attacks and public emergencies.
- Developments affecting public health, safety, infrastructure or essential services.
- International developments with meaningful consequences for India.
- Major awards and historically significant events, including Nobel Prize announcements in Physics, Chemistry, Physiology or Medicine, Literature, Peace, and Economic Sciences.
- Other major awards or discoveries when their significance is clearly established.

**REJECT**
- Routine local incidents, personal tragedies and crimes without wider consequences.
- Celebrity, entertainment, sports or organizational news without major public significance.
- Minor company announcements, product launches and incremental research or technology updates.
- Generic advice, lifestyle content, opinion pieces, promotional material, clickbait, unsupported speculation and roundups lacking a major factual development.

## DECISION RULES

1. Identify the specific news development reported in the article.
2. Judge its actual public, scientific, economic, political, technological or historical importance—not popularity, emotional appeal, headline drama or length.
3. Use only facts supported by the title and article. Never invent consequences, exaggerate significance or treat speculation as fact.
4. Recognize established high-significance events. Nobel Prize announcements, major scientific discoveries, landmark government decisions and exceptional international events can qualify even when their immediate everyday impact is limited.
5. Do not automatically accept or reject a story based on its category, award status, headline format or the presence of a famous person. Evaluate the actual development.
6. Reject stories that provide no identifiable consequential development. A local or single-organization story qualifies only when its wider significance is supported by evidence.
7. If publishable is false, editorial_relevance should normally be below 50, and rejection_reason must briefly explain the decision.
8. If publishable is true, rejection_reason must be an empty string, and reason must state the principal significance in one sentence.
9. Use integer scores from 0 to 100. Score each dimension independently according to the article's evidence. A high score in one dimension does not automatically justify high scores in others.
10. Severity tiers: 1 = minor, 2 = notable but limited, 3 = significant public interest, 4 = major national/international event, 5 = exceptional event with enormous consequences. Reserve tiers 4–5 for evidence-supported significance.

## SCORING DIMENSIONS

- everyday_impact: effect on ordinary people's lives
- public_impact: overall public consequences
- public_need_to_know: importance of public awareness
- public_concern: need for attention or preparation
- human_consequence: seriousness of human consequences
- economic_impact: effects on prices, jobs, income, trade or markets
- political_significance: importance of political or government developments
- health_significance: public-health importance
- scientific_significance: scientific importance
- technology_significance: technological importance
- global_reach: geographical scale
- urgency: how quickly the information is needed
- remarkability: historical, exceptional or unprecedented significance
- editorial_relevance: overall justification for publication, not popularity or click potential

## EVENT FLAGS

Set a flag to true only when supported by the article:
major_disaster, mass_casualties, pandemic, election, major_political_change, major_economic_event, major_award, celebrity_death, record_breaking, unprecedented_event, major_scientific_discovery, major_technology_event.

For major_award, recognize major internationally significant awards, explicitly including Nobel Prizes. Do not set major_scientific_discovery to true merely because an award is given; assess the discovery separately.

## ARTICLE

Category: {category}
Title: {title}
Content:
{content}

## OUTPUT

Return only valid JSON matching this schema. Use the exact keys, correct data types, integer scores, boolean event flags, and no additional keys. Every value must be supported by the article.

{
  "editorial_relevance": 0,
  "publishable": false,
  "rejection_reason": "",
  "everyday_impact": 0,
  "public_impact": 0,
  "public_need_to_know": 0,
  "public_concern": 0,
  "human_consequence": 0,
  "economic_impact": 0,
  "political_significance": 0,
  "health_significance": 0,
  "scientific_significance": 0,
  "technology_significance": 0,
  "global_reach": 0,
  "urgency": 0,
  "remarkability": 0,
  "severity_tier": 1,
  "events": {
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
  },
  "reason": ""
}
Every value must be supported by the article.
Do not fabricate missing information.
"""

        return prompt

    # ============================================================
    # JSON EXTRACTION
    # ============================================================

    def _extract_json(self, text: str) -> dict:
        """
        Extract JSON from an Ollama response.

        Handles:
        - raw JSON
        - ```json ... ```
        - surrounding explanatory text
        """

        text = text.strip()

        # Remove markdown code fences
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
            raise ValueError(
                "No JSON object found in Ollama response."
            )

        text = text[start:end + 1]

        return json.loads(text)

    # ============================================================
    # ANALYZE
    # ============================================================

    def analyze(self, article: Dict[str, Any]) -> dict:

        prompt = self._build_prompt(article)

        # --------------------------------------------------------
        # PRIMARY: STRUCTURED OUTPUT
        # --------------------------------------------------------

        try:

            res = self.client.generate(
                prompt=prompt,
                response_model=ArticleAnalysisResponse,
                role="user",
            )

            return self._validate(res.model_dump())

        except Exception as e:

            logger.warning(
                f"Structured article analysis failed: {e}. "
                f"Falling back to raw response."
            )

        # --------------------------------------------------------
        # FALLBACK: RAW JSON
        # --------------------------------------------------------

        try:

            raw = self.client.generate_raw(
                prompt=prompt,
                role="user",
            )

            parsed = self._extract_json(raw)

            return self._validate(parsed)

        except Exception as e:

            logger.error(
                f"Article analysis failed completely: {e}"
            )

            return self._default_analysis()

    # ============================================================
    # DEFAULT ANALYSIS
    # ============================================================

    def _default_analysis(self) -> dict:

        return {
            "editorial_relevance": 0,
            "publishable": False,
            "rejection_reason": (
                "Article analysis failed and therefore the article "
                "is not eligible for ranking."
            ),

            "everyday_impact": 0,
            "public_impact": 0,
            "public_need_to_know": 0,
            "public_concern": 0,

            "human_consequence": 0,
            "economic_impact": 0,
            "political_significance": 0,
            "health_significance": 0,
            "scientific_significance": 0,
            "technology_significance": 0,

            "global_reach": 0,
            "urgency": 0,
            "remarkability": 0,

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

            "reason": (
                "Analysis failed, so the article was not considered "
                "eligible for publication."
            ),
        }

    # ============================================================
    # VALIDATION
    # ============================================================

    def _validate(self, analysis: dict) -> dict:

        # --------------------------------------------------------
        # SCORE FIELDS
        # --------------------------------------------------------

        score_fields = [
            "editorial_relevance",
            "everyday_impact",
            "public_impact",
            "public_need_to_know",
            "public_concern",
            "human_consequence",
            "economic_impact",
            "political_significance",
            "health_significance",
            "scientific_significance",
            "technology_significance",
            "global_reach",
            "urgency",
            "remarkability",
        ]

        for field in score_fields:

            value = analysis.get(field, 0)

            try:
                value = int(value)

            except (ValueError, TypeError):

                value = 0

            analysis[field] = max(
                0,
                min(100, value),
            )

        # --------------------------------------------------------
        # PUBLISHABLE
        # --------------------------------------------------------

        publishable = analysis.get(
            "publishable",
            False,
        )

        if isinstance(publishable, str):

            publishable = (
                publishable.strip().lower()
                in {
                    "true",
                    "yes",
                    "1",
                    "publish",
                    "publishable",
                }
            )

        else:

            publishable = bool(publishable)

        analysis["publishable"] = publishable

        # --------------------------------------------------------
        # REJECTION REASON
        # --------------------------------------------------------

        rejection_reason = analysis.get(
            "rejection_reason",
            "",
        )

        if not isinstance(rejection_reason, str):
            rejection_reason = str(rejection_reason)

        analysis["rejection_reason"] = rejection_reason.strip()

        # --------------------------------------------------------
        # REASON
        # --------------------------------------------------------

        reason = analysis.get(
            "reason",
            "",
        )

        if not isinstance(reason, str):
            reason = str(reason)

        analysis["reason"] = reason.strip()

        # --------------------------------------------------------
        # SAFETY RULE
        # --------------------------------------------------------
        #
        # If the model says publishable=False, make sure the
        # editorial relevance does not contradict that decision.
        #
        # We do NOT automatically reject based on score because
        # publishability is an editorial judgement.
        # --------------------------------------------------------

        if not analysis["publishable"]:

            if not analysis["rejection_reason"]:

                analysis["rejection_reason"] = (
                    "The article does not have sufficient public "
                    "significance for Todards."
                )

        # --------------------------------------------------------
        # SEVERITY
        # --------------------------------------------------------

        try:

            tier = int(
                analysis.get(
                    "severity_tier",
                    1,
                )
            )

        except (ValueError, TypeError):

            tier = 1

        analysis["severity_tier"] = max(
            1,
            min(5, tier),
        )

        # --------------------------------------------------------
        # EVENT FLAGS
        # --------------------------------------------------------

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

        events = analysis.get(
            "events",
            {},
        )

        if not isinstance(events, dict):
            events = {}

        for key, default in default_events.items():

            value = events.get(
                key,
                default,
            )

            if isinstance(value, str):

                value = (
                    value.strip().lower()
                    in {
                        "true",
                        "yes",
                        "1",
                    }
                )

            else:

                value = bool(value)

            events[key] = value

        analysis["events"] = events

        # --------------------------------------------------------
        # FINAL NORMALIZATION
        # --------------------------------------------------------

        return analysis