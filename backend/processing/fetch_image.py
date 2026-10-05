import os
import json
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO
from ollama import chat


load_dotenv()


# ============================================================
# KEYWORD CLASSIFIER
# ============================================================

class KeywordClassifier:

    def __init__(self, model="llama3.1:latest"):
        self.model = model

    def classify(self, keywords):

        prompt = f"""
Classify each image-search keyword as either PERSON or OTHER.

PERSON:
A specific identifiable real person.

OTHER:
Everything else, including countries, cities, organizations,
companies, buildings, places, events, objects, animals,
concepts, diseases, professions, groups, products, etc.

Keywords:
{json.dumps(keywords)}

Return ONLY valid JSON:

[
    {{"keyword": "Donald Trump", "type": "PERSON"}},
    {{"keyword": "White House", "type": "OTHER"}}
]

Do not add explanations.
"""

        response = chat(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        text = response.message.content.strip()

        if text.startswith("```"):
            text = text.replace("```json", "")
            text = text.replace("```", "")
            text = text.strip()

        return json.loads(text)


# ============================================================
# WIKIPEDIA
# ============================================================

class WikiImageFetcher:

    BASE_URL = "https://en.wikipedia.org/wiki/"

    def __init__(self):

        self.headers = {
            "User-Agent": "Todards/1.0"
        }

    def get_image_url(self, person_name):

        keyword = person_name.replace(" ", "_")

        url = urljoin(
            self.BASE_URL,
            keyword
        )

        response = requests.get(
            url,
            headers=self.headers,
            timeout=20
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        image = soup.select_one(
            "table.infobox img.mw-file-element"
        )

        if not image:
            return None

        # Prefer highest-resolution image
        srcset = image.get("srcset")

        if srcset:

            candidates = []

            for item in srcset.split(","):

                parts = item.strip().split()

                if len(parts) < 2:
                    continue

                image_url = parts[0]

                try:

                    scale = float(
                        parts[1].replace("x", "")
                    )

                    candidates.append(
                        (scale, image_url)
                    )

                except ValueError:
                    continue

            if candidates:

                candidates.sort(
                    key=lambda x: x[0],
                    reverse=True
                )

                src = candidates[0][1]

            else:
                src = image.get("src")

        else:
            src = image.get("src")

        if not src:
            return None

        if src.startswith("//"):
            src = "https:" + src

        return src

    def get_image(self, person_name):

        try:

            image_url = self.get_image_url(
                person_name
            )

            if not image_url:
                return None

            response = requests.get(
                image_url,
                headers=self.headers,
                timeout=30
            )

            response.raise_for_status()

            return {
                "source": "wikipedia",
                "keyword": person_name,
                "url": image_url,
                "content": response.content
            }

        except Exception as e:

            print(
                f"Wikipedia failed for "
                f"{person_name}: {e}"
            )

            return None


# ============================================================
# PEXELS
# ============================================================

class PexelImageFetcher:

    SEARCH_URL = "https://api.pexels.com/v1/search"

    def __init__(self):

        self.api_key = os.getenv(
            "PEXEL_API_KEY"
        )

        if not self.api_key:
            raise RuntimeError(
                "PEXEL_API_KEY is missing from .env"
            )

        self.headers = {
            "Authorization": self.api_key
        }

    def get_images(
        self,
        keyword,
        per_page=2
    ):

        params = {
            "query": keyword,
            "per_page": per_page,
            "orientation": "portrait"
        }

        response = requests.get(
            self.SEARCH_URL,
            headers=self.headers,
            params=params,
            timeout=20
        )

        response.raise_for_status()

        photos = response.json().get(
            "photos",
            []
        )

        results = []

        for photo in photos:

            image_url = photo["src"]["large"]

            try:

                image_response = requests.get(
                    image_url,
                    headers={
                        "User-Agent": "Todards/1.0"
                    },
                    timeout=30
                )

                image_response.raise_for_status()

                picture = Image.open(
                    BytesIO(
                        image_response.content
                    )
                )

                # Center crop to square
                width, height = picture.size

                side = min(
                    width,
                    height
                )

                left = (
                    width - side
                ) // 2

                top = (
                    height - side
                ) // 2

                square = picture.crop(
                    (
                        left,
                        top,
                        left + side,
                        top + side
                    )
                )

                buffer = BytesIO()

                square.convert(
                    "RGB"
                ).save(
                    buffer,
                    format="JPEG"
                )

                results.append({
                    "source": "pexels",
                    "keyword": keyword,
                    "url": image_url,
                    "content": buffer.getvalue()
                })

            except Exception as e:

                print(
                    f"Pexels image failed: {e}"
                )

        return results


# ============================================================
# UNSPLASH
# ============================================================

class UnsplashDownloader:

    SEARCH_URL = (
        "https://api.unsplash.com/search/photos"
    )

    def __init__(self):

        self.access_key = os.getenv(
            "UNSPLASH_ACCESS_KEY"
        )

        if not self.access_key:
            raise RuntimeError(
                "UNSPLASH_ACCESS_KEY is missing"
            )

        self.headers = {
            "Authorization":
                f"Client-ID {self.access_key}",
            "Accept-Version": "v1"
        }

    def get_images(
        self,
        keyword,
        per_page=5
    ):

        params = {
            "query": keyword,
            "page": 1,
            "per_page": per_page,
            "orientation": "landscape",
            "content_filter": "high"
        }

        response = requests.get(
            self.SEARCH_URL,
            headers=self.headers,
            params=params,
            timeout=20
        )

        response.raise_for_status()

        photos = response.json().get(
            "results",
            []
        )

        results = []

        for photo in photos:

            image_url = photo["urls"]["regular"]

            try:

                image_response = requests.get(
                    image_url,
                    headers={
                        "User-Agent": "Todards/1.0"
                    },
                    timeout=30
                )

                image_response.raise_for_status()

                results.append({
                    "source": "unsplash",
                    "keyword": keyword,
                    "url": image_url,
                    "content": image_response.content
                })

            except Exception as e:

                print(
                    f"Unsplash image failed: {e}"
                )

        return results


# ============================================================
# COMPLETE IMAGE FETCHER
# ============================================================

class ImageFetcher:

    def __init__(
        self,
        model="llama3.1:latest"
    ):

        self.classifier = KeywordClassifier(
            model=model
        )

        self.wikipedia = WikiImageFetcher()
        self.pexels = PexelImageFetcher()
        self.unsplash = UnsplashDownloader()

        # All images go here
        self.output_dir = Path("images")

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

    # --------------------------------------------------------
    # SAVE IMAGE
    # --------------------------------------------------------

    def save_image(
        self,
        image_data,
        image_id
    ):

        filename = f"{image_id}.jpg"

        output_file = (
            self.output_dir /
            filename
        )

        output_file.write_bytes(
            image_data["content"]
        )

        return {
            "image_id": image_id,
            "source": image_data["source"],
            "keyword": image_data["keyword"],
            "url": image_data["url"],
            "local_path": str(output_file)
        }

    # --------------------------------------------------------
    # GET ONE FALLBACK IMAGE
    # --------------------------------------------------------

    def get_fallback_image(
        self,
        keyword
    ):

        print(
            f"  → Wikipedia failed."
        )

        print(
            f"  → Searching fallback image..."
        )

        # First try Pexels
        try:

            images = self.pexels.get_images(
                keyword=keyword,
                per_page=1
            )

            if images:
                return images[0]

        except Exception as e:

            print(
                f"Pexels fallback failed: {e}"
            )

        # Then try Unsplash
        try:

            images = self.unsplash.get_images(
                keyword=keyword,
                per_page=1
            )

            if images:
                return images[0]

        except Exception as e:

            print(
                f"Unsplash fallback failed: {e}"
            )

        return None

    # --------------------------------------------------------
    # MAIN
    # --------------------------------------------------------

    def get_images(
        self,
        keywords,
        image_id,
        pexels_per_keyword=2,
        unsplash_per_keyword=2
    ):

        results = []

        # ----------------------------------------------------
        # ONE LLM CALL
        # ----------------------------------------------------

        classifications = (
            self.classifier.classify(
                keywords
            )
        )

        print("\nClassifications:")

        for item in classifications:

            print(
                f"  {item['keyword']} "
                f"→ {item['type']}"
            )

        image_counter = 1

        # ----------------------------------------------------
        # PROCESS KEYWORDS
        # ----------------------------------------------------

        for item in classifications:

            keyword = item["keyword"]
            keyword_type = item["type"]

            print(
                f"\nProcessing: {keyword}"
            )

            # =================================================
            # PERSON
            # =================================================

            if keyword_type == "PERSON":

                print(
                    "  → Wikipedia"
                )

                wiki_image = (
                    self.wikipedia.get_image(
                        person_name=keyword
                    )
                )

                if wiki_image:

                    current_id = (
                        f"{image_id}_{image_counter}"
                    )

                    result = self.save_image(
                        wiki_image,
                        current_id
                    )

                    results.append(result)

                    image_counter += 1

                else:

                    # -----------------------------------------
                    # WIKIPEDIA FAILED → FALLBACK
                    # -----------------------------------------

                    fallback = (
                        self.get_fallback_image(
                            keyword
                        )
                    )

                    if fallback:

                        current_id = (
                            f"{image_id}_{image_counter}"
                        )

                        result = self.save_image(
                            fallback,
                            current_id
                        )

                        results.append(result)

                        image_counter += 1

                    else:

                        print(
                            f"  No image found "
                            f"for {keyword}"
                        )

            # =================================================
            # OTHER
            # =================================================

            else:

                print(
                    "  → Pexels + Unsplash"
                )

                # ---------------------------------------------
                # PEXELS
                # ---------------------------------------------

                try:

                    images = (
                        self.pexels.get_images(
                            keyword=keyword,
                            per_page=pexels_per_keyword
                        )
                    )

                    for image in images:

                        current_id = (
                            f"{image_id}_{image_counter}"
                        )

                        result = self.save_image(
                            image,
                            current_id
                        )

                        results.append(result)

                        image_counter += 1

                except Exception as e:

                    print(
                        f"Pexels failed: {e}"
                    )

                # ---------------------------------------------
                # UNSPLASH
                # ---------------------------------------------

                try:

                    images = (
                        self.unsplash.get_images(
                            keyword=keyword,
                            per_page=unsplash_per_keyword
                        )
                    )

                    for image in images:

                        current_id = (
                            f"{image_id}_{image_counter}"
                        )

                        result = self.save_image(
                            image,
                            current_id
                        )

                        results.append(result)

                        image_counter += 1

                except Exception as e:

                    print(
                        f"Unsplash failed: {e}"
                    )

        return results


