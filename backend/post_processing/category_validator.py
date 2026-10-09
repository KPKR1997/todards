"""
Todards Pipeline — Category Relevance Validator

Validates whether scraped articles are genuinely relevant to the category
folder they were placed in.

Articles that are clearly unrelated to their assigned category are rejected
and removed from that category. Articles are NEVER redistributed.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from backend.core.ollama_client import OllamaClient
from backend.core.schemas import CategoryValidationResponse
from config.categories import CATEGORIES, FOLDER_TO_CATEGORY
from config.settings import (
    DATA_ROOT,
    CATEGORY_VALIDATION_ENABLED,
    CATEGORY_VALIDATION_CONFIDENCE_THRESHOLD,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
)

logger = logging.getLogger("todards.category_validator")


class CategoryValidator:
    """
    Validates whether articles are genuinely relevant to the category
    in which they were scraped.

    This validator DOES NOT redistribute articles.

    If an article is clearly unrelated to its current category, it is
    removed from that category.
    """

    def __init__(
        self,
        data_root: Optional[Path] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        client: Optional[OllamaClient] = None,
        enabled: bool = CATEGORY_VALIDATION_ENABLED,
        confidence_threshold: float = CATEGORY_VALIDATION_CONFIDENCE_THRESHOLD,
        metrics_collector=None,
    ):
        self.data_root = Path(data_root or DATA_ROOT)
        self.enabled = enabled
        self.confidence_threshold = confidence_threshold
        self.metrics = metrics_collector

        self.client = client or OllamaClient(
            base_url=base_url or OLLAMA_BASE_URL,
            model=model or OLLAMA_MODEL,
        )

    def validate_article(
        self,
        title: str,
        content: str,
        current_category: str,
    ) -> CategoryValidationResponse:
        """
        Ask the LLM whether the article is genuinely relevant to the
        category in which it currently exists.

        The LLM may identify another category, but that information is
        NOT used to move the article.
        """

        categories_str = ", ".join(
            f"'{category}'" for category in CATEGORIES
        )

        prompt = f"""
You are an editorial quality-control classifier for Todards news.

Your task is NOT to redistribute articles between categories.

Your ONLY task is to determine whether this article is genuinely relevant
to its CURRENT CATEGORY.

Todards has the following categories:

{categories_str}

CATEGORY DEFINITIONS:

- 'health':
  Medicine, healthcare, public health, diseases, medical research,
  hospitals, treatments, vaccines, epidemiology, mental health,
  medical breakthroughs and health-related developments.

- 'science and technology':
  Science, scientific research, physics, chemistry, biology,
  astronomy, space exploration, AI, software, computing,
  cybersecurity, gadgets, engineering and technological inventions.

- 'people':
  Politics, governments, elections, governance, diplomacy,
  politicians, world leaders, international relations,
  wars, conflicts, social developments and major human-interest stories.

- 'earth and environment':
  Climate change, climate science, natural disasters, earthquakes,
  floods, storms, wildfires, weather events, wildlife, ecology,
  conservation, environment and energy-related environmental issues.

- 'entertainment':
  Competitive sports, athletes, tournaments, sporting events,
  cinema, television, music, gaming, arts, pop culture,
  entertainment and awards,  Movies, television, music, celebrities, gaming, arts,
  pop culture and entertainment awards.

- 'economy and business':
  Stock markets, companies, corporate developments, business,
  startups, finance, banking, inflation, interest rates,
  trade, employment, labor markets, central banks and economic policy.

CONTENT TYPE FILTER

Todards should publish substantive news, not generic editorial or content
formats.

REJECT articles that are primarily:

- "5 things you need to know..."
- "10 things to watch..."
- "Here's your Sunday..."
- "Your Monday/weekly briefing..."
- "What happened this week..."
- "What to expect this week..."
- "Morning briefing" or "daily briefing"
- "Weekend roundup" or "weekly roundup"
- "Top stories of the day/week"
- "Things you missed..."
- "Everything you need to know..."
- "What you need to know..."
- "Explained" articles that contain no meaningful new development
- Generic listicles or compilation articles
- Opinion, analysis or commentary without a new factual development
- Lifestyle, tips, advice or generic informational articles
- Articles mainly summarizing several unrelated minor stories
- Promotional, sponsored or branded content

The article must contain a SPECIFIC NEWS DEVELOPMENT, EVENT, DECISION,
DISCOVERY, REPORT, or CHANGE that is important enough to justify
publication.

A useful test:

"Can I identify one specific consequential development being reported?"

If NO:
    publishable = false

Do not publish an article merely because it contains many facts or
summarizes several stories.

IMPORTANT:
A headline format alone is not sufficient reason to reject an article.
If a list/roundup contains a genuinely major development, evaluate the
underlying news. However, generic listicles, briefings and roundups should
normally be rejected.
 

CURRENT CATEGORY:
'{current_category}'

ARTICLE TITLE:
{title}

ARTICLE CONTENT:
{content}

IMPORTANT RULES:

1. Judge the article against the CURRENT CATEGORY only.

2. If the article has a clear and meaningful connection to the
   current category, consider it RELEVANT.

3. Do NOT reject an article merely because it could also fit another
   category.

4. News articles can legitimately overlap categories.
   For example:
   - A NASA discovery can be science and technology.
   - A government climate policy can be people OR earth and environment.
   - A company developing AI can be science and technology OR economy and business.

5. If the CURRENT CATEGORY is a reasonable and meaningful category
   for the article, KEEP it.

6. Only classify an article as belonging to another category when it is
   clearly more relevant to that category and has little or no meaningful
   connection to the CURRENT CATEGORY.

7. Most importantly:
   DO NOT reject borderline or ambiguous articles.
   Reject ONLY articles that are clearly unrelated to the current category.

Return valid JSON containing:

- "assigned_category":
    The category that best describes the article overall.
    It must be exactly one of the categories listed above.

- "confidence":
    A number from 0.0 to 1.0 representing how confident you are
    in the classification.

- "reason":
    A brief one-sentence explanation.

CURRENT CATEGORY: '{current_category}'
"""

        try:
            response = self.client.generate(
                prompt=prompt,
                response_model=CategoryValidationResponse,
                role="system",
            )

            return response

        except Exception as e:
            logger.warning(
                f"Category validation error: {e}. "
                f"Keeping article in '{current_category}'."
            )

            # Fail-open:
            # If the LLM fails, NEVER delete the article.
            return CategoryValidationResponse(
                assigned_category=current_category,
                confidence=0.5,
                reason="Validation failed; article retained.",
            )

    def validate_today_articles(
        self,
        date_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Validate today's articles against their existing categories.

        Articles that are clearly unrelated to their current category
        are removed.

        Articles are NEVER moved to another category.
        """

        if not self.enabled:
            logger.info("Category validation disabled.")

            return {
                "status": "disabled",
                "total_checked": 0,
                "rejected_count": 0,
                "rejected_articles": [],
            }

        if date_str is None:
            date_str = datetime.now().strftime("%d%m%Y")

        total_checked = 0
        rejected = []

        for folder_name, expected_category in FOLDER_TO_CATEGORY.items():

            folder_path = self.data_root / folder_name

            if not folder_path.exists():
                continue

            file_path = (
                folder_path /
                f"{date_str}_{folder_name}.json"
            )

            if not file_path.exists():
                continue

            # --------------------------------------------------------
            # LOAD ARTICLES
            # --------------------------------------------------------

            try:
                with open(
                    file_path,
                    "r",
                    encoding="utf-8",
                ) as f:
                    articles = json.load(f)

            except Exception as e:
                logger.error(
                    f"Failed to read {file_path}: {e}"
                )
                continue

            if not isinstance(articles, list):
                logger.warning(
                    f"Expected list in {file_path}, "
                    f"got {type(articles).__name__}"
                )
                continue

            remaining_articles = []

            # --------------------------------------------------------
            # VALIDATE EACH ARTICLE
            # --------------------------------------------------------

            for article in articles:

                total_checked += 1

                title = str(
                    article.get("title", "")
                ).strip()

                content = str(
                    article.get("content", "")
                ).strip()

                # ----------------------------------------------------
                # EMPTY ARTICLE SAFETY
                # ----------------------------------------------------

                if not title and not content:
                    logger.warning(
                        f"Rejecting empty article from "
                        f"'{expected_category}'."
                    )

                    rejected.append({
                        "title": "",
                        "from": expected_category,
                        "confidence": 1.0,
                        "reason": "Article contains no title or content.",
                    })

                    continue

                # ----------------------------------------------------
                # LLM VALIDATION
                # ----------------------------------------------------

                validation = self.validate_article(
                    title=title,
                    content=content,
                    current_category=expected_category,
                )

                assigned = (
                    validation.assigned_category
                    .lower()
                    .strip()
                )

                confidence = validation.confidence

                # ----------------------------------------------------
                # DECISION
                # ----------------------------------------------------
                #
                # IMPORTANT:
                #
                # We only reject when:
                #
                # 1. LLM thinks it belongs somewhere else
                # 2. That decision has high confidence
                #
                # Otherwise KEEP.
                #
                # No redistribution.
                # ----------------------------------------------------

                should_reject = (
                    assigned != expected_category.lower().strip()
                    and confidence >= self.confidence_threshold
                )

                if should_reject:

                    logger.info(
                        f"CATEGORY REJECTED: "
                        f"'{title[:80]}' | "
                        f"current='{expected_category}' | "
                        f"detected='{assigned}' | "
                        f"confidence={confidence:.2f}"
                    )

                    rejected.append({
                        "title": title,
                        "from": expected_category,
                        "detected_category": assigned,
                        "confidence": confidence,
                        "reason": validation.reason,
                    })

                    # Do NOT append to remaining_articles.
                    # Therefore it is removed from this category.
                    continue

                # ----------------------------------------------------
                # ARTICLE PASSES VALIDATION
                # ----------------------------------------------------

                remaining_articles.append(article)

            # --------------------------------------------------------
            # WRITE UPDATED FILE
            # --------------------------------------------------------

            if len(remaining_articles) != len(articles):

                try:
                    with open(
                        file_path,
                        "w",
                        encoding="utf-8",
                    ) as f:
                        json.dump(
                            remaining_articles,
                            f,
                            ensure_ascii=False,
                            indent=4,
                        )

                    logger.info(
                        f"Updated {file_path}: "
                        f"removed "
                        f"{len(articles) - len(remaining_articles)} "
                        f"invalid article(s)."
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to save modified file "
                        f"{file_path}: {e}"
                    )

        # ------------------------------------------------------------
        # SUMMARY
        # ------------------------------------------------------------

        summary = {
            "status": "completed",
            "total_checked": total_checked,
            "rejected_count": len(rejected),
            "rejected_articles": rejected,
        }

        if self.metrics:
            self.metrics.log_category_validation(summary)

        logger.info(
            f"Category validation completed: "
            f"{total_checked} checked, "
            f"{len(rejected)} rejected."
        )

        return summary