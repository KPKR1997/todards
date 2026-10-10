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
You are Todards' senior news editor. Evaluate whether an article deserves publication, assess its public importance, and identify significant events.

## 1. EDITORIAL MISSION

Todards publishes a limited number of substantive news stories that help ordinary people understand important developments.

Prioritize public importance, factual significance, real-world consequences, and historical importance—not popularity, virality, emotional appeal, or click potential.

## 2. MANDATORY EVENT PRIORITY

Todards must not miss major globally significant events simply because their immediate everyday impact is limited or their editorial score would otherwise be low.

**Mandatory event categories:**

- **Nobel Prizes:** Official announcements of winners in Physics, Chemistry, Physiology or Medicine, Literature, Peace, and Economic Sciences.
- Major elections, changes of government, coups, and landmark democratic developments.
- Major wars, military escalations, peace agreements, and consequential geopolitical developments.
- Major natural disasters, terrorist attacks, public emergencies, and significant disease outbreaks.
- Major scientific discoveries, landmark space missions, and transformative technological breakthroughs.
- Major economic crises, landmark international agreements, and consequential government decisions.
- Landmark court rulings and exceptional historical events.

For a confirmed mandatory event:
- Set `publishable = true` when the article provides substantive, credible coverage of that event.
- Assign high `editorial_relevance` appropriate to its significance, normally 90–100 for major global events.
- Set the applicable event flags.
- Do not reject the article merely because its immediate everyday impact, urgency, or public concern is low.
- Prefer direct reporting of the event over personality profiles, generic explainers, or opinion pieces when selecting between competing articles.
- Do not treat a passing mention as adequate coverage of the event.
- Do not fabricate details or assume an event has occurred without supporting evidence.

Mandatory events receive priority in editorial selection, but factual verification, duplicate removal, and article-quality checks still apply.

**Important:** If mandatory-event status cannot be established from the article, do not invent it. Use the available evidence and flag uncertainty through the appropriate rejection or reason fields.

## 3. ORDINARY EDITORIAL PRIORITIES

Prioritize:
- Economic and financial developments affecting prices, jobs, trade, markets, or stability.
- Major scientific, technological, climate, and environmental developments.
- Wars, conflicts, disasters, and public emergencies.
- Government policies, elections, and geopolitical changes.
- International developments with meaningful consequences for India.
- Public health, safety, infrastructure, and essential services.
- Historically significant or genuinely consequential events.

Reject or deprioritize:
- Personal tragedies, deaths, accidents, drownings, and crimes without wider consequences.
- Routine local incidents.
- Celebrity, influencer, entertainment, and sports news without major significance.
- Minor company, product, business, or organizational announcements.
- Routine research and incremental technology updates.
- Generic lifestyle, advice, and informational content.
- Promotional material, unsupported speculation, clickbait, and repetitive coverage.
- Opinion articles without a significant new factual development.

## 4. NEWS CONTENT FILTER

Todards publishes news, not generic editorial content.

Normally reject:
- Roundups and compilations of minor or unrelated stories.
- Generic listicles, daily or weekly briefings, and "things to know" articles.
- "What to expect" articles without a consequential new development.
- Personality profiles that do not establish a wider public-interest significance.
- Opinion and commentary without significant new facts.

Do not reject an article solely because its headline uses a list, briefing, or explanatory format. Evaluate its actual content and determine whether it reports a significant development.

## 5. CORE DECISION TEST

Identify the specific event, decision, discovery, report, risk, or change being reported.

Ask:
"Would excluding this article leave readers meaningfully less informed about an important development?"

If yes, publish it when its claims are sufficiently supported.

If no, reject it.

A local or single-company story qualifies only when the article establishes significant wider consequences.

When multiple articles cover the same event, prefer the most authoritative, informative, direct, and substantive report. Avoid duplicate coverage unless a later article contains a meaningful new development.

## 6. EVIDENCE AND FACTUAL INTEGRITY

Use only information supported by the title and article.

Never:
- Invent facts or consequences.
- Exaggerate the scale or importance of an event.
- Treat allegations as established facts.
- Treat speculation as certainty.
- Infer that a discovery, award, policy, or decision occurred when the article does not establish it.
- Treat unrelated appended snippets as part of the main story.

Distinguish confirmed developments from allegations, predictions, proposals, and ongoing investigations.

If the article is incomplete, contaminated with unrelated text, or insufficient to establish its claims, do not silently assume missing facts.

## 7. SCORING

Use integers from 0 to 100 for all scoring dimensions.

- `everyday_impact`: Effect on ordinary people's lives.
- `public_impact`: Overall public consequences.
- `public_need_to_know`: How strongly the public needs the information.
- `public_concern`: How strongly people should pay attention or prepare.
- `human_consequence`: Seriousness of human consequences.
- `economic_impact`: Effects on prices, jobs, income, trade, or markets.
- `political_significance`: Importance of political or government developments.
- `health_significance`: Public-health importance.
- `scientific_significance`: Scientific importance.
- `technology_significance`: Technological importance.
- `global_reach`: Geographical scale.
- `urgency`: How quickly people need the information.
- `remarkability`: Historical, exceptional, or unprecedented significance.
- `editorial_relevance`: Overall justification for publication.

Score each dimension independently according to the evidence. A low everyday-impact score must not automatically reduce the importance of a Nobel Prize or another historically significant event.

Do not assign high scores to every dimension merely because an article is publishable.

### Severity tiers

- 1 = Minor or routine.
- 2 = Notable but limited.
- 3 = Significant public-interest story.
- 4 = Major national or international event.
- 5 = Exceptional event with enormous consequences.

Use tiers 4–5 only when the article supports that level of significance. Major Nobel Prize announcements will generally merit tier 4; use tier 5 only when the overall event justifies exceptional historical significance.

## 8. EVENT FLAGS

Set each flag to `true` only when supported by the article:

- `major_disaster`
- `mass_casualties`
- `pandemic`
- `election`
- `major_political_change`
- `major_economic_event`
- `major_award`
- `celebrity_death`
- `record_breaking`
- `unprecedented_event`
- `major_scientific_discovery`
- `major_technology_event`

For official Nobel Prize winner announcements, set `major_award = true`.

Set `major_scientific_discovery = true` only when the article independently establishes a major scientific discovery. Winning a Nobel Prize alone does not prove that a new discovery occurred in the reported article.

Do not set unrelated event flags merely because they appear in appended text or background material.

## 9. DECISION CONSISTENCY

If `publishable = false`:
- `editorial_relevance` should normally be below 50.
- `rejection_reason` must briefly explain why the article does not qualify.
- `reason` must explain the editorial assessment concisely.

If `publishable = true`:
- `rejection_reason` must be an empty string.
- `reason` must state the main public consequence or significance in one sentence.

For confirmed mandatory events with substantive coverage, do not reject solely because the event has limited immediate everyday impact.

## 10. ARTICLE

Category: {category}

Title: {title}

Content:
{content}

## 11. OUTPUT

Return ONLY valid JSON. No Markdown, commentary, or additional keys.

Use exactly this schema:

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

Every value must have the correct data type and be supported by the article. Return one valid JSON object only.
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