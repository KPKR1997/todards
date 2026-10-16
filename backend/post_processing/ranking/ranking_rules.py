from datetime import datetime, timezone


class RankingRules:
    """
    Deterministic international-news ranking for Todards.

    Public methods and calculate_score() result keys are preserved.
    Scores are normalized to a 0-100 base score before small, bounded
    freshness/source/event adjustments are applied.

    Editorial intent:
    - Prioritize global significance, everyday-life impact, and knowledge value.
    - Down-rank routine local-only stories, gossip, and low-consequence novelty.
    - Keep exceptional events eligible even when their immediate local impact
      is limited.
    - Never allow ranking to make a rejected article publishable.
    """

    # Weights are normalized internally. Missing fields contribute zero.
    WEIGHTS = {
        "global_reach": 0.25,
        "everyday_impact": 0.25,
        "public_need_to_know": 0.20,
        "public_impact": 0.15,
        "economic_impact": 0.05,
        "health_significance": 0.04,
        "political_significance": 0.02,
        "scientific_significance": 0.01,
        "technology_significance": 0.01,
        "human_consequence": 0.01,
        "remarkability": 0.01,
        # Kept for compatibility if an upstream module supplies it.
        "dont_miss": 0.00,
        "entertainment_significance": 0.00,
    }

    SEVERITY_MULTIPLIERS = {
        1: 1.00,
        2: 1.02,
        3: 1.04,
        4: 1.07,
        5: 1.10,
    }

    EVENT_MULTIPLIERS = {
        "major_disaster": 1.08,
        "mass_casualties": 1.10,
        "pandemic": 1.10,
        "election": 1.04,
        "major_political_change": 1.06,
        "major_economic_event": 1.08,
        "major_award": 1.02,
        "celebrity_death": 1.01,
        "record_breaking": 1.03,
        "unprecedented_event": 1.04,
        "major_scientific_discovery": 1.06,
        "major_technology_event": 1.05,
    }

    # Small, bounded adjustments: they must not overwhelm the article's value.
    MAX_COMBINED_BOOST = 1.20

    def calculate_base_score(self, analysis):
        """Return a normalized 0-100 weighted score."""
        if not isinstance(analysis, dict):
            return 0.0

        weighted_sum = 0.0
        total_weight = 0.0

        for field, weight in self.WEIGHTS.items():
            if weight <= 0:
                continue

            value = analysis.get(field, 0)
            try:
                value = float(value)
            except (ValueError, TypeError):
                value = 0.0

            # Ignore NaN and infinities.
            if value != value or value in (float("inf"), float("-inf")):
                value = 0.0

            value = max(0.0, min(100.0, value))
            weighted_sum += value * weight
            total_weight += weight

        if total_weight <= 0:
            return 0.0

        return max(0.0, min(100.0, weighted_sum / total_weight))

    def calculate_event_multiplier(self, analysis):
        events = analysis.get("events", {})
        if not isinstance(events, dict):
            return 1.0

        # Use the strongest applicable event boost, not a product of all flags.
        multiplier = 1.0
        for event, event_multiplier in self.EVENT_MULTIPLIERS.items():
            value = events.get(event, False)
            if isinstance(value, str):
                value = value.strip().lower() in {"true", "yes", "1"}
            if value:
                multiplier = max(multiplier, event_multiplier)

        return multiplier

    def calculate_severity_multiplier(self, analysis):
        try:
            tier = int(analysis.get("severity_tier", 1))
        except (ValueError, TypeError, OverflowError):
            tier = 1

        tier = max(1, min(5, tier))
        return self.SEVERITY_MULTIPLIERS[tier]

    @staticmethod
    def _parse_article_datetime(value):
        if not value:
            return None
        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
            except ValueError:
                return None
        else:
            return None

        # Treat naive publication dates as UTC to avoid machine-local timezone
        # assumptions and make comparisons consistent.
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def calculate_freshness_multiplier(self, article):
        """Small recency adjustment; future or malformed dates get no boost."""
        if not isinstance(article, dict):
            return 1.0

        article_date = article.get("published_at") or article.get("date")
        published = self._parse_article_datetime(article_date)
        if published is None:
            return 1.0

        age_hours = (datetime.now(timezone.utc) - published).total_seconds() / 3600

        if age_hours < 0:
            return 1.0
        if age_hours <= 6:
            return 1.04
        if age_hours <= 12:
            return 1.02
        if age_hours <= 24:
            return 1.00
        if age_hours <= 48:
            return 0.97
        return 0.93

    def calculate_source_multiplier(self, source_count=1):
        """Modest corroboration bonus; source count alone is not proof."""
        try:
            count = max(1, int(source_count))
        except (ValueError, TypeError, OverflowError):
            count = 1

        if count >= 3:
            return 1.05
        if count == 2:
            return 1.025
        return 1.0

    @staticmethod
    def _has_exceptional_event(analysis):
        events = analysis.get("events", {})
        if not isinstance(events, dict):
            return False
        exceptional = {
            "major_disaster",
            "mass_casualties",
            "pandemic",
            "election",
            "major_political_change",
            "major_economic_event",
            "major_award",
            "record_breaking",
            "unprecedented_event",
            "major_scientific_discovery",
            "major_technology_event",
        }
        for name in exceptional:
            value = events.get(name, False)
            if isinstance(value, str):
                value = value.strip().lower() in {"true", "yes", "1"}
            if value:
                return True
        return False

    def _local_only_penalty(self, analysis):
        """
        Apply a substantial penalty to stories that appear local-only and have
        little public-knowledge or everyday-life value. This is a ranking
        penalty, not an automatic rejection, because global consequences may
        be under-reported by the analyzer.
        """
        try:
            global_reach = float(analysis.get("global_reach", 0) or 0)
            public_need = float(analysis.get("public_need_to_know", 0) or 0)
            everyday = float(analysis.get("everyday_impact", 0) or 0)
            public_impact = float(analysis.get("public_impact", 0) or 0)
        except (ValueError, TypeError):
            return 1.0

        if self._has_exceptional_event(analysis):
            return 1.0

        # Likely routine/local-only: low global reach AND low wider public value.
        if global_reach < 15 and public_need < 35 and public_impact < 30:
            return 0.55

        # A geographically narrow story may still matter to everyday life,
        # but should generally trail internationally consequential reporting.
        if global_reach < 25 and public_need < 45 and everyday < 45:
            return 0.75

        return 1.0

    def calculate_score(self, analysis, article, source_count=1):
        if not isinstance(analysis, dict):
            analysis = {}
        if not isinstance(article, dict):
            article = {}

        base_score = self.calculate_base_score(analysis)

        # Rejected/failed analysis must never be rescued by multipliers.
        publishable = analysis.get("publishable", True)
        if isinstance(publishable, str):
            publishable = publishable.strip().lower() in {
                "true", "yes", "1", "publish", "publishable"
            }
        if not publishable:
            return {
                "base_score": round(base_score, 2),
                "event_multiplier": 1.0,
                "severity_multiplier": 1.0,
                "freshness_multiplier": 1.0,
                "source_multiplier": 1.0,
                "final_score": 0.0,
            }

        event_multiplier = self.calculate_event_multiplier(analysis)
        severity_multiplier = self.calculate_severity_multiplier(analysis)
        freshness_multiplier = self.calculate_freshness_multiplier(article)
        source_multiplier = self.calculate_source_multiplier(source_count)
        local_penalty = self._local_only_penalty(analysis)

        combined_multiplier = (
            event_multiplier
            * severity_multiplier
            * freshness_multiplier
            * source_multiplier
        )
        combined_multiplier = min(self.MAX_COMBINED_BOOST, combined_multiplier)

        final_score = base_score * combined_multiplier * local_penalty
        final_score = max(0.0, min(100.0, final_score))

        # Keep existing result keys. Additional diagnostics are additive.
        return {
            "base_score": round(base_score, 2),
            "event_multiplier": round(event_multiplier, 3),
            "severity_multiplier": round(severity_multiplier, 3),
            "freshness_multiplier": round(freshness_multiplier, 3),
            "source_multiplier": round(source_multiplier, 3),
            "final_score": round(final_score, 2),
        }
