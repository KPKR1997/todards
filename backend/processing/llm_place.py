import logging
from typing import Optional
from backend.core.ollama_client import OllamaClient
from backend.core.schemas import PlaceResponse, PlaceValidationResponse
from config.settings import OLLAMA_BASE_URL, OLLAMA_MODEL

logger = logging.getLogger("todards.place")


class LlmPlacefinder:
    def __init__(self, base_url=None, model=None, client: Optional[OllamaClient] = None):
        self.base_url = base_url or OLLAMA_BASE_URL
        self.model = model or OLLAMA_MODEL
        self.client = client or OllamaClient(base_url=self.base_url, model=self.model)

    def trace_location(self, content: str, remarks: str = "") -> str:
        prompt = f"""

                        {remarks}

                        You are a news-location extraction system.

                        Read the news paragraph and determine the single best geographic location to associate with the story.

                        Follow this priority order:

                        1. INCIDENT / EVENT LOCATION
                        If the paragraph explicitly states where the event, accident, discovery, attack, launch, meeting, study, disaster, or other main event happened, return that location.

                        2. SPECIFIC LOCATION
                        Prefer the most specific useful location available. For example,
                        - City + country → "Tokyo, Japan"
                        - Town + country → "Cannes, France"
                        - State/province + country → "Kerala, India"
                        - Country only → "Japan"
        

                        3. VENUE / FACILITY / INSTITUTION LOCATION
                        If the event occurred at a named facility, laboratory, hospital, airport, university, stadium, government building, research centre, or other identifiable place, use the city/country where that facility is located if available.

                        4. REPORTING LOCATION
                        If the actual incident location cannot be determined, identify the location from which the report is being filed or where the journalist/news organisation explicitly places the report.
                        Examples:
                        - "Reporting from Tokyo" → "Tokyo, Japan"
                        - "Our correspondent in London reports..." → "London, UK"

                        5. OFFICIAL / ORGANIZATIONAL LOCATION
                        If neither the incident location nor reporting location is available, use the relevant organisation's principal headquarters location when it is clearly relevant to the story.
                        Examples:
                        - A NASA announcement with no event location → "Washington, USA"
                        - A WHO announcement with no event location → "Geneva, Switzerland"
                        - ISRO Launched 9 orbital satelites yesterda... - "Bengaluru, India"
                        Do not use an organisation's headquarters merely because its name appears in the article, If the news is coming from that organization, you can do it

                        6. SUBJECT LOCATION
                        If the story concerns a person, company, project, research institution, government, or event whose location is central to the story, use the most relevant location associated with that subject when no better event/reporting location exists.

                        7. GEOGRAPHIC SCOPE
                        If the story clearly concerns an entire country, return the country.
                        If it concerns multiple countries or a genuinely worldwide development and no single location is dominant, return "Global, general"

                        8. DO NOT GUESS
                        Never infer a location merely from:
                        - the nationality of a person
                        - the nationality of a company
                        - the language of the article
                        - the news publisher's country
                        - an unrelated place mentioned in background information
                        - a person's birthplace
                        - a company's founding location

                        9. LOCATION MENTIONED ONLY AS BACKGROUND
                        Do not select a geographic location if it is mentioned only as historical context, comparison, example, previous research, or unrelated background.

                        10. CONFLICTING LOCATIONS
                            If several locations are present, select the location most directly connected to the main news reporting point.
                            Do not combine unrelated locations.
            

                        IMPORTANT OUTPUT RULE:
                        Return ONLY the location string

                        Your entire response must contain exactly ONE location string with no more than one line or 3 words.

                        Examples:
                        Tokyo, Japan
                        Japan
                        Geneva, Switzerland
                        Global

                        NEWS PARAGRAPH:
                        {content}
                        """

        try:
            res = self.client.generate(prompt=prompt, response_model=PlaceResponse, role="system")
            if res and res.place:
                return self._clean_place(res.place)
        except Exception as e:
            logger.warning(f"Structured place extraction failed: {e}. Falling back to raw response.")

        try:
            raw = self.client.generate_raw(prompt=prompt, role="system")
            return self._clean_place(raw)
        except Exception as e:
            logger.error(f"Place extraction failed: {e}")
            return "Global"

    def _clean_place(self, text: str) -> str:
        if not text:
            return "Global"
        cleaned = text.strip().splitlines()[0].strip()
        cleaned = cleaned.replace('"', '').replace("'", "").strip()
        if cleaned.startswith("place:"):
            cleaned = cleaned[6:].strip()
        return cleaned or "Global"

    def validate_place(self, content: str, place: str):
        prompt = f"""
        
        You are a validation system. You are given a place and a news/article paragraph. The place is identified by an LLM system using the paragraph.
        Your duty is to validate the place is valid and relevant to the paragraph according to criterias given to place identification LLM. If LLM identification
        is good, Return "True" else "False".

        Below was the instructions given to LLM:

        priority order considered:
            1. INCIDENT / EVENT LOCATION
            2. SPECIFIC LOCATION
            3. VENUE / FACILITY / INSTITUTION LOCATION
            4. REPORTING LOCATION
            5. OFFICIAL / ORGANIZATIONAL LOCATION
            6. SUBJECT LOCATION
            7. GEOGRAPHIC SCOPE
            8. DO NOT GUESS
            9. LOCATION MENTIONED ONLY AS BACKGROUND
            10. CONFLICTING LOCATIONS

        Below is the news/article paragraph

        NEWS PARAGRAPH:
        {content}

        And the place identified is : {place}

        Important - Return only "True" or "False" Boolean value only, no any explanation or add on reslts
        """

        try:
            res = self.client.generate(prompt=prompt, response_model=PlaceValidationResponse, role="system")
            return ["True"] if res.is_valid else ["False"]
        except Exception:
            try:
                raw = self.client.generate_raw(prompt=prompt, role="system")
                return raw.split()
            except Exception:
                return ["True"]
