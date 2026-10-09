import json
import logging
from pathlib import Path
from typing import Dict, Optional

from backend.core.ollama_client import OllamaClient
from config.settings import OLLAMA_BASE_URL


logger = logging.getLogger("todards.article_safety")


class ArticleSafetyGuard:
    """
    Safety screening for scraped articles using Llama Guard 4.

    This is separate from editorial filtering.
    It only determines whether article content violates
    the configured safety policy.

    IMPORTANT:
    - SAFE  -> article is retained
    - UNSAFE -> article is removed
    - ERROR -> article is retained, but the error is logged

    A technical failure must never be confused with an unsafe
    classification.
    """

    def __init__(
        self,
        client: OllamaClient,
        model: str = "llama-guard3:1b",
    ):
        self.client = client
        self.model = model

        # Create a dedicated Ollama client configured for
        # the safety model.
        #
        # This avoids passing `model=` to generate_raw(), since
        # the current OllamaClient.generate_raw() does not accept
        # a model argument.
        self.guard_client = OllamaClient(
            base_url=OLLAMA_BASE_URL,
            model=self.model,
            timeout=120,
        )

    def _check_article(
        self,
        article: Dict,
    ) -> Optional[bool]:
        """
        Check one article.

        Returns:
            True  -> article is safe
            False -> article is unsafe
            None  -> safety check failed
        """

        title = str(
            article.get(
                "title",
                "",
            )
        ).strip()

        content = str(
            article.get(
                "content",
                "",
            )
        ).strip()

        prompt = f"""
You are a safety classifier for a news publishing pipeline.

Your task is ONLY to determine whether the article contains
content that should NOT be published because it violates
safety policies.

Do NOT judge:
- news importance
- editorial value
- political importance
- public interest
- popularity
- credibility

Only classify the CONTENT for safety.

TITLE:
{title}

ARTICLE:
{content}

Return ONLY valid JSON.

Use exactly this format:

{{
    "safe": true
}}

If the article contains content that violates the configured
safety policy, return:

{{
    "safe": false
}}

Do not provide any explanation.
"""

        try:
            # The dedicated guard client already uses
            # llama-guard4, so we DO NOT pass model= here.
            response = self.guard_client.generate_raw(
                prompt=prompt,
            )

            if not response:
                raise ValueError(
                    "Llama Guard returned an empty response."
                )

            # Handle possible markdown fences or surrounding text.
            response_text = response.strip()

            if response_text.startswith("```"):
                lines = response_text.splitlines()

                if lines:
                    lines = lines[1:]

                if lines and lines[-1].strip().startswith("```"):
                    lines = lines[:-1]

                response_text = "\n".join(
                    lines
                ).strip()

            # Extract the JSON object if the model returned
            # surrounding whitespace/text.
            start = response_text.find("{")
            end = response_text.rfind("}")

            if start == -1 or end == -1:
                raise ValueError(
                    "Llama Guard did not return valid JSON."
                )

            response_text = response_text[
                start:end + 1
            ]

            result = json.loads(
                response_text
            )

            if "safe" not in result:
                raise ValueError(
                    "Llama Guard response does not contain "
                    "'safe'."
                )

            safe = result["safe"]

            if isinstance(safe, str):
                safe = (
                    safe.strip().lower()
                    in {
                        "true",
                        "yes",
                        "1",
                        "safe",
                    }
                )
            else:
                safe = bool(safe)

            return safe

        except Exception as e:

            logger.error(
                f"Llama Guard failed for article "
                f"'{title[:80]}': {e}"
            )

            # IMPORTANT:
            #
            # Do NOT return False here.
            #
            # False means the safety model explicitly classified
            # the article as unsafe.
            #
            # None means the safety check itself failed.
            return None

    def run(
        self,
        data_paths: Dict[str, str],
    ) -> int:
        """
        Scan all scraped article files.

        Returns:
            Number of articles explicitly rejected by
            Llama Guard.

        Articles for which the safety check fails are NOT
        removed. They are retained and logged as errors.
        """

        total_removed = 0
        total_checked = 0
        total_errors = 0

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

                if not isinstance(
                    articles,
                    list,
                ):
                    logger.warning(
                        f"Skipping invalid article file "
                        f"{path}: expected a list."
                    )
                    continue

                safe_articles = []

                for article in articles:

                    result = self._check_article(
                        article
                    )

                    total_checked += 1

                    # ------------------------------------------------
                    # SAFE
                    # ------------------------------------------------

                    if result is True:

                        safe_articles.append(
                            article
                        )

                    # ------------------------------------------------
                    # UNSAFE
                    # ------------------------------------------------

                    elif result is False:

                        total_removed += 1

                        logger.warning(
                            f"Llama Guard rejected article: "
                            f"{article.get('title', '')[:100]}"
                        )

                    # ------------------------------------------------
                    # ERROR
                    # ------------------------------------------------

                    else:

                        total_errors += 1

                        # Safety check failed.
                        #
                        # Do NOT delete the article merely because
                        # the safety model failed.
                        safe_articles.append(
                            article
                        )

                        logger.error(
                            f"Llama Guard unavailable; "
                            f"keeping article unchanged: "
                            f"{article.get('title', '')[:100]}"
                        )

                # Only rewrite the file if actual unsafe
                # articles were removed.
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

                    logger.info(
                        f"Updated {path}: "
                        f"removed "
                        f"{len(articles) - len(safe_articles)} "
                        f"unsafe articles."
                    )

            except Exception as e:

                logger.error(
                    f"Article safety scan failed for "
                    f"{path}: {e}"
                )

        logger.info(
            f"Llama Guard safety scan completed: "
            f"checked={total_checked}, "
            f"removed={total_removed}, "
            f"errors={total_errors}"
        )

        return total_removed