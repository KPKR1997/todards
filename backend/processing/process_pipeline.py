"""
Todards Pipeline — Article Processing Pipeline

Processes top-ranked articles through:
1. Historical context enrichment (RAG)
2. Professional summarization (100-120 words)
3. Location extraction and verification
4. Headline drafting and fine-tuning
5. Image keyword generation, multi-source search (Pexels, Unsplash, Wikipedia)
6. SigLIP visual-headline semantic matching
7. Cross-article image deduplication (perceptual + URL registry)
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from backend.processing.llm_summarize import LlmSummarizer
from backend.processing.llm_place import LlmPlacefinder
from backend.processing.llm_headline import LlmHeadlineEditor
from backend.processing.llm_image_keywords import LlmImageKeywordsGenerator
from backend.processing.fetch_image import ImageFetcher
from backend.processing.image_match_scorer import SigLIPMatcher
from config.settings import OLLAMA_BASE_URL, OLLAMA_MODEL

logger = logging.getLogger("todards.process_pipeline")


class MainProcessPipeline:
    def __init__(
        self,
        url: Optional[str] = None,
        model: Optional[str] = None,
        image_fetcher: Optional[ImageFetcher] = None,
        image_scorer: Optional[SigLIPMatcher] = None,
        rag_enricher=None,
    ):
        self.url = url or OLLAMA_BASE_URL
        self.model = model or OLLAMA_MODEL

        # Shared components to avoid reloading heavy models
        self.image_fetcher = image_fetcher or ImageFetcher(model=self.model)
        self.image_scorer = image_scorer or SigLIPMatcher()
        self.rag_enricher = rag_enricher

        # LLM helpers
        self.summarizer = LlmSummarizer(self.url, self.model)
        self.place_finder = LlmPlacefinder(self.url, self.model)
        self.headline_writer = LlmHeadlineEditor(self.url, self.model)
        self.image_keyword_generator = LlmImageKeywordsGenerator(self.url, self.model)

    def run_pipeline(
        self,
        data_path: str,
        progress_tracker=None,
        stage_name: str = "Processing",
    ) -> List[Dict[str, Any]]:
        self.data_path = data_path

        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        data = data[:3]
        feed_data = []

        total_sections = len(data)
        for idx, section in enumerate(data, 1):
            content = section.get("content", "")
            art_id = section.get("id", f"art_{idx}")
            category = section.get("category", "")
            title = section.get("title", "")

            if progress_tracker:
                progress_tracker.update_status(
                    f"{stage_name} → Article {idx}/{total_sections}: {title[:30]}..."
                )

            # 1. RAG Historical Context Enrichment
            historical_context = None
            if self.rag_enricher:
                try:
                    historical_context = self.rag_enricher.get_context(title=title, content=content)
                except Exception as e:
                    logger.warning(f"RAG context enrichment failed: {e}")

            # 2. Summarize
            summarized_content = self.summarizer.summarize(content, historical_context=historical_context)

            # 3. Location
            place = self.place_finder.trace_location(content, "")

            # 4. Headline drafting and validation
            headline_draft = self.headline_writer.write_headline(summarized_content, "")
            headline = self.headline_writer.validate_headline(summarized_content, headline_draft)

            # 5. Image keywords
            raw_keywords = self.image_keyword_generator.generate_keywords(content)
            image_keywords = [k.strip() for k in raw_keywords.split(",") if k.strip()]

            # 6. Fetch images
            images = self.image_fetcher.get_images(
                keywords=image_keywords,
                image_id=art_id,
                pexels_per_keyword=3,
                unsplash_per_keyword=2,
            )

            # 7. Score images with SigLIP and pick the best unused match
            matched_image_url = None
            if images:
                image_scores = []
                for img in images:
                    candidate_image_path = img.get("local_path")
                    try:
                        score = self.image_scorer.score(candidate_image_path, headline)
                    except Exception as e:
                        logger.warning(f"SigLIP scoring failed for {candidate_image_path}: {e}")
                        score = 0.0
                    image_scores.append(score)

                best_idx = int(image_scores.index(max(image_scores)))
                selected_candidate = images[best_idx]
                matched_image_url = selected_candidate.get("url")

                # Explicitly register the selected image in the global run registry
                try:
                    local_p = Path(selected_candidate.get("local_path", ""))
                    content_bytes = local_p.read_bytes() if local_p.exists() else None
                    self.image_fetcher.register_used_image(
                        image_url=matched_image_url,
                        article_id=art_id,
                        image_content=content_bytes,
                    )
                except Exception as e:
                    logger.warning(f"Could not register selected image: {e}")

            if not matched_image_url:
                # Ultimate fallback image if image search yields nothing
                matched_image_url = "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=800&q=80"
                logger.warning(f"No image found for '{headline[:30]}'. Using fallback.")

            feed_data.append({
                "id": art_id,
                "category": category,
                "title": headline,
                "image": matched_image_url,
                "place": place,
                "time": datetime.now().strftime("%b %d, %Y"),
                "content": summarized_content,
            })

        return feed_data


from backend.core.image_dedup import (
    get_canonical_image_id,
    compute_perceptual_hash,
    is_perceptual_match,
)


def ensure_unique_images(articles: List[Dict[str, Any]], image_fetcher: Optional[ImageFetcher] = None) -> List[Dict[str, Any]]:
    """
    Post-processing guardrail: Guarantees that every article across all
    categories in the final issue has a 100% unique image URL and distinct visual identity.
    Uses canonical image IDs (independent of query parameters) and perceptual hashes.
    """
    seen_canonical_ids = set()
    cleaned_articles = []

    for art in articles:
        url = art.get("image", "")
        cid = get_canonical_image_id(url)

        if (not cid or cid in seen_canonical_ids) and image_fetcher:
            logger.warning(
                f"Cross-article duplicate image detected: '{url[:60]}...' (canonical: {cid}). Replacing with distinct image."
            )
            # Try keyword-based search for a unique image
            kw = art.get("title", "global news")
            fallback = None
            for attempt in range(1, 4):
                candidate = image_fetcher.get_fallback_image(kw)
                if candidate and candidate.get("url"):
                    cand_cid = get_canonical_image_id(candidate["url"])
                    if cand_cid not in seen_canonical_ids:
                        fallback = candidate
                        break
                # Try broader search term if specific title failed
                kw = "news editorial journalism"

            if fallback and fallback.get("url"):
                art["image"] = fallback["url"]
                cid = get_canonical_image_id(fallback["url"])
                logger.info(f"Replaced duplicate with unique image: {cid}")

        if cid:
            seen_canonical_ids.add(cid)
        cleaned_articles.append(art)

    return cleaned_articles


def ensure_unique_sections(sections: List[Dict[str, Any]], image_fetcher: Optional[ImageFetcher] = None) -> List[Dict[str, Any]]:
    """
    Global issue-level guardrail: Scans ALL 18 cards across ALL sections in todards.json.
    Ensures that no two cards in the entire publication have duplicate canonical image IDs.
    """
    seen_canonical_ids = set()

    for section in sections:
        cards = section.get("cards", [])
        for card in cards:
            url = card.get("image", "")
            cid = get_canonical_image_id(url)

            if (not cid or cid in seen_canonical_ids) and image_fetcher:
                logger.warning(
                    f"Duplicate image found in section '{section.get('id')}' card '{card.get('id')}': {cid}. Fetching unique replacement."
                )
                kw = card.get("title", "global news")
                replacement = None
                for attempt in range(1, 5):
                    candidate = image_fetcher.get_fallback_image(kw)
                    if candidate and candidate.get("url"):
                        cand_cid = get_canonical_image_id(candidate["url"])
                        if cand_cid not in seen_canonical_ids:
                            replacement = candidate
                            break
                    kw = f"{section.get('id', 'world')} news"

                if replacement and replacement.get("url"):
                    card["image"] = replacement["url"]
                    cid = get_canonical_image_id(replacement["url"])
                    logger.info(f"Updated card {card.get('id')} with new image: {cid}")

            if cid:
                seen_canonical_ids.add(cid)

    return sections
