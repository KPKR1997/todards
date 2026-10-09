from datetime import datetime


class RankingRules:
    """
    Converts LLM-generated signals into a deterministic ranking score.
    """

    WEIGHTS = {
        "everyday_impact": 0.50,
        "dont_miss": 0.50,
        "human_consequence": 0.25,
        "economic_impact": 0.20,
        "political_significance": 0.30,
        "health_significance": 0.40,
        "scientific_significance": 0.05,
        "entertainment_significance": 0.03,
        "remarkability": 0.04,
        "global_reach": 0.03,
    }

    SEVERITY_MULTIPLIERS = {
        1: 1.00,
        2: 1.05,
        3: 1.10,
        4: 1.20,
        5: 1.35,
    }

    EVENT_MULTIPLIERS = {
        "major_disaster": 1.30,
        "mass_casualties": 1.40,
        "pandemic": 1.50,
        "election": 1.15,
        "major_political_change": 1.25,
        "major_economic_event": 1.30,
        "major_award": 1.08,
        "celebrity_death": 1.10,
        "record_breaking": 1.10,
        "unprecedented_event": 1.15,
        "major_scientific_discovery": 1.15,
        "major_technology_event": 1.15,
    }

    def calculate_base_score(self, analysis):

        score = 0.0

        for field, weight in self.WEIGHTS.items():

            value = analysis.get(field, 0)

            try:
                value = float(value)
            except (ValueError, TypeError):
                value = 0

            value = max(0, min(100, value))

            score += value * weight

        return score

    def calculate_event_multiplier(self, analysis):

        events = analysis.get(
            "events",
            {},
        )

        multiplier = 1.0

        for event, event_multiplier in self.EVENT_MULTIPLIERS.items():

            if events.get(event, False):

                # Do not simply multiply every event.
                # Take the strongest event effect.
                multiplier = max(
                    multiplier,
                    event_multiplier,
                )

        return multiplier

    def calculate_severity_multiplier(self, analysis):

        tier = analysis.get(
            "severity_tier",
            1,
        )

        try:
            tier = int(tier)
        except (ValueError, TypeError):
            tier = 1

        tier = max(
            1,
            min(5, tier),
        )

        return self.SEVERITY_MULTIPLIERS[tier]

    def calculate_freshness_multiplier(
        self,
        article,
    ):
        """
        Freshness is intentionally mild.

        Importance should dominate freshness.
        """

        article_date = article.get(
            "published_at"
        )

        if not article_date:
            article_date = article.get(
                "date"
            )

        if not article_date:
            return 1.0

        try:

            article_datetime = datetime.fromisoformat(
                article_date.replace(
                    "Z",
                    "+00:00",
                )
            )

            now = datetime.now(
                article_datetime.tzinfo
            )

            age_hours = (
                now - article_datetime
            ).total_seconds() / 3600

            if age_hours <= 6:
                return 1.05

            if age_hours <= 12:
                return 1.03

            if age_hours <= 24:
                return 1.00

            if age_hours <= 48:
                return 0.97

            return 0.93

        except Exception:
            return 1.0

    def calculate_source_multiplier(
        self,
        source_count=1,
    ):
        """
        Multiple reputable sources provide some evidence,
        but source count should never dominate importance.
        """

        if source_count >= 3:
            return 1.08

        if source_count == 2:
            return 1.04

        return 1.0

    def calculate_score(
        self,
        analysis,
        article,
        source_count=1,
    ):

        base_score = self.calculate_base_score(
            analysis
        )

        event_multiplier = (
            self.calculate_event_multiplier(
                analysis
            )
        )

        severity_multiplier = (
            self.calculate_severity_multiplier(
                analysis
            )
        )

        freshness_multiplier = (
            self.calculate_freshness_multiplier(
                article
            )
        )

        source_multiplier = (
            self.calculate_source_multiplier(
                source_count
            )
        )

        final_score = (
            base_score
            * event_multiplier
            * severity_multiplier
            * freshness_multiplier
            * source_multiplier
        )

        return {
            "base_score": round(
                base_score,
                2,
            ),
            "event_multiplier": round(
                event_multiplier,
                3,
            ),
            "severity_multiplier": round(
                severity_multiplier,
                3,
            ),
            "freshness_multiplier": round(
                freshness_multiplier,
                3,
            ),
            "source_multiplier": round(
                source_multiplier,
                3,
            ),
            "final_score": round(
                final_score,
                2,
            ),
        }