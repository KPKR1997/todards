from datetime import datetime, timezone
import math
class RankingRules:
 
    # The weights sum to 1.0.
    # Category-specific significance is calculated separately
    # using the strongest relevant category signal.
    WEIGHTS = {
        "public_need_to_know": 0.25,
        "public_impact": 0.20,
        "global_reach": 0.15,
        "everyday_impact": 0.10,
        "economic_impact": 0.10,
        "political_significance": 0.10,
        "category_significance": 0.10,
    }
    CATEGORY_FIELDS = (
        "health_significance",
        "scientific_significance",
        "technology_significance",
        "entertainment_significance",
    )
    EVENT_MULTIPLIERS = {
        "major_disaster": 1.05,
        "mass_casualties": 1.03,
        "pandemic": 1.05,
        "election": 1.03,
        "major_political_change": 1.05,
        "major_economic_event": 1.05,
        "major_award": 1.04,
        "celebrity_death": 1.00,
        "record_breaking": 1.03,
        "unprecedented_event": 1.04,
        "major_scientific_discovery": 1.05,
        "major_technology_event": 1.04,
    }
    MAX_COMBINED_BOOST = 1.08
    @staticmethod
    def _to_finite_float(value, default=0.0):
        try:
            result = float(value)
        except (ValueError, TypeError, OverflowError):
            return default
        if not math.isfinite(result):
            return default
        return result
    @staticmethod
    def _flag_is_true(value):
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
    
        if not isinstance(analysis, dict):
            return 0.0
        values = {}
        for field in self.WEIGHTS:
            if field == "category_significance":
                category_values = [
                    self._to_finite_float(analysis.get(name, 0))
                    for name in self.CATEGORY_FIELDS
                ]
                value = max(category_values, default=0.0)
            elif field == "public_need_to_know":
                value = max(
                    self._to_finite_float(
                        analysis.get("public_need_to_know", 0)
                    ),
                    self._to_finite_float(
                        analysis.get("dont_miss", 0)
                    ),
                )
            else:
                value = self._to_finite_float(
                    analysis.get(field, 0)
                )
            values[field] = max(0.0, min(100.0, value))
        score = sum(
            values[field] * weight
            for field, weight in self.WEIGHTS.items()
        )
        return round(max(0.0, min(100.0, score)), 2)
    def calculate_event_multiplier(self, analysis):
        if not isinstance(analysis, dict):
            return 1.0
        events = analysis.get("events", {})
        if not isinstance(events, dict):
            return 1.0
        applicable = [
            multiplier
            for event, multiplier in self.EVENT_MULTIPLIERS.items()
            if self._flag_is_true(events.get(event, False))
        ]
        return max(applicable, default=1.0)
    def calculate_severity_multiplier(self, analysis):
        return 1.0
    @staticmethod
    def _parse_article_datetime(value):
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
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    def calculate_freshness_multiplier(self, article):
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

        return 1.0
    def calculate_score(self, analysis, article, source_count=1):
        if not isinstance(analysis, dict):
            analysis = {}
        if not isinstance(article, dict):
            article = {}
        base_score = self.calculate_base_score(analysis)
        # Fail closed: a rejected article cannot be rescued by bonuses.
        publishable = analysis.get("publishable", True)
        if not self._flag_is_true(publishable):
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
        combined_multiplier = (
            event_multiplier
            * severity_multiplier
            * freshness_multiplier
            * source_multiplier
        )
        # Preserve a small, bounded bonus rather than allowing
        # multiple flags to overwhelm the underlying importance score.
        combined_multiplier = min(
            self.MAX_COMBINED_BOOST,
            max(0.0, combined_multiplier),
        )
        final_score = base_score * combined_multiplier
        final_score = max(0.0, min(100.0, final_score))
        return {
            "base_score": round(base_score, 2),
            "event_multiplier": round(event_multiplier, 3),
            "severity_multiplier": round(severity_multiplier, 3),
            "freshness_multiplier": round(freshness_multiplier, 3),
            "source_multiplier": round(source_multiplier, 3),
            "final_score": round(final_score, 2),
        }
