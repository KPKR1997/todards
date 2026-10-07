import os

import json
import hashlib

import numpy as np

from pathlib import Path

from urllib.parse import urljoin



import requests

from bs4 import BeautifulSoup

from dotenv import load_dotenv

from PIL import Image

from io import BytesIO

try:
    from ollama import chat
except ImportError:
    chat = None

from backend.core.image_dedup import (
    get_canonical_image_id,
    compute_perceptual_hash,
    is_perceptual_match,
)

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



        try:
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
        except Exception as e:
            # Resilient fallback: treat all as OTHER
            return [{"keyword": kw, "type": "OTHER"} for kw in keywords]





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

        per_page=2,

        page=1

    ):



        params = {

            "query": keyword,

            "per_page": per_page,

            "page": page,

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

        per_page=5,

        page=1

    ):



        params = {

            "query": keyword,

            "page": page,

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



from pathlib import Path

from datetime import datetime, timedelta

import json





class ImageFetcher:



    def __init__(

        self,

        model="llama3.1:latest",

        history_path="data/image_history.json",

        history_days=6,

    ):



        self.classifier = KeywordClassifier(

            model=model

        )



        self.wikipedia = WikiImageFetcher()

        self.pexels = PexelImageFetcher()

        self.unsplash = UnsplashDownloader()



        # ----------------------------------------------------

        # IMAGE OUTPUT DIRECTORY

        # ----------------------------------------------------



        self.project_root = Path(__file__).resolve().parents[2]
        self.output_dir = self.project_root / "images"



        self.output_dir.mkdir(

            parents=True,

            exist_ok=True

        )



        # ----------------------------------------------------

        # IMAGE HISTORY

        # ----------------------------------------------------



        self.history_path = Path(

            history_path

        )



        self.history_days = history_days



        self.history_path.parent.mkdir(

            parents=True,

            exist_ok=True

        )



        self.image_history = (

            self.load_image_history()

        )



        # Images already used during THIS run.

        self.current_run_urls = set()
        self.current_run_hashes = set()
        self.current_run_perceptual_hashes = set()

        self.todards_json_path = self.project_root / "frontend" / "public" / "data" / "todards.json"
        self.current_todards_image_urls = set()
        self.current_todards_image_hashes = set()
        self.current_todards_perceptual_hashes = set()
        self.refresh_current_todards_images()



    # ========================================================

    # IMAGE HISTORY

    # ========================================================



    @staticmethod
    def normalize_image_url(image_url):
        return get_canonical_image_id(image_url)

    @staticmethod
    def get_content_hash(content):
        if not content:
            return ""
        try:
            return hashlib.sha256(content).hexdigest()
        except Exception:
            return ""

    @staticmethod
    def get_perceptual_hash(content):
        """Create a simple 256-bit perceptual hash from image bytes.

        The image is center-cropped to a square before hashing so that the
        hash is less sensitive to the different aspect ratios returned by
        Pexels, Unsplash and existing Todards images.
        """
        if not content:
            return None

        try:
            image = Image.open(BytesIO(content)).convert("L")
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

    @staticmethod
    def perceptual_distance(hash_a, hash_b):
        if hash_a is None or hash_b is None:
            return 10**9
        return (hash_a ^ hash_b).bit_count()

    def is_perceptual_duplicate(self, image_content, threshold=18):
        """Check an image against perceptual hashes already in Todards/current run."""
        image_hash = self.get_perceptual_hash(image_content)
        if image_hash is None:
            return False

        for existing_hash in self.current_todards_perceptual_hashes:
            if self.perceptual_distance(image_hash, existing_hash) <= threshold:
                return True

        for existing_hash in self.current_run_perceptual_hashes:
            if self.perceptual_distance(image_hash, existing_hash) <= threshold:
                return True

        return False

    def _collect_image_references(self, obj, references):
        image_keys = {
            "image", "image_url", "imageurl", "local_path", "localpath",
            "image_src", "imagesrc", "thumbnail", "thumbnail_url",
            "thumbnailurl", "src"
        }
        if isinstance(obj, dict):
            for key, value in obj.items():
                key_lower = str(key).lower()
                if key_lower in image_keys:
                    if isinstance(value, str):
                        value = value.strip()
                        if value:
                            references.add(value)
                    else:
                        self._collect_image_references(value, references)
                elif isinstance(value, (dict, list)):
                    self._collect_image_references(value, references)
                elif key_lower == "url" and isinstance(value, str):
                    if any(str(k).lower() in image_keys for k in obj.keys()):
                        references.add(value.strip())
        elif isinstance(obj, list):
            for item in obj:
                self._collect_image_references(item, references)

    def _resolve_local_image_path(self, image_reference):
        if not isinstance(image_reference, str):
            return None
        reference = image_reference.strip()
        if not reference or reference.startswith(("http://", "https://", "data:")):
            return None
        normalized = reference.replace("\\", "/")
        relative = normalized.lstrip("/")
        candidates = [
            self.project_root / relative,
            self.project_root / "frontend" / "public" / relative,
            self.project_root / "frontend" / relative,
            Path(reference),
            Path(relative),
        ]
        for candidate in candidates:
            try:
                if candidate.exists() and candidate.is_file():
                    return candidate
            except Exception:
                pass
        return None

    def refresh_current_todards_images(self):
        """Load every image currently used by the frontend Todards JSON.

        The important point is that todards.json normally stores the remote
        image URL, not the local file created by ImageFetcher. Therefore we
        also download those remote images and build perceptual hashes from
        them. URL comparison alone is not enough when the same photograph is
        available from another URL/provider.
        """
        self.current_todards_image_urls = set()
        self.current_todards_image_hashes = set()
        self.current_todards_perceptual_hashes = set()

        if not self.todards_json_path.exists():
            print(f"Todards JSON not found: {self.todards_json_path.resolve()}")
            return

        try:
            with open(self.todards_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            references = set()
            self._collect_image_references(data, references)

            for reference in references:
                normalized_url = self.normalize_image_url(reference)

                if normalized_url.startswith(("http://", "https://")):
                    self.current_todards_image_urls.add(normalized_url)

                    # todards.json stores remote URLs. Download the existing
                    # image so duplicate detection is not limited to URL text.
                    try:
                        response = requests.get(
                            reference,
                            headers={"User-Agent": "Todards/1.0"},
                            timeout=15
                        )
                        response.raise_for_status()

                        content = response.content
                        image_hash = self.get_content_hash(content)
                        if image_hash:
                            self.current_todards_image_hashes.add(image_hash)

                        perceptual_hash = self.get_perceptual_hash(content)
                        if perceptual_hash is not None:
                            self.current_todards_perceptual_hashes.add(
                                perceptual_hash
                            )
                    except Exception as e:
                        print(
                            f"Could not download current Todards image "
                            f"{reference}: {e}"
                        )

                local_path = self._resolve_local_image_path(reference)
                if local_path is not None:
                    try:
                        content = local_path.read_bytes()

                        image_hash = self.get_content_hash(content)
                        if image_hash:
                            self.current_todards_image_hashes.add(image_hash)

                        perceptual_hash = self.get_perceptual_hash(content)
                        if perceptual_hash is not None:
                            self.current_todards_perceptual_hashes.add(
                                perceptual_hash
                            )
                    except Exception as e:
                        print(
                            f"Could not read current Todards image "
                            f"{local_path}: {e}"
                        )

            print(
                "Current Todards images loaded: "
                f"{len(self.current_todards_image_urls)} URLs, "
                f"{len(self.current_todards_image_hashes)} exact hashes, "
                f"{len(self.current_todards_perceptual_hashes)} perceptual hashes"
            )

        except Exception as e:
            print(f"Could not load current Todards JSON: {e}")


    def load_image_history(self):



        if not self.history_path.exists():



            return []



        try:



            with open(

                self.history_path,

                "r",

                encoding="utf-8"

            ) as f:



                history = json.load(f)



            if not isinstance(

                history,

                list

            ):



                return []



            return history



        except Exception as e:



            print(

                f"Could not load image history: {e}"

            )



            return []



    # ========================================================



    def save_image_history(self):



        try:



            with open(

                self.history_path,

                "w",

                encoding="utf-8"

            ) as f:



                json.dump(

                    self.image_history,

                    f,

                    ensure_ascii=False,

                    indent=4

                )



        except Exception as e:



            print(

                f"Could not save image history: {e}"

            )



    # ========================================================



    def cleanup_image_history(self):



        cutoff_date = (

            datetime.now().date()

            - timedelta(

                days=self.history_days

            )

        )



        cleaned_history = []



        for item in self.image_history:



            date_string = item.get(

                "date",

                ""

            )



            try:



                item_date = datetime.strptime(

                    date_string,

                    "%Y-%m-%d"

                ).date()



            except Exception:



                continue



            if item_date >= cutoff_date:



                cleaned_history.append(

                    item

                )



        self.image_history = (

            cleaned_history

        )



        self.save_image_history()



    # ========================================================



    def get_recent_used_urls(self):



        cutoff_date = (

            datetime.now().date()

            - timedelta(

                days=self.history_days

            )

        )



        used_urls = set()



        for item in self.image_history:



            date_string = item.get(

                "date",

                ""

            )



            image_url = item.get(

                "image_url",

                ""

            )



            if not date_string or not image_url:

                continue



            try:



                item_date = datetime.strptime(

                    date_string,

                    "%Y-%m-%d"

                ).date()



            except Exception:



                continue



            if item_date >= cutoff_date:



                used_urls.add(

                    image_url

                )



        return used_urls



    # ========================================================



    def register_used_image(self, image_url, article_id, image_content=None):
        if not image_url:
            return
        normalized_url = self.normalize_image_url(image_url)
        today = datetime.now().strftime("%Y-%m-%d")
        exists = any(
            item.get("date") == today
            and self.normalize_image_url(item.get("image_url", "")) == normalized_url
            and item.get("article_id") == article_id
            for item in self.image_history
        )
        if not exists:
            self.image_history.append({
                "date": today,
                "image_url": image_url,
                "article_id": article_id
            })
        self.current_run_urls.add(normalized_url)
        if image_content:
            image_hash = self.get_content_hash(image_content)
            if image_hash:
                self.current_run_hashes.add(image_hash)

            perceptual_hash = self.get_perceptual_hash(image_content)
            if perceptual_hash is not None:
                self.current_run_perceptual_hashes.add(perceptual_hash)


    def is_image_used_recently(self, image_url, image_content=None):
        if not image_url:
            return True
        normalized_url = self.normalize_image_url(image_url)
        if normalized_url in self.current_todards_image_urls:
            return True
        if image_content:
            image_hash = self.get_content_hash(image_content)
            if image_hash and (
                image_hash in self.current_todards_image_hashes
                or image_hash in self.current_run_hashes
            ):
                return True

            if self.is_perceptual_duplicate(image_content):
                return True

        if normalized_url in self.current_run_urls:
            return True
        recent_urls = self.get_recent_used_urls()
        return normalized_url in {
            self.normalize_image_url(url)
            for url in recent_urls
        }


    def save_image(

        self,

        image_data,

        image_id

    ):



        filename = (

            f"{image_id}.jpg"

        )



        output_file = (

            self.output_dir /

            filename

        )



        output_file.write_bytes(

            image_data["content"]

        )



        self.register_used_image(
            image_url=image_data["url"],
            article_id=image_id,
            image_content=image_data.get("content")
        )


        return {

            "image_id": image_id,

            "source": image_data["source"],

            "keyword": image_data["keyword"],

            "url": image_data["url"],

            "local_path": str(

                output_file

            )

        }



    # ========================================================

    # FALLBACK IMAGE

    # ========================================================



    def get_fallback_image(

        self,

        keyword

    ):

        print(
            "  → Searching fallback image..."
        )

        # Search several result pages. This prevents the fetcher from
        # returning no image just because page 1 contains duplicates.
        max_pages = 5

        # ----------------------------------------------------
        # PEXELS
        # ----------------------------------------------------
        try:
            for page in range(1, max_pages + 1):
                images = self.pexels.get_images(
                    keyword=keyword,
                    per_page=5,
                    page=page
                )

                if not images:
                    break

                for image in images:
                    if not self.is_image_used_recently(
                        image["url"],
                        image.get("content")
                    ):
                        return image

        except Exception as e:
            print(f"Pexels fallback failed: {e}")

        # ----------------------------------------------------
        # UNSPLASH
        # ----------------------------------------------------
        try:
            for page in range(1, max_pages + 1):
                images = self.unsplash.get_images(
                    keyword=keyword,
                    per_page=5,
                    page=page
                )

                if not images:
                    break

                for image in images:
                    if not self.is_image_used_recently(
                        image["url"],
                        image.get("content")
                    ):
                        return image

        except Exception as e:
            print(f"Unsplash fallback failed: {e}")

        return None


    def get_images(

        self,

        keywords,

        image_id,

        pexels_per_keyword=2,

        unsplash_per_keyword=2

    ):

        results = []

        # Always read the latest frontend data before selecting images.
        self.refresh_current_todards_images()
        self.cleanup_image_history()

        recent_used_urls = self.get_recent_used_urls()
        print(
            "\nRecently used images: "
            f"{len(recent_used_urls)}"
        )

        classifications = self.classifier.classify(keywords)

        print("\nClassifications:")
        for item in classifications:
            print(
                f"  {item['keyword']} "
                f"→ {item['type']}"
            )

        image_counter = 1

        def get_unique_pexels(keyword, target_count):
            """Search multiple Pexels pages until target_count unique images."""
            unique = []
            max_pages = 5
            per_page = max(target_count, 5)

            for page in range(1, max_pages + 1):
                try:
                    images = self.pexels.get_images(
                        keyword=keyword,
                        per_page=per_page,
                        page=page
                    )
                except Exception as e:
                    print(f"Pexels failed on page {page}: {e}")
                    break

                if not images:
                    break

                for image in images:
                    if self.is_image_used_recently(
                        image["url"],
                        image.get("content")
                    ):
                        print(
                            f"  → Pexels duplicate skipped "
                            f"(page {page})."
                        )
                        continue

                    unique.append(image)

                    if len(unique) >= target_count:
                        return unique

            return unique

        def get_unique_unsplash(keyword, target_count):
            """Search multiple Unsplash pages until target_count unique images."""
            unique = []
            max_pages = 5
            per_page = max(target_count, 5)

            for page in range(1, max_pages + 1):
                try:
                    images = self.unsplash.get_images(
                        keyword=keyword,
                        per_page=per_page,
                        page=page
                    )
                except Exception as e:
                    print(f"Unsplash failed on page {page}: {e}")
                    break

                if not images:
                    break

                for image in images:
                    if self.is_image_used_recently(
                        image["url"],
                        image.get("content")
                    ):
                        print(
                            f"  → Unsplash duplicate skipped "
                            f"(page {page})."
                        )
                        continue

                    unique.append(image)

                    if len(unique) >= target_count:
                        return unique

            return unique

        for item in classifications:

            keyword = item["keyword"]
            keyword_type = item["type"]

            print(f"\nProcessing: {keyword}")

            # =================================================
            # PERSON
            # =================================================
            if keyword_type == "PERSON":

                print("  → Wikipedia")
                wiki_image = self.wikipedia.get_image(
                    person_name=keyword
                )

                # If Wikipedia has no image OR its image is already used,
                # immediately search Pexels/Unsplash instead.
                if (
                    wiki_image
                    and not self.is_image_used_recently(
                        wiki_image["url"],
                        wiki_image.get("content")
                    )
                ):
                    current_id = f"{image_id}_{image_counter}"
                    result = self.save_image(
                        wiki_image,
                        current_id
                    )
                    results.append(result)
                    image_counter += 1

                else:
                    if wiki_image:
                        print(
                            "  → Wikipedia image already used. "
                            "Searching fallback."
                        )
                    else:
                        print("  → Wikipedia failed. Searching fallback.")

                    fallback = self.get_fallback_image(keyword)

                    if fallback:
                        current_id = f"{image_id}_{image_counter}"
                        result = self.save_image(
                            fallback,
                            current_id
                        )
                        results.append(result)
                        image_counter += 1
                    else:
                        print(
                            f"  No unused image found for {keyword}"
                        )

            # =================================================
            # OTHER
            # =================================================
            else:

                print("  → Pexels + Unsplash")

                # Search additional pages if page 1 contains duplicates.
                pexels_images = get_unique_pexels(
                    keyword,
                    pexels_per_keyword
                )

                for image in pexels_images:
                    current_id = f"{image_id}_{image_counter}"
                    result = self.save_image(
                        image,
                        current_id
                    )
                    results.append(result)
                    image_counter += 1

                unsplash_images = get_unique_unsplash(
                    keyword,
                    unsplash_per_keyword
                )

                for image in unsplash_images:
                    current_id = f"{image_id}_{image_counter}"
                    result = self.save_image(
                        image,
                        current_id
                    )
                    results.append(result)
                    image_counter += 1

        self.cleanup_image_history()
        self.save_image_history()

        print(
            f"\nImageFetcher finished: {len(results)} unique images."
        )

        return results

