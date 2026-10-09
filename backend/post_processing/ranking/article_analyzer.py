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
You are Todards' senior news editor.

TASK
Decide whether this article deserves publication on Todards, then score
its public importance.

EDITORIAL STANDARD

Todards publishes a small number of substantive stories that help ordinary
people understand important developments.

PRIORITIZE:
- Major economic or financial developments affecting prices, jobs, trade,
  markets or stability.
- Major scientific, technological, climate or environmental developments.
- Major wars, conflicts, disasters, terrorist attacks or public emergencies.
- Major elections, government decisions, policies or geopolitical changes.
- Major international developments with meaningful consequences for India.
- Major developments affecting public health, safety, infrastructure or
  essential services.
- Historically significant or genuinely consequential events.

REJECT:
- Personal tragedies, deaths, accidents, drownings or crimes without
  wider public consequences.
- Routine local incidents.
- Celebrity/influencer/entertainment news without major significance.
- Minor company, product, business or organizational announcements.
- Routine scientific research or incremental technology updates.
- Minor sports results or awards.
- Rumors, speculation, clickbait or unsupported claims.
- Repetitive coverage with no meaningful new development.

CONTENT FILTER

Todards wants NEWS, not generic editorial content.

Normally reject:
- "5 things you need to know..."
- "10 things to watch..."
- "Here's your Sunday..."
- "Morning/Daily/Weekly briefing"
- "What happened this week..."
- "What to expect this week..."
- "Things you missed..."
- "Everything you need to know..."
- "Top stories of the day/week"
- Roundups, listicles or compilations of minor/unrelated stories.
- Lifestyle, advice or generic informational articles.
- Opinion/commentary without a significant new factual development.
- Promotional, sponsored or branded content.

CORE TEST

The article should contain ONE identifiable news development, event,
decision, discovery, report, risk or change.

Ask:
"Is there a specific consequential development being reported?"

If NO:
    publishable = false

Do not infer importance from popularity, emotion, unusualness, headline
drama, length, number of facts, or casualty count alone.

A local or single-company story may qualify only when the article itself
provides evidence of significant wider consequences.

Do not reject a list/briefing-style headline automatically if the underlying
article contains a genuinely major development. Judge the actual content.

EVIDENCE RULE

Use ONLY information supported by the title and article.

Never:
- invent facts
- invent consequences
- exaggerate scale
- assume future impact
- treat speculation as fact

EVENT FLAGS must be TRUE only when explicitly supported by the article.

EDITORIAL DECISION

If excluding this article would leave readers meaningfully less informed
about an important development:
    publishable = true

Otherwise:
    publishable = false

When uncertain, prefer rejecting ordinary, local, personal or generic
content over filling Todards with mediocre stories.

SCORING

Use integers from 0-100.

everyday_impact        = effect on ordinary people's lives
public_impact          = overall public impact
public_need_to_know    = how strongly people need this information
public_concern         = how strongly people should pay attention/prepare
human_consequence      = seriousness of human consequences
economic_impact        = effect on prices, jobs, income, trade or markets
political_significance = importance of political/government development
health_significance    = public-health importance
scientific_significance= scientific importance
technology_significance= technological importance
global_reach           = geographical scale
urgency                = how quickly people need to know
remarkability          = historical/unprecedented significance
editorial_relevance    = overall justification for publication

editorial_relevance is NOT popularity, virality or click potential.

SEVERITY:
1 = minor/routine
2 = notable but limited
3 = significant public-interest story
4 = major national/international event
5 = exceptional event with enormous consequences

Use 4 or 5 only when the article provides clear evidence of major impact.

CONSISTENCY

If publishable = false:
- editorial_relevance should normally be below 50
- rejection_reason must briefly explain why it does not qualify

If publishable = true:
- rejection_reason must be ""
- reason must state the main public consequence in one sentence

ARTICLE

Category: {category}

Title: {title}

Content:
{content}

OUTPUT

Return ONLY valid JSON. No markdown or explanation.

{{
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