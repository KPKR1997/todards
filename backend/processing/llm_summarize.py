import ollama
import json
import requests
from datetime import datetime


class LlmSummarizer:
    def __init__(self, base_url, model):
        self.base_url = base_url
        self.model = model

    def summarize(self, content):
        response = requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "messages" : [
                    {
                        "role": "system",
                        "content": f"""
                        
                        You are an efficient news summarizer
                        
                        You need to go through the paragraphs thourohly and summarize the relevant portion only in below 7 sentences. 
                        The paragraph will be a news content, you need to answer below information to summarise if available in paragraph -  this is mandatory
    
                        Points to look for in summarizing is given below. Don't answer it point by point but return a natural paragraph which includes them very professionally.

                        Read the entire provided news content and produce a concise, factual summary in ONE natural paragraph of 100–120 words.

                        The summary should:

                        Start with the most important development.
                        Clearly explain what happened and where.
                        Identify the key people, organizations, or groups involved when relevant.
                        Include important numbers, dates, locations, and measurable impacts.
                        Explain significant consequences or risks when mentioned in the article.
                        Include relevant context needed to understand why the event matters.
                        Expand important abbreviations on first use, such as MMR (measles, mumps and rubella).
                        If multiple related developments are covered, connect them naturally in the same paragraph.
                        Prioritize the most important information and omit minor details, quotes, background history, and repetition.
                        Do not introduce information that is not present in the provided content.
                        Use clear, professional language suitable for a news website.
                        Do not use bullet points, headings, numbering, or quotation marks around the summary.
                        Return ONLY the summary paragraph.
                        
                        
                        So use the above instructions to summarize the paragraph. The tone should be very professional and should sound like an experienced news journalist reporting. 
                        Don't loose any important points which cause issues or trade off to health and other risk elements. Care to be given if it's health or security related ad in exceptional cases and worst case scenarios.
                        
    
                        Here is the paragraph: {content}
    
                        You need to give output strictly in string format and within 120 words.
                        
    
                        Don't add any wrapping texts like 'here is...', 'Find the...', 'Here is the summary:..' etc

                        """
                    }
                ],
                "stream":False
            },
            timeout=600
        )
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]



