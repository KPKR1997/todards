import json
import logging
from typing import Optional, Dict, Any

from backend.core.ollama_client import OllamaClient
from backend.core.schemas import ArticleAnalysisResponse
from config.settings import OLLAMA_BASE_URL, OLLAMA_MODEL


logger = logging.getLogger("todards.analyzer")


class ArticleAnalyzer:
    """
    Analyzes how important and publicly relevant a news article is.

    The LLM does NOT calculate the final ranking score.

    Its job is to extract structured signals answering:

        1. Does this matter to ordinary people?
        2. Does this affect the public?
        3. Does the public need to know about it?
        4. Could people reasonably need to worry, prepare, or pay attention?
        5. How broad and serious are the consequences?

    Final ranking is handled by the ranking layer.
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
You are the public-interest news editor for a global news service.

Your task is NOT to determine whether an article is interesting,
popular, viral, sensational, entertaining, or likely to receive clicks.

Your task is to determine whether an ordinary person genuinely
NEEDS TO KNOW about this event.

The most important question is:

"IF A PERSON READS ONLY A FEW NEWS STORIES TODAY,
DOES THIS STORY DESERVE ONE OF THOSE LIMITED SLOTS?"

Evaluate the article from a PUBLIC-INTEREST perspective.

--------------------------------
CORE PRINCIPLE
--------------------------------

A story should receive a high importance score when:

- It affects people's daily lives.
- It affects public safety or security.
- It affects health or wellbeing.
- It affects jobs, income, prices, economy, infrastructure, or services.
- It represents a major political or governmental development.
- It represents a major war, conflict, disaster, or geopolitical development.
- People may need to change their behavior, plans, decisions, or expectations.
- People should reasonably be aware of the development.
- A large number of people are affected.
- The consequences are serious, immediate, widespread, or long-lasting.
- The event has major international consequences.
- The event represents a genuinely extraordinary or historic development.

--------------------------------
IMPORTANT DISTINCTIONS
--------------------------------

Do NOT confuse:

POPULARITY
with
PUBLIC IMPORTANCE.

Do NOT confuse:

VIRALITY
with
PUBLIC CONSEQUENCE.

Do NOT confuse:

CELEBRITY INTEREST
with
PUBLIC NEED TO KNOW.

Do NOT give a high score merely because:

- the headline is dramatic
- the person is famous
- many websites reported it
- it is trending
- it is controversial
- it is entertaining
- it is unusual

A story can be interesting but still have LOW public importance.

--------------------------------
THE PUBLIC-INTEREST TEST
--------------------------------

Ask these questions internally:

1. WHO is affected?

2. HOW MANY people are affected?

3. HOW seriously are they affected?

4. DOES this affect ordinary people's lives?

5. DOES the public need to know this?

6. Could people reasonably need to WORRY, PREPARE,
   CHANGE A DECISION, or PAY ATTENTION because of it?

7. How immediate is the consequence?

8. How long-lasting could the consequence be?

9. Is the consequence local, national, regional, or global?

10. If this article disappeared from today's news,
    would the public meaningfully lose important information?

--------------------------------
SCORING
--------------------------------

Use integers from 0 to 100.

everyday_impact:
How strongly does this affect ordinary people's daily lives?

public_impact:
How strongly does this affect the public as a whole?

public_need_to_know:
How strongly does the public NEED to know this?

public_concern:
How strongly should an ordinary person reasonably
pay attention, worry, prepare, or reconsider something?

human_consequence:
How serious are the consequences for human beings?

economic_impact:
Impact on prices, jobs, income, businesses, markets,
trade, financial stability, or economic conditions.

political_significance:
Importance of the political/governmental development.

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

--------------------------------
SEVERITY
--------------------------------

severity_tier:

1 = Minor / routine news
2 = Notable but limited public importance
3 = Significant public-interest story
4 = Major national or international event
5 = Exceptional event with enormous public consequences

--------------------------------
NEGATIVE SIGNALS
--------------------------------

Be conservative.

A story should generally receive LOW public importance when:

- It affects only a small group with no wider consequence.
- It is primarily celebrity gossip.
- It is primarily entertainment.
- It is promotional content.
- It is a routine corporate announcement.
- It is a minor political statement with no meaningful consequence.
- It is a routine scientific publication with limited immediate importance.
- It is a minor sports result.
- It is merely trending on social media.
- It is speculation without meaningful evidence.
- It repeats an already-known development without significant new information.

--------------------------------
EVENT FLAGS
--------------------------------

Set event flags to TRUE only when clearly supported by the article.

major_disaster:
Major natural or human-caused disaster.

mass_casualties:
Large number of deaths or injuries.

pandemic:
Major infectious disease outbreak or pandemic-level development.

election:
Major election, election result, or election development.

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

--------------------------------
ARTICLE
--------------------------------

Category:
{category}

TITLE:
{title}

ARTICLE:
{content}

--------------------------------
OUTPUT
--------------------------------

Return ONLY valid JSON.

Return exactly this structure:

{{
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

The reason must be one short sentence explaining the
PUBLIC CONSEQUENCE of the event.

Do not explain why the article is interesting.
Explain why the PUBLIC should or should not care.
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
            raise ValueError(
                "No JSON object found in Ollama response."
            )

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

            return self._validate(res.model_dump())

        except Exception as e:
            logger.warning(
                f"Structured article analysis failed: {e}. "
                f"Falling back to raw response."
            )

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

    def _default_analysis(self) -> dict:
        return {
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
                "Default fallback analysis due to LLM error."
            ),
        }

    def _validate(self, analysis: dict) -> dict:

        score_fields = [
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
            events[key] = bool(
                events.get(key, default)
            )

        analysis["events"] = events

        reason = analysis.get("reason", "")

        if not isinstance(reason, str):
            reason = str(reason)

        analysis["reason"] = reason.strip()

        return analysis