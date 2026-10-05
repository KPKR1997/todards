import ollama
import json
import requests
from datetime import datetime


class LlmContentClasifier:
    def __init__(self, base_url, model):
        self.base_url = base_url
        self.model = model

    def classify_content(self, content):
        response = requests.post(
            f"{self.base_url}/api/chat",
            json ={
                "model": self.model,
                "messages" : [
                    {
                        "role": "system",
                        "content": 
                        f"""

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
                    }
                ],
                "stream": False
            },
            timeout=120
        )

        response.raise_for_status()

        data = response.json()
   
        result = data["message"]["content"].split()
        return result

    
