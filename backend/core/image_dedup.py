"""
Todards Pipeline — Image Deduplication Utilities

Provides canonical image ID extraction and perceptual hashing to guarantee
zero duplicate images across cards, categories, and runs.
"""

import re
import hashlib
from io import BytesIO
from urllib.parse import urlsplit
from typing import Optional, List, Tuple
from PIL import Image
import numpy as np


def get_canonical_image_id(image_url: str) -> str:
    """
    Extract a query-param-independent canonical identifier for any image URL.
    - Unsplash: extracts photo ID (e.g., 'unsplash:photo-1697577418970-95d99b5a55cf')
    - Pexels: extracts photo ID (e.g., 'pexels:17428267')
    - Wikimedia/Wikipedia: extracts filename
    - Generic: extracts scheme + domain + clean path
    """
    if not image_url or not isinstance(image_url, str):
        return ""
    image_url = image_url.strip()

    # 1. Unsplash photo ID
    if "unsplash.com" in image_url:
        match = re.search(r"(photo-[a-zA-Z0-9_-]+)", image_url)
        if match:
            return f"unsplash:{match.group(1)}"

    # 2. Pexels photo ID
    if "pexels.com" in image_url:
        match = re.search(r"/photos/(\d+)", image_url)
        if match:
            return f"pexels:{match.group(1)}"

    # 3. Wikipedia / Wikimedia commons
    if "wikimedia.org" in image_url or "wikipedia.org" in image_url:
        parts = urlsplit(image_url)
        filename = parts.path.split("/")[-1]
        return f"wiki:{filename.lower()}"

    # 4. Generic fallback: scheme + domain + path (strip query & fragment)
    parts = urlsplit(image_url)
    clean = f"{parts.scheme.lower()}://{parts.netloc.lower()}{parts.path}".rstrip("/")
    return clean


def compute_perceptual_hash(image_bytes: Optional[bytes]) -> Optional[int]:
    """
    Compute a 256-bit perceptual hash (difference hash / dHash) from image bytes.
    Robust to resizing, compression artifacts, and slight crops.
    """
    if not image_bytes:
        return None

    try:
        image = Image.open(BytesIO(image_bytes)).convert("L")
        width, height = image.size
        side = min(width, height)
        left = (width - side) // 2
        top = (height - side) // 2
        image = image.crop((left, top, left + side, top + side))
        image = image.resize((16, 16), Image.Resampling.LANCZOS)

        pixels = np.asarray(image, dtype=np.float32)
        average = pixels.mean()
        bits = (pixels >= average).flatten()

        value = 0
        for bit in bits:
            value = (value << 1) | int(bit)

        return value
    except Exception:
        return None


def perceptual_distance(hash_a: Optional[int], hash_b: Optional[int]) -> int:
    """Compute Hamming distance between two perceptual hashes."""
    if hash_a is None or hash_b is None:
        return 10**9
    return (hash_a ^ hash_b).bit_count()


def is_perceptual_match(hash_a: Optional[int], hash_b: Optional[int], threshold: int = 18) -> bool:
    """Return True if two images are visually identical or nearly identical."""
    return perceptual_distance(hash_a, hash_b) <= threshold
