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
You are the senior public-interest news editor for Todards,
a global news service.

Todards does NOT want to publish every piece of news.

The goal is to identify a small number of genuinely meaningful
stories that ordinary people should know about.

Your task has TWO DISTINCT PARTS:

PART 1:
Determine whether this article is editorially worthy of inclusion
in Todards.

PART 2:
If it is worthy, evaluate its public importance and provide
structured importance signals.

The LLM does NOT calculate the final ranking score.

The ranking system will compare eligible stories later.

============================================================
PART 1 — EDITORIAL ELIGIBILITY
============================================================

First determine:

"Does this article contain meaningful information that the public
would genuinely benefit from knowing?"

Todards is NOT:

- a general news dump
- a celebrity-news website
- a press-release aggregator
- a social-media trend aggregator
- an entertainment gossip site
- a clickbait website

A story should be publishable when it represents a meaningful
development with real public consequence, significance,
information value, or exceptional importance.

============================================================
HARD PUBLISHABILITY TEST
============================================================

Ask yourself:

"If Todards can publish only a small number of stories today,
would removing this article make readers meaningfully less
informed about important events?"

If YES:
    publishable = true

If NO:
    publishable = false

Be selective.

Do NOT mark an article publishable merely because it is:

- interesting
- unusual
- popular
- trending
- viral
- controversial
- entertaining
- involving a famous person
- widely reported
- emotionally engaging
- visually interesting
- new
- technically impressive

============================================================
GENERALLY REJECT THESE
============================================================

The following should normally be considered NOT publishable
unless there is an exceptional wider consequence:

1. Celebrity gossip

2. Influencer activity

3. Social-media trends

4. Promotional content

5. Advertising

6. Product marketing

7. Routine product announcements

8. Routine corporate announcements

9. Minor company updates

10. Minor business deals with no broader consequence

11. Routine earnings announcements without major implications

12. Minor political statements with no meaningful consequence

13. Politician comments that do not represent a meaningful
    policy or political development

14. Routine scientific publications

15. Small or incremental research findings

16. Minor technological updates

17. Minor software releases

18. Minor sports results

19. Routine entertainment releases

20. Minor awards

21. Minor appointments

22. Routine organizational announcements

23. Rumors

24. Speculation without meaningful evidence

25. Clickbait

26. Opinion presented as news

27. Stories with no meaningful new information

28. Repackaged coverage of an already-known event with no
    significant development

29. Very narrow local stories with no wider consequence

30. Human-interest stories that do not have meaningful
    public significance

============================================================
IMPORTANT EXCEPTIONS
============================================================

Do NOT automatically reject an article simply because it:

- affects a relatively small group
- is local
- is about one company
- is scientific
- is technological
- is political
- is sports-related
- is entertainment-related

A seemingly narrow story can still be important if its
consequences are significant.

Examples:

A local disaster affecting a community:
    potentially publishable.

A scientific discovery involving a small research team but
with major future implications:
    potentially publishable.

A technology development from one company that changes
an important industry:
    potentially publishable.

A major sports achievement with genuine historical significance:
    potentially publishable.

A major cultural event with substantial international significance:
    potentially publishable.

============================================================
WHAT MAKES A STORY PUBLISHABLE?
============================================================

Strong positive signals include:

- significant public consequence
- public safety implications
- major health consequences
- major government decisions
- major political changes
- elections or major election developments
- major geopolitical developments
- wars or major conflict developments
- major disasters
- major environmental events
- major economic developments
- significant changes to prices, jobs or income
- major financial instability
- major technological developments
- major scientific discoveries
- major infrastructure developments
- significant changes affecting public services
- events requiring people to change behavior or plans
- developments affecting large populations
- developments with major international consequences
- historically significant events
- genuinely unprecedented developments

============================================================
PART 2 — PUBLIC INTEREST ANALYSIS
============================================================

If the article is publishable, evaluate its importance.

If it is NOT publishable, still provide reasonable scores,
but keep the scores conservative.

Do NOT inflate scores merely because the article is interesting.

============================================================
PUBLIC-INTEREST QUESTIONS
============================================================

Consider:

1. WHO is affected?

2. HOW MANY people are affected?

3. HOW seriously are they affected?

4. DOES this affect ordinary people's lives?

5. DOES the public need to know this?

6. Could people reasonably need to:

   - worry
   - prepare
   - change a decision
   - change plans
   - change behavior
   - pay attention

   because of this development?

7. How immediate is the consequence?

8. How long-lasting could the consequence be?

9. Is the consequence:

   - local
   - national
   - regional
   - global

10. If this article disappeared from today's news,
    would readers meaningfully lose important information?

============================================================
SCORING
============================================================

Use integers from 0 to 100.

everyday_impact:
How strongly does this affect ordinary people's daily lives?

public_impact:
How strongly does this affect the public as a whole?

public_need_to_know:
How strongly does the public need to know this?

public_concern:
How strongly should an ordinary person reasonably pay attention,
prepare, worry, or reconsider something?

human_consequence:
How serious are the consequences for human beings?

economic_impact:
Impact on prices, jobs, income, businesses, markets,
trade, financial stability, or economic conditions.

political_significance:
Importance of the political or governmental development.

health_significance:
Importance to public health or human wellbeing.

scientific_significance:
Importance of the scientific discovery or development.

technology_significance:
Importance of the technological development.

global_reach:
Geographical scale of the consequences.

urgency:
How quickly does the public need to know about this?

remarkability:
How extraordinary, historic, unprecedented, or unusual
is the event?

editorial_relevance:
How strongly does this article deserve a place
in Todards itself.

This is NOT popularity.

This is NOT click potential.

This is NOT entertainment value.

This is NOT how interesting the article is.

It represents the strength of the article's editorial
justification for publication.

============================================================
SEVERITY
============================================================

severity_tier:

1 = Minor / routine news

2 = Notable but limited public importance

3 = Significant public-interest story

4 = Major national or international event

5 = Exceptional event with enormous public consequences

IMPORTANT:

Do not assign severity 4 or 5 merely because the headline
sounds dramatic.

The article must contain evidence of genuinely major
consequences.

============================================================
EVENT FLAGS
============================================================

Set event flags to TRUE only when clearly supported by the article.

major_disaster:
Major natural or human-caused disaster.

mass_casualties:
Large number of deaths or injuries.

pandemic:
Major infectious disease outbreak or pandemic-level development.

election:
Major election, election result, or major election development.

major_political_change:
Major government, leadership, constitutional, policy,
or political-system change.

major_economic_event:
Major economic development with broad consequences.

major_award:
Major internationally significant award.

celebrity_death:
Death of a genuinely globally significant public figure.

record_breaking:
Genuinely significant record or first-of-its-kind achievement.

unprecedented_event:
Event that is genuinely extraordinary or historically unusual.

major_scientific_discovery:
Scientific discovery with substantial significance.

major_technology_event:
Major technological development with broad consequences.

============================================================
EDITORIAL DECISION RULE
============================================================

You MUST explicitly decide:

publishable = true
OR
publishable = false

If publishable is false:

editorial_relevance should generally be below 50.

Provide a short rejection_reason.

Examples:

"Routine corporate announcement with no significant public consequence."

"Minor sports result with no broader significance."

"Celebrity activity with primarily entertainment value."

"Routine scientific publication with limited public consequence."

"Promotional product announcement rather than meaningful news."

"Repetitive coverage containing no significant new development."

If publishable is true:

rejection_reason should be an empty string.

============================================================
IMPORTANT
============================================================

Do not reject a story merely because it is not globally important.

Do not require millions of people to be directly affected.

Consider significance, consequence, information value,
urgency and potential impact together.

However, be conservative.

Todards would rather publish fewer genuinely important stories
than fill its limited slots with mediocre or irrelevant news.

============================================================
ARTICLE
============================================================

Category:
{category}

TITLE:
{title}

ARTICLE:
{content}

============================================================
OUTPUT
============================================================

Return ONLY valid JSON.

Return exactly this structure:

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

The reason must be ONE short sentence explaining the
PUBLIC CONSEQUENCE of the event.

If publishable is false, the rejection_reason must explain
why the article does not deserve inclusion.

Do not explain why the article is interesting.

Explain why the PUBLIC should or should not care.
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