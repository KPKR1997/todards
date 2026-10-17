
from datetime import datetime, timezone
import math


class RankingRules:
    """
    Deterministic editorial ranking for Todards.

    Compatibility:
    - Preserves the RankingRules class.
    - Preserves existing public method names and parameters.
    - Preserves calculate_score() result keys.
    - Preserves publishable=False rejection behavior.
    - Requires no new dependencies or pipeline changes.

    Editorial priorities:
    1. Major global and national developments.
    2. Economic decisions affecting trade, employment, prices,
       markets, public finances, and everyday life.
    3. Major political, public-health, safety, scientific, and
       technological developments.
    4. Significant human consequences, assessed in proportion
       to their scale and wider relevance.
    5. Freshness and corroboration, with only small bonuses.

    Ranking does not replace article qualification, validation,
    or deduplication.
    """

    # The weights sum to 1.0. Missing fields contribute zero.
    #
    # Economic and political significance receive more weight.
    # Human consequence and remarkability cannot dominate the score.
    WEIGHTS = {
        "global_reach": 0.24,
        "everyday_impact": 0.19,
        "public_need_to_know": 0.18,
        "public_impact": 0.13,
        "economic_impact": 0.10,
        "health_significance": 0.04,
        "political_significance": 0.04,
        "scientific_significance": 0.025,
        "technology_significance": 0.025,
        "human_consequence": 0.015,
        "remarkability": 0.015,

        # Compatibility with upstream analysis fields.
        "dont_miss": 0.0,
        "entertainment_significance": 0.0,
    }

    # Severity is a small tie-breaker, not a substitute for
    # broad public significance.
    SEVERITY_MULTIPLIERS = {
        1: 1.00,
        2: 1.005,
        3: 1.010,
        4: 1.020,
        5: 1.030,
    }

    # Event boosts are deliberately modest.
    # An event flag alone must not make a weak article dominant.
    EVENT_MULTIPLIERS = {
        "major_disaster": 1.04,
        "mass_casualties": 1.02,
        "pandemic": 1.05,
        "election": 1.02,
        "major_political_change": 1.04,
        "major_economic_event": 1.05,
        "major_award": 1.02,
        "celebrity_death": 1.00,
        "record_breaking": 1.02,
        "unprecedented_event": 1.03,
        "major_scientific_discovery": 1.04,
        "major_technology_event": 1.03,
    }

    # Combined adjustments cannot increase the base score by
    # more than 8%, even if several signals are simultaneously true.
    MAX_COMBINED_BOOST = 1.08

    @staticmethod
    def _to_finite_float(value, default=0.0):
        """Convert a value to a finite float, using a safe default."""
        try:
            result = float(value)
        except (ValueError, TypeError, OverflowError):
            return default

        if not math.isfinite(result):
            return default

        return result

    @staticmethod
    def _flag_is_true(value):
        """Interpret boolean-like event and publishability values."""
        if isinstance(value, str):
            return value.strip().lower() in {
                "true", "yes", "1", "publish", "publishable"
            }

        return value is True or (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and value == 1
        )

    def calculate_base_score(self, analysis):
        """Return a normalized weighted score between 0 and 100."""
        if not isinstance(analysis, dict):
            return 0.0

        weighted_sum = 0.0
        total_weight = 0.0

        for field, weight in self.WEIGHTS.items():
            if weight <= 0:
                continue

            value = self._to_finite_float(analysis.get(field, 0))
            value = max(0.0, min(100.0, value))

            weighted_sum += value * weight
            total_weight += weight

        if total_weight <= 0:
            return 0.0

        return max(
            0.0,
            min(100.0, weighted_sum / total_weight)
        )

    def calculate_event_multiplier(self, analysis):
        """Return the strongest applicable event multiplier."""
        if not isinstance(analysis, dict):
            return 1.0

        events = analysis.get("events", {})
        if not isinstance(events, dict):
            return 1.0

        multiplier = 1.0

        for event, event_multiplier in self.EVENT_MULTIPLIERS.items():
            if self._flag_is_true(events.get(event, False)):
                multiplier = max(multiplier, event_multiplier)

        return multiplier

    def calculate_severity_multiplier(self, analysis):
        """Apply a small, bounded severity adjustment."""
        if not isinstance(analysis, dict):
            return 1.0

        raw_tier = analysis.get("severity_tier", 1)

        try:
            tier = int(raw_tier)
        except (ValueError, TypeError, OverflowError):
            tier = 1

        tier = max(1, min(5, tier))
        return self.SEVERITY_MULTIPLIERS[tier]

    @staticmethod
    def _parse_article_datetime(value):
        """Parse an article timestamp and normalize it to UTC."""
        if not value:
            return None

        if isinstance(value, datetime):
            parsed = value

        elif isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(
                    value.strip().replace("Z", "+00:00")
                )
            except ValueError:
                return None

        else:
            return None

        # Avoid machine-local timezone assumptions.
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed.astimezone(timezone.utc)

    def calculate_freshness_multiplier(self, article):
        """
        Apply a small recency adjustment.

        Malformed dates and future timestamps receive no bonus.
        Freshness is not allowed to dominate editorial importance.
        """
        if not isinstance(article, dict):
            return 1.0

        article_date = (
            article.get("published_at") or article.get("date")
        )
        published = self._parse_article_datetime(article_date)

        if published is None:
            return 1.0

        age_hours = (
            datetime.now(timezone.utc) - published
        ).total_seconds() / 3600

        if age_hours < 0:
            return 1.0
        if age_hours <= 6:
            return 1.02
        if age_hours <= 12:
            return 1.01
        if age_hours <= 24:
            return 1.00
        if age_hours <= 48:
            return 0.98

        return 0.95

    def calculate_source_multiplier(self, source_count=1):
        """
        Apply a small corroboration bonus.

        Source count is not a measure of editorial importance and
        does not establish that different sources are independent.
        """
        try:
            count = max(1, int(source_count))
        except (ValueError, TypeError, OverflowError):
            count = 1

        if count >= 3:
            return 1.02
        if count == 2:
            return 1.01

        return 1.0

    @staticmethod
    def _has_exceptional_event(analysis):
        """
        Identify events that can justify broader editorial attention.

        A mass-casualty flag by itself is not sufficient to exempt
        a geographically narrow incident from the local-story penalty.
        """
        if not isinstance(analysis, dict):
            return False

        events = analysis.get("events", {})
        if not isinstance(events, dict):
            return False

        exceptional_events = {
            "major_disaster",
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

        return any(
            RankingRules._flag_is_true(events.get(name, False))
            for name in exceptional_events
        )

    def _local_only_penalty(self, analysis):
        """
        Penalize stories with little reach or wider public value.

        This is a ranking adjustment, not a rejection rule.

        Local tragedies can still rank well when the analyzer
        identifies substantial public impact, everyday relevance,
        or a genuinely exceptional event.
        """
        if not isinstance(analysis, dict):
            return 1.0

        global_reach = self._to_finite_float(
            analysis.get("global_reach", 0)
        )
        public_need = self._to_finite_float(
            analysis.get("public_need_to_know", 0)
        )
        everyday = self._to_finite_float(
            analysis.get("everyday_impact", 0)
        )
        public_impact = self._to_finite_float(
            analysis.get("public_impact", 0)
        )
        economic = self._to_finite_float(
            analysis.get("economic_impact", 0)
        )
        political = self._to_finite_float(
            analysis.get("political_significance", 0)
        )
        health = self._to_finite_float(
            analysis.get("health_significance", 0)
        )
        science = self._to_finite_float(
            analysis.get("scientific_significance", 0)
        )
        technology = self._to_finite_float(
            analysis.get("technology_significance", 0)
        )

        # A local story with a genuinely exceptional event may
        # deserve broader attention despite limited geographic reach.
        if self._has_exceptional_event(analysis):
            return 1.0

        # Strong public, economic, political, health, or scientific
        # consequences protect a story from being treated as trivial.
        wider_significance = max(
            public_need,
            everyday,
            public_impact,
            economic,
            political,
            health,
            science,
            technology,
        )

        # Strongly demote routine incidents that have little
        # reach and little relevance outside their immediate setting.
        if (
            global_reach < 20
            and wider_significance < 30
        ):
            return 0.50

        # Moderately demote narrow stories with limited wider value.
        if (
            global_reach < 35
            and wider_significance < 45
        ):
            return 0.75

        return 1.0

    def calculate_score(self, analysis, article, source_count=1):
        """
        Calculate the final score while preserving the established
        return structure expected by downstream modules.
        """
        if not isinstance(analysis, dict):
            analysis = {}

        if not isinstance(article, dict):
            article = {}

        base_score = self.calculate_base_score(analysis)

        # Never allow ranking multipliers to rescue a rejected article.
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

        # Bound both positive and negative adjustments.
        combined_multiplier = min(
            self.MAX_COMBINED_BOOST,
            max(0.0, combined_multiplier),
        )

        final_score = base_score * combined_multiplier * local_penalty
        final_score = max(0.0, min(100.0, final_score))

        # Keep the exact existing output keys.
        return {
            "base_score": round(base_score, 2),
            "event_multiplier": round(event_multiplier, 3),
            "severity_multiplier": round(severity_multiplier, 3),
            "freshness_multiplier": round(freshness_multiplier, 3),
            "source_multiplier": round(source_multiplier, 3),
            "final_score": round(final_score, 2),
        }
