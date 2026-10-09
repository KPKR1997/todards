import json
import logging
from pathlib import Path
from typing import Dict

from backend.core.ollama_client import OllamaClient

logger = logging.getLogger("todards.article_safety")


class ArticleSafetyGuard:
    """
    Safety screening for scraped articles using Llama Guard 4.

    This is separate from editorial filtering.
    It only determines whether article content violates
    the configured safety policy.
    """

    def __init__(
        self,
        client: OllamaClient,
        model: str = "llama-guard4",
    ):
        self.client = client
        self.model = model

    def _check_article(self, article: Dict) -> bool:

        title = str(article.get("title", "")).strip()
        content = str(article.get("content", "")).strip()

        prompt = f"""
You are a safety classifier for a news publishing pipeline.

Classify whether the following news article contains content that
should NOT be published because it violates safety policies.

Do not judge whether the article is important news.
Only judge safety.

TITLE:
{title}

ARTICLE:
{content}

Return ONLY JSON:

{{
    "safe": true
}}
"""

        try:
            # Use raw generation because this is a simple safety decision.
            response = self.client.generate_raw(
                prompt=prompt,
                model=self.model,
            )

            result = json.loads(response)

            return bool(result.get("safe", False))

        except Exception as e:
            logger.error(
                f"Llama Guard failed for article "
                f"'{title[:80]}': {e}"
            )

            # Fail closed for safety.
            return False

    def run(self, data_paths: Dict[str, str]) -> int:
        """
        Scan all scraped article files.

        Returns number of removed articles.
        """

        total_removed = 0

        for folder_name, path_str in data_paths.items():

            path = Path(path_str)

            if not path.exists():
                continue

            try:
                with open(
                    path,
                    "r",
                    encoding="utf-8",
                ) as f:
                    articles = json.load(f)

                if not isinstance(articles, list):
                    continue

                safe_articles = []

                for article in articles:

                    if self._check_article(article):
                        safe_articles.append(article)
                    else:
                        total_removed += 1

                        logger.warning(
                            f"Llama Guard rejected article: "
                            f"{article.get('title', '')[:100]}"
                        )

                if len(safe_articles) != len(articles):

                    with open(
                        path,
                        "w",
                        encoding="utf-8",
                    ) as f:
                        json.dump(
                            safe_articles,
                            f,
                            ensure_ascii=False,
                            indent=4,
                        )

            except Exception as e:

                logger.error(
                    f"Article safety scan failed for "
                    f"{path}: {e}"
                )

        logger.info(
            f"Llama Guard removed {total_removed} articles."
        )

        return total_removed