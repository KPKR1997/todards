"""
Todards Pipeline — Category Cross-Validator

Validates that scraped articles actually belong to the category folder
they were placed in. Uses Ollama to cross-check category assignment
against Todards canonical taxonomy.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from backend.core.ollama_client import OllamaClient
from backend.core.schemas import CategoryValidationResponse
from config.categories import (
    CATEGORIES,
    FOLDER_TO_CATEGORY,
    CATEGORY_TO_FOLDER,
)
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
    Validates and rectifies category mismatches for scraped news articles.
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
        Ask LLM to determine the most accurate Todards category for the article.
        """
        categories_str = ", ".join(f"'{cat}'" for cat in CATEGORIES)

        prompt = f"""
You are an editorial classification specialist for Todards news.

You must categorize this article into exactly ONE of the following 6 categories:
{categories_str}

Category descriptions:
- 'health': Medicine, public health, diseases, fitness, hospitals, medical breakthroughs, vaccines, mental health.
- 'science and technology': AI, space exploration, software, gadgets, physics, computing, cybersecurity, inventions.
- 'people': Politics, governance, diplomacy, social figures, world leaders, human interest, elections, war & peace.
- 'earth and environment': Climate change, natural disasters, weather events, wildlife, ecology, conservation, energy.
- 'sports and entertainment': Competitive sports, cinema, music, gaming, arts, pop culture, awards.
- 'economy and business': Stock markets, inflation, corporate finance, trade, labor, central banks, startups.
- 'entertainment': Movies, TV shows, music, celebrity news, gaming, arts, pop culture, awards.

CURRENT ASSIGNED CATEGORY: '{current_category}'

TITLE:
{title}

CONTENT:
{content}

Determine whether the article belongs in '{current_category}' or if another category is clearly more accurate.
Return valid JSON with:
- "assigned_category": exact category name from the list above
- "confidence": confidence score from 0.0 to 1.0
- "reason": brief 1-sentence reason
"""

        try:
            res = self.client.generate(
                prompt=prompt,
                response_model=CategoryValidationResponse,
                role="system",
            )
            return res
        except Exception as e:
            logger.warning(f"Category validation error: {e}. Keeping current category.")
            return CategoryValidationResponse(
                assigned_category=current_category,
                confidence=0.5,
                reason="Default pass due to error",
            )

    def validate_today_articles(self, date_str: Optional[str] = None) -> Dict[str, Any]:
        """
        Scans today's JSON files, validates category alignment, and relocates
        or updates misclassified articles if confidence is high.
        """
        if not self.enabled:
            logger.info("Category validation disabled.")
            return {"status": "disabled", "reassigned_count": 0}

        if date_str is None:
            date_str = datetime.now().strftime("%d%m%Y")

        reassigned = []
        total_checked = 0

        for folder_name, expected_category in FOLDER_TO_CATEGORY.items():
            folder_path = self.data_root / folder_name
            if not folder_path.exists():
                continue

            file_path = folder_path / f"{date_str}_{folder_name}.json"
            if not file_path.exists():
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    articles = json.load(f)
            except Exception as e:
                logger.error(f"Failed to read {file_path}: {e}")
                continue

            if not isinstance(articles, list):
                continue

            remaining_articles = []
            file_modified = False

            for art in articles:
                total_checked += 1
                title = art.get("title", "")
                content = art.get("content", "")

                validation = self.validate_article(title, content, expected_category)

                # Check if reassignment is needed
                assigned = validation.assigned_category.lower().strip()
                if (
                    assigned != expected_category
                    and assigned in CATEGORY_TO_FOLDER
                    and validation.confidence >= self.confidence_threshold
                ):
                    target_folder_name = CATEGORY_TO_FOLDER[assigned]
                    target_folder = self.data_root / target_folder_name
                    target_folder.mkdir(parents=True, exist_ok=True)
                    target_file = target_folder / f"{date_str}_{target_folder_name}.json"

                    # Load target file
                    target_articles = []
                    if target_file.exists():
                        try:
                            with open(target_file, "r", encoding="utf-8") as tf:
                                target_articles = json.load(tf)
                        except Exception:
                            target_articles = []

                    # Move article
                    art["category"] = assigned
                    art["original_scraped_category"] = expected_category
                    target_articles.append(art)

                    try:
                        with open(target_file, "w", encoding="utf-8") as tf:
                            json.dump(target_articles, tf, ensure_ascii=False, indent=4)

                        logger.info(
                            f"Category REASSIGNED: '{title[:40]}' from '{expected_category}' "
                            f"-> '{assigned}' (confidence: {validation.confidence:.2f})"
                        )
                        reassigned.append({
                            "title": title,
                            "from": expected_category,
                            "to": assigned,
                            "confidence": validation.confidence,
                            "reason": validation.reason,
                        })
                        file_modified = True
                        continue  # Article moved, don't keep in original file
                    except Exception as e:
                        logger.error(f"Failed to write reassigned article to {target_file}: {e}")

                remaining_articles.append(art)

            if file_modified:
                try:
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(remaining_articles, f, ensure_ascii=False, indent=4)
                except Exception as e:
                    logger.error(f"Failed to save modified file {file_path}: {e}")

        summary = {
            "total_checked": total_checked,
            "reassigned_count": len(reassigned),
            "reassignments": reassigned,
        }

        if self.metrics:
            self.metrics.log_category_validation(summary)

        return summary
