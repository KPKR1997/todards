import logging
from typing import Optional, List
from backend.core.ollama_client import OllamaClient
from backend.core.schemas import ImageKeywordsResponse
from config.settings import OLLAMA_BASE_URL, OLLAMA_MODEL

logger = logging.getLogger("todards.image_keywords")


class LlmImageKeywordsGenerator:
    def __init__(self, base_url=None, model=None, client: Optional[OllamaClient] = None):
        self.base_url = base_url or OLLAMA_BASE_URL
        self.model = model or OLLAMA_MODEL
        self.client = client or OllamaClient(base_url=self.base_url, model=self.model)

    def generate_keywords(self, content: str) -> str:
        """
        Generate exactly 3 image-search keywords.
        Returns a comma-separated string for backward compatibility with .split(',').
        """
        prompt = f"""
        
                                You are an image-search keyword generator for a news and article website.

                                Your task is to read the provided news/article paragraph and generate exactly THREE image-search keywords that can be used to find relevant images on Unsplash or Pexels.

                                The keywords do NOT need to describe the exact event. They should produce visually relevant images that help represent the main subject, event, people, organization, technology, place, or concept discussed in the content.

                                Do not just take direct word meaning ad produce keywords. For example if menioned 'Hunter-gatherer', don't pass keyword for 'hunter-gatherer', it may mislead. Instead pass 'ancient time' or 'primitive human' etc

                                Choose keywords using this priority:

                                1. A generalised image relevant to main subject or event.
                                    for example, Any iphone related news can be associate to Apple logo, American govnt related can be associated to American flag etc
                                2. A recognizable person, logo, organization, facility, object, or location related to the story.
                                3. A broader visual concept that represents the story if an exact image is unlikely to exist.

                                For example:

                                * WHO vaccine campaign → `WHO headquarters, vaccine vial, vaccination`
                                * SpaceX rocket launch → `SpaceX rocket, rocket launch, space launch`
                                * AI model release → `AI technology, data center, artificial intelligence`
                                * Climate change → `climate change, melting glacier, extreme weather`
                                * Measles outbreak → `measles vaccination, vaccine vial, healthcare worker`

                                IMPORTANT:

                                * Generate exactly 3 keywords.
                                * Separate them ONLY with commas.
                                * Each keyword must contain a maximum of 3 words.
                                * Use simple, searchable phrases suitable for Unsplash and Pexels.
                                * Prefer concrete visual subjects over abstract concepts.
                                * Avoid complete sentences.
                                * Avoid quotation marks.
                                * Avoid numbering.
                                * Avoid explanations.
                                * Do not repeat the same keyword.
                                * Do not invent a specific event, person, location, or object that is not supported by the paragraph.
                                * If an exact subject is difficult to visualize, use a closely related general visual concept.
                                * The three keywords should ideally represent different visual possibilities.

                                Return ONLY the three comma-separated keywords. Don't add any text before or after list and list should mandatory contain only three keywords.

                                NEWS/ARTICLE PARAGRAPH:
                                {content}

                                """

        try:
            res = self.client.generate(prompt=prompt, response_model=ImageKeywordsResponse, role="system")
            if res and res.keywords:
                clean_kws = [k.strip() for k in res.keywords if k.strip()]
                if clean_kws:
                    return ", ".join(clean_kws[:3])
        except Exception as e:
            logger.warning(f"Structured image keyword extraction failed: {e}. Falling back to raw response.")

        try:
            raw = self.client.generate_raw(prompt=prompt, role="system")
            cleaned = raw.strip().replace("\n", ", ")
            return cleaned
        except Exception as e:
            logger.error(f"Image keyword generation failed: {e}")
            return "news, technology, global"

    def generate_keywords_list(self, content: str) -> List[str]:
        """Convenience method returning a validated list of keyword strings."""
        result_str = self.generate_keywords(content)
        parts = [p.strip() for p in result_str.split(",") if p.strip()]
        return parts[:3]