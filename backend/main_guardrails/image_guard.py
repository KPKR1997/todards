import logging
from typing import List, Dict, Any

logger = logging.getLogger("todards.image_safety")


class ImageSafetyGuard:

    def __init__(
        self,
        model: str = "shieldgemma",
    ):
        self.model = model

    def check_image(self, image_path: str) -> bool:
        """
        Run ShieldGemma against one image.

        Returns True if safe.
        """

        # ShieldGemma inference implementation goes here.

        return True

    def run(
        self,
        articles: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Remove unsafe images/articles from processed output.
        """

        safe_articles = []

        for article in articles:

            image_path = article.get("image")

            if not image_path:
                safe_articles.append(article)
                continue

            try:

                if self.check_image(image_path):
                    safe_articles.append(article)

                else:
                    logger.warning(
                        "ShieldGemma rejected image for: "
                        f"{article.get('title', '')[:100]}"
                    )

                    # Don't publish an article with an unsafe image.
                    # Better to remove/replace the image depending
                    # on your image fallback strategy.

            except Exception as e:

                logger.error(
                    f"Image safety check failed for "
                    f"{article.get('title', '')[:80]}: {e}"
                )

                # Fail closed for image safety.
                continue

        return safe_articles