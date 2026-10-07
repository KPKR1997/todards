"""
Todards Pipeline — Category Definitions and Mappings

Central definition of news categories, display titles, folder mappings,
and validation rules.
"""

from typing import Dict, List

# Standard categories in Todards
CATEGORIES: List[str] = [
    "people",
    "science and technology",
    "health",
    "earth and environment",
    "entertainment",
    "economy and business",
]

# Display names for UI / frontend
CATEGORY_DISPLAY_NAMES: Dict[str, str] = {
    "people": "People",
    "science and technology": "Science & Technology",
    "health": "Health",
    "earth and environment": "Earth & Environment",
    "entertainment": "Sports & Entertainment",
    "economy and business": "Economy & Business",
}

# Mapping from folder name to canonical category name
FOLDER_TO_CATEGORY: Dict[str, str] = {
    "health_data": "health",
    "tech_data": "science and technology",
    "people_data": "people",
    "environment_data": "earth and environment",
    "economy_data": "economy and business",
    "entertainment_data": "entertainment",
}

# Mapping from canonical category name to folder name
CATEGORY_TO_FOLDER: Dict[str, str] = {
    v: k for k, v in FOLDER_TO_CATEGORY.items()
}

# Folder priority when resolving duplicate articles across categories
# Higher priority retains the article, lower priority deletes/yields
CATEGORY_PRIORITY: Dict[str, int] = {
    "economy_data": 5,
    "tech_data": 4,
    "health_data": 3,
    "environment_data": 2,
    "people_data": 1,
    "entertainment_data": 0,
}
