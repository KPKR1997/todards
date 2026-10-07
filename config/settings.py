"""
Todards Pipeline — Central Configuration

Single source of truth for all constants, paths, thresholds, and model settings.
Modify values here instead of scattering magic numbers across the codebase.
"""

from pathlib import Path


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_ROOT = PROJECT_ROOT / "data"
IMAGE_DIR = PROJECT_ROOT / "images"
FRONTEND_DATA_DIR = PROJECT_ROOT / "frontend" / "public" / "data"
TODARDS_JSON_PATH = FRONTEND_DATA_DIR / "todards.json"
BACKUP_ROOT = DATA_ROOT / "backup"
RAG_STORE_DIR = DATA_ROOT / "rag_store"
EVALUATION_DIR = PROJECT_ROOT / "evaluation"
EVALUATION_REPORTS_DIR = EVALUATION_DIR / "reports"
IMAGE_HISTORY_PATH = DATA_ROOT / "image_history.json"


# ============================================================
# DATA FOLDERS (category → folder name)
# ============================================================

CATEGORY_FOLDERS = {
    "health": "health_data",
    "science and technology": "tech_data",
    "people": "people_data",
    "earth and environment": "environment_data",
    "economy and business": "economy_data",
    "entertainment": "entertainment_data",
}

# Ordered list for pipeline processing
ALL_DATA_FOLDERS = [
    "health_data",
    "tech_data",
    "people_data",
    "environment_data",
    "economy_data",
    "entertainment_data"
]


# ============================================================
# OLLAMA SETTINGS
# ============================================================

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3:latest"
OLLAMA_TIMEOUT = 120  # seconds
OLLAMA_MAX_RETRIES = 2
OLLAMA_RETRY_DELAY = 3  # seconds


# ============================================================
# DEDUPLICATION SETTINGS
# ============================================================

DEDUP_SIMILARITY_THRESHOLD = 0.75
DEDUP_CROSS_DAY_THRESHOLD = 0.85
DEDUP_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
DEDUP_HISTORY_DAYS = 5
DEDUP_TFIDF_OVERLAP_THRESHOLD = 0.6


# ============================================================
# RANKING SETTINGS
# ============================================================

RANKING_TOP_N = 3
RANKING_SIMILARITY_THRESHOLD = 0.78


# ============================================================
# IMAGE SETTINGS
# ============================================================

IMAGE_HISTORY_DAYS = 6
IMAGE_PEXELS_PER_KEYWORD = 3
IMAGE_UNSPLASH_PER_KEYWORD = 2
IMAGE_PERCEPTUAL_HASH_THRESHOLD = 18
IMAGE_SCORER_MODEL = "google/siglip-base-patch16-224"
IMAGE_KEYWORD_CLASSIFIER_MODEL = "llama3:latest"


# ============================================================
# CONTENT GUARDRAIL SETTINGS
# ============================================================

GUARDRAIL_ENABLED = True


# ============================================================
# CATEGORY VALIDATION SETTINGS
# ============================================================

CATEGORY_VALIDATION_ENABLED = True
CATEGORY_VALIDATION_CONFIDENCE_THRESHOLD = 0.6


# ============================================================
# RAG SETTINGS
# ============================================================

RAG_ENABLED = True
RAG_SIMILARITY_THRESHOLD = 0.7
RAG_MAX_HISTORY_RESULTS = 3
RAG_COLLECTION_NAME = "todards_articles"


# ============================================================
# TODARDS CATEGORIES (for validation and classification)
# ============================================================

TODARDS_CATEGORIES = [
    "people",
    "science and technology",
    "health",
    "earth and environment",
    "entertainment",
    "economy and business",
]

# Section ID mapping in todards.json
SECTION_ID_MAP = {
    "people": "people",
    "entertainment": "entertainment",
    "health": "health",
    "earth and environment": "earth and environment",
    "sports and entertainment": "sports and entertainment",
    "economy and business": "economy and business",
}
