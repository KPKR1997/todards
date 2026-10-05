import json
import requests


class ArticleAnalyzer:
    """
    Uses Ollama to analyze the importance of a news article.

    Ollama does NOT decide the final ranking score.
    It only extracts structured importance signals.
    """

    def __init__(
        self,
        url="http://localhost:11434",
        model="llama3:latest",
        timeout=120,
    ):
        self.url = url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def _build_prompt(self, article):
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

    def _extract_json(self, text):

        text = text.strip()

        # Remove markdown code fences if Ollama adds them.
        if text.startswith("```"):
            lines = text.splitlines()

            if lines:
                lines = lines[1:]

            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]

            text = "\n".join(lines).strip()

        # Find JSON object if there is extra text.
        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end == -1:
            raise ValueError(
                "No JSON object found in Ollama response."
            )

        text = text[start:end + 1]

        return json.loads(text)

    def analyze(self, article):

        prompt = self._build_prompt(article)

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "stream": False,
            "format": "json",
        }

        response = requests.post(
            f"{self.url}/api/chat",
            json=payload,
            timeout=self.timeout,
        )

        response.raise_for_status()

        result = response.json()

        content = (
            result
            .get("message", {})
            .get("content", "")
        )

        if not content:
            raise ValueError(
                "Empty response received from Ollama."
            )

        analysis = self._extract_json(content)

        return self._validate(analysis)

    def _validate(self, analysis):

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