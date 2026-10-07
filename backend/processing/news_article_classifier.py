import logging
from typing import Optional, List
from backend.core.ollama_client import OllamaClient
from backend.core.schemas import ContentTypeResponse
from config.settings import OLLAMA_BASE_URL, OLLAMA_MODEL

logger = logging.getLogger("todards.classifier")


class LlmContentClasifier:
    def __init__(self, base_url=None, model=None, client: Optional[OllamaClient] = None):
        self.base_url = base_url or OLLAMA_BASE_URL
        self.model = model or OLLAMA_MODEL
        self.client = client or OllamaClient(base_url=self.base_url, model=self.model)

    def classify_content(self, content: str) -> List[str]:
        prompt = f"""

                        You are an expert news editor. Classify the provided content into exactly ONE category:

                        'news' or 'article'

                        Return only: NEWS or ARTICLE.

                        ### NEWS

                        Choose NEWS when the main purpose is reporting a specific current or identifiable development, event, announcement, discovery, incident, investigation finding, decision, launch, outbreak, result, or other recent change.

                        A NEWS report may contain background, history, expert opinions, interviews, and explanations. These do not make it an ARTICLE if they mainly provide context for a current development.

                        ### ARTICLE

                        Choose ARTICLE when the main purpose is explaining, educating, analyzing, reviewing, comparing, interpreting, or providing broad background about a topic rather than reporting a specific development.

                        ### Tricky cases
                        Do not classify based on length, topic, number of facts, or amount of background.
                        Ask:
                        "What is the primary purpose of this content?"

                        If background explains a current event → NEWS.
                        If a current event is only used to explain a broader topic → ARTICLE.
                        If multiple current developments are being reported → NEWS.
                        Human-interest or investigative reporting can still be NEWS if a specific current development is the focus.

                        Return only one word:
                        'news'
                        or
                        'article'

                        Content is:

                        {content}
                        """

        try:
            res = self.client.generate(prompt=prompt, response_model=ContentTypeResponse, role="system")
            if res and res.content_type:
                return [res.content_type.upper()]
        except Exception as e:
            logger.warning(f"Structured content classification failed: {e}. Falling back to raw response.")

        try:
            raw = self.client.generate_raw(prompt=prompt, role="system")
            words = raw.strip().upper().split()
            if "ARTICLE" in words:
                return ["ARTICLE"]
            return ["NEWS"]
        except Exception as e:
            logger.error(f"Content classification failed: {e}")
            return ["NEWS"]
