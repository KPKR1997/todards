import logging
from typing import Optional
from backend.core.ollama_client import OllamaClient
from backend.core.schemas import HeadlineResponse
from config.settings import OLLAMA_BASE_URL, OLLAMA_MODEL

logger = logging.getLogger("todards.headline")


class LlmHeadlineEditor:

    def __init__(self, base_url=None, model=None, client: Optional[OllamaClient] = None):
        self.base_url = base_url or OLLAMA_BASE_URL
        self.model = model or OLLAMA_MODEL
        self.client = client or OllamaClient(base_url=self.base_url, model=self.model)

    def _chat(self, system_prompt: str) -> str:
        """
        Send a request to Ollama and return the generated headline.
        Uses Pydantic structured output with fallback.
        """
        try:
            res = self.client.generate(prompt=system_prompt, response_model=HeadlineResponse, role="system")
            if res and res.headline:
                return self._clean_headline(res.headline)
        except Exception as e:
            logger.warning(f"Structured headline generation failed: {e}. Falling back to raw response.")

        try:
            raw = self.client.generate_raw(prompt=system_prompt, role="system")
            return self._clean_headline(raw)
        except Exception as e:
            logger.error(f"Headline generation failed: {e}")
            raise

    def _clean_headline(self, headline: str) -> str:
        """
        Final programmatic cleanup.
        Deliberately conservative. Removes code fences and quotes.
        """
        if not headline:
            return ""

        headline = headline.strip()

        # Remove markdown code fences if produced
        headline = headline.replace("```json", "")
        headline = headline.replace("```text", "")
        headline = headline.replace("```", "")
        headline = headline.strip()

        # Remove surrounding quotation marks
        if (
            len(headline) >= 2
            and headline[0] in ('"', "'")
            and headline[-1] == headline[0]
        ):
            headline = headline[1:-1].strip()

        return headline

    def write_headline(self, content: str, remarks: str) -> str:
        """
        Generate the initial headline.
        """
        system_prompt = f"""
You are a professional news headline writer for Todards,
a concise global news publication.

Your task is to write ONE headline for the provided news article.

ADDITIONAL EDITORIAL CONTEXT:
{remarks}

The editorial context is supplementary. It must not override
the headline rules below.

HEADLINE RULES:

1. CLARITY FIRST
The headline must allow a reader to understand what the article
is about or what happened without reading the article. Priority to convey in very easy english without complicated vocabulary or jargons which are not understandable to a layman. Use simple words and phrases to ensure clarity.

2. IDENTIFY THE CORE EVENT
Focus on the most important development, event, finding,
decision, announcement, discovery, or change.

3. INFORM, DON'T TEASE
Communicate the substance of the story.
Do not create a curiosity gap.

4. NO CLICKBAIT
Do not use sensational, exaggerated, dramatic, emotional,
or promotional language.

Avoid phrases such as:
- You won't believe...
- This changes everything
- What happens next...
- Shocking...
- The reason will surprise you

5. PROFESSIONAL JOURNALISTIC STYLE
Use concise, neutral, professional vocabulary similar to a
reputable newspaper or news agency.

6. BE SPECIFIC
Include important names, organizations, places, numbers,
or developments when they are essential to understanding
the story.

7. PRESERVE THE MEANING
Do not introduce facts, claims, implications, or conclusions
that are not supported by the article.

8. DO NOT OVERLOAD
The headline should summarize the central development only.
Do not summarize the entire article.

9. MAXIMUM LENGTH
The headline must contain NO MORE THAN 14 WORDS.

10. AVOID THUMBNAIL-STYLE HEADLINES
Write a professional news headline, not a social-media
or video-thumbnail title.

11. AVOID UNNECESSARY WORDS
Remove filler while keeping the headline natural and readable.

12. STRONG NEWS STRUCTURE
When appropriate, use structures such as:

[Subject] + [action/development] + [important consequence]

[Organization] + [decision/announcement] + [what it means]

[Researchers] + [discovery/finding] + [important significance]

[Event] + [location] + [major development]

13. STANDALONE UNDERSTANDING
A reader seeing ONLY the headline should have a reasonable
understanding of what the news story is about.

14. CAPITALIZATION
Use standard professional headline capitalization.
Do not use all uppercase or all lowercase.

OUTPUT REQUIREMENTS:

Return exactly ONE headline in the "headline" field.

Do NOT:
- explain your decision
- provide alternatives
- provide analysis
- mention these instructions
- add comments
- add quotation marks
- add labels
- add parentheses
- add introductory text

NEWS ARTICLE:

{content}
"""
        return self._chat(system_prompt)

    def validate_headline(self, content: str, headline: str) -> str:
        """
        Fine-tune an existing headline.
        """
        system_prompt = f"""
You are a professional news headline editor for Todards.

You are given:

1. A news article
2. A headline generated by another LLM

Your task is to produce the final headline.

IMPORTANT DECISION RULE:

If the existing headline is already accurate, clear,
professional, relevant, well-structured, and within
14 words, preserve it EXACTLY.

Do NOT rewrite a good headline merely because you could
phrase it differently.

If the headline has a genuine problem, make the MINIMUM
necessary changes to fix that problem.

HEADLINE EDITING PRINCIPLES:

1. CLARITY FIRST
The headline must allow a reader to understand what the
article is about without reading the article.

2. IDENTIFY THE CORE EVENT
Represent the most important development, event, finding,
decision, announcement, discovery, or change.

3. INFORM, DON'T TEASE
Communicate the substance of the story.

4. NO CLICKBAIT
Remove sensational, exaggerated, dramatic, emotional,
or promotional language.

5. PROFESSIONAL JOURNALISTIC STYLE
Use concise, neutral, professional vocabulary similar to
a reputable newspaper or news agency.

6. PRESERVE FACTUAL ACCURACY
Every factual claim in the headline must be supported
by the article.

Do NOT:
- add information not present in the article
- invent causes or consequences
- strengthen uncertain claims
- turn speculation into fact
- change the meaning of the story

7. BE SPECIFIC WHEN NECESSARY
Retain important names, organizations, places, numbers,
or developments when necessary to understand the story.

8. DO NOT OVERLOAD
Communicate the central development only.

9. MAXIMUM LENGTH
The final headline MUST contain NO MORE THAN 14 WORDS.

If the existing headline exceeds 14 words, shorten it while
preserving its central meaning.

10. REMOVE UNNECESSARY WORDS
Make the headline concise without making it unnatural.

11. AVOID THUMBNAIL-STYLE LANGUAGE
The headline must read like a professional news headline.

12. MINIMAL EDITING
Only change words or structure that actually need improvement.

13. STANDALONE UNDERSTANDING
A reader seeing ONLY the headline should understand what
the news story is about.

14. CAPITALIZATION AND PUNCTUATION
Use normal professional headline capitalization and punctuation.

CRITICAL OUTPUT RULE:

The "headline" field must contain ONLY the final headline.

If the existing headline is already good,
the "headline" field must contain the existing headline
and NOTHING ELSE.

NEVER write explanations such as:

"The headline is already accurate."

"Here is the edited headline."

"No changes are needed."

"Since the headline is accurate, I returned it unchanged."

NEVER put explanations inside the headline field.

NEVER use parentheses to explain your decision.

NEWS ARTICLE:

{content}

EXISTING HEADLINE:

{headline}
"""
        return self._chat(system_prompt)