"""
Todards Pipeline — Pydantic Schemas

Data contracts for every LLM interaction and internal data exchange.
Using Pydantic ensures structured, validated outputs from Ollama
with zero format hallucination.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator


# ============================================================
# SUMMARIZER
# ============================================================

class SummaryResponse(BaseModel):
    """Structured output from the summarization LLM."""
    summary: str = Field(
        ...,
        min_length=1,
        description=(
            "The final news summary as plain text. "
            "Return only the summary paragraph itself. "
            "Do not include JSON, braces, field names, labels, "
            "markdown, quotation marks, or introductory text."
        )
    )

# ============================================================
# PLACE FINDER
# ============================================================

class PlaceResponse(BaseModel):
    """Structured output from the location extraction LLM."""
    place: str = Field(
        ...,
        description="Geographic location string, e.g. 'Tokyo, Japan'"
    )


class PlaceValidationResponse(BaseModel):
    """Structured output from the place validation LLM."""
    is_valid: bool = Field(
        ...,
        description="Whether the identified place is valid and relevant"
    )


# ============================================================
# HEADLINE
# ============================================================

class HeadlineResponse(BaseModel):
    """Structured output from the headline writer/editor LLM."""
    headline: str = Field(
        ...,
        description="Professional news headline, max 14 words"
    )


# ============================================================
# IMAGE KEYWORDS
# ============================================================

class ImageKeywordsResponse(BaseModel):
    """Structured output from the image keyword generator LLM."""
    keywords: List[str] = Field(
        ...,
        description="Exactly 3 image-search keywords",
        min_length=1,
        max_length=5
    )

    @field_validator("keywords")
    @classmethod
    def strip_keywords(cls, v):
        return [kw.strip() for kw in v if kw.strip()]


# ============================================================
# KEYWORD CLASSIFIER (PERSON vs OTHER)
# ============================================================

class KeywordClassificationItem(BaseModel):
    """Single keyword classification."""
    keyword: str
    type: Literal["PERSON", "OTHER"] = "OTHER"


class KeywordClassificationResponse(BaseModel):
    """Structured output from keyword classifier LLM."""
    classifications: List[KeywordClassificationItem]


# ============================================================
# ARTICLE ANALYSIS (for ranking)
# ============================================================

class EventFlags(BaseModel):
    """Boolean flags for major event types."""
    major_disaster: bool = False
    mass_casualties: bool = False
    pandemic: bool = False
    election: bool = False
    major_political_change: bool = False
    major_economic_event: bool = False
    major_award: bool = False
    celebrity_death: bool = False
    record_breaking: bool = False
    unprecedented_event: bool = False
    major_scientific_discovery: bool = False
    major_technology_event: bool = False


class ArticleAnalysisResponse(BaseModel):
    """Structured output from the article importance analyzer."""
    everyday_impact: int = Field(0, ge=0, le=100)
    dont_miss: int = Field(0, ge=0, le=100)
    human_consequence: int = Field(0, ge=0, le=100)
    economic_impact: int = Field(0, ge=0, le=100)
    political_significance: int = Field(0, ge=0, le=100)
    health_significance: int = Field(0, ge=0, le=100)
    scientific_significance: int = Field(0, ge=0, le=100)
    entertainment_significance: int = Field(0, ge=0, le=100)
    remarkability: int = Field(0, ge=0, le=100)
    global_reach: int = Field(0, ge=0, le=100)
    urgency: int = Field(0, ge=0, le=100)
    severity_tier: int = Field(1, ge=1, le=5)
    events: EventFlags = Field(default_factory=EventFlags)
    reason: str = ""

    @field_validator(
        "everyday_impact", "dont_miss", "human_consequence",
        "economic_impact", "political_significance",
        "health_significance", "scientific_significance",
        "entertainment_significance", "remarkability",
        "global_reach", "urgency",
        mode="before"
    )
    @classmethod
    def clamp_score(cls, v):
        try:
            v = int(v)
        except (ValueError, TypeError):
            return 0
        return max(0, min(100, v))

    @field_validator("severity_tier", mode="before")
    @classmethod
    def clamp_tier(cls, v):
        try:
            v = int(v)
        except (ValueError, TypeError):
            return 1
        return max(1, min(5, v))


# ============================================================
# CATEGORY VALIDATION
# ============================================================

class CategoryValidationResponse(BaseModel):
    """Structured output from category cross-validation LLM."""
    assigned_category: str = Field(
        ...,
        description="The category this article best belongs to"
    )
    confidence: float = Field(
        0.5,
        ge=0.0,
        le=1.0,
        description="Confidence score for the category assignment"
    )
    reason: str = Field(
        "",
        description="Brief explanation of the classification"
    )

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, v):
        try:
            v = float(v)
        except (ValueError, TypeError):
            return 0.5
        return max(0.0, min(1.0, v))


# ============================================================
# CONTENT GUARDRAILS
# ============================================================

class GuardrailResponse(BaseModel):
    """Structured output from the content guardrail LLM."""
    is_safe: bool = Field(
        True,
        description="False if contains NSFW, toxic, abusive, or adult content"
    )
    is_factual: bool = Field(
        True,
        description="False if content is gossip, rumor, or unverified claims"
    )
    is_neutral: bool = Field(
        True,
        description="False if promotes toxic agendas or propaganda"
    )
    flags: List[str] = Field(
        default_factory=list,
        description="List of specific flags triggered"
    )
    reason: str = Field(
        "",
        description="Brief explanation of the guardrail assessment"
    )


# ============================================================
# NEWS vs ARTICLE CLASSIFIER
# ============================================================

class ContentTypeResponse(BaseModel):
    """Structured output from the news/article classifier."""
    content_type: Literal["NEWS", "ARTICLE"] = "NEWS"


# ============================================================
# INTERNAL DATA MODELS
# ============================================================

class ArticleRecord(BaseModel):
    """Internal representation of an article during pipeline processing."""
    id: str = ""
    title: str = ""
    content: str = ""
    category: str = ""
    source: Optional[str] = None
    url: Optional[str] = None
    published_at: Optional[str] = None
    file_path: Optional[str] = None
    article_index: int = 0
    folder: str = ""


class ProcessedArticle(BaseModel):
    """Final processed article ready for todards.json."""
    id: str
    category: str
    title: str
    image: str
    place: str
    time: str
    content: str
