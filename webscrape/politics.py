import os
import json
import re
import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timezone, timedelta


# ============================================================
# DATETIME HELPERS
# ============================================================

def get_24_hour_window():
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)

    return now, cutoff


def parse_datetime(value):
    """
    Convert a datetime string into timezone-aware UTC datetime.
    """

    if not value:
        return None

    value = value.strip()

    # ISO datetime
    try:
        value = value.replace("Z", "+00:00")

        parsed = datetime.fromisoformat(value)

        if parsed.tzinfo is None:
            parsed = parsed.replace(
                tzinfo=timezone.utc
            )

        return parsed.astimezone(timezone.utc)

    except ValueError:
        pass

    # Common datetime formats
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%b %d, %Y",
        "%B %d, %Y",
    ]

    for fmt in formats:

        try:

            parsed = datetime.strptime(
                value,
                fmt
            )

            return parsed.replace(
                tzinfo=timezone.utc
            )

        except ValueError:
            continue

    return None


def is_within_last_24_hours(published_time):

    if not published_time:
        return False

    now, cutoff = get_24_hour_window()

    return cutoff <= published_time <= now


def get_jsonld_datetime(soup, keys):
    """
    Extract datePublished/dateModified from JSON-LD.
    """

    scripts = soup.find_all(
        "script",
        type="application/ld+json"
    )

    for script in scripts:

        if not script.string:
            continue

        try:
            data = json.loads(
                script.string
            )

        except json.JSONDecodeError:
            continue

        if isinstance(data, list):
            data_list = data

        else:
            data_list = [data]

        for item in data_list:

            if not isinstance(item, dict):
                continue

            # Sometimes JSON-LD contains @graph
            graph = item.get("@graph")

            if isinstance(graph, list):
                candidates = graph

            else:
                candidates = [item]

            for candidate in candidates:

                if not isinstance(candidate, dict):
                    continue

                for key in keys:

                    value = candidate.get(key)

                    if value:

                        parsed = parse_datetime(
                            value
                        )

                        if parsed:
                            return parsed

    return None


def get_html_datetime(soup):

    time_tag = soup.find(
        "time",
        attrs={
            "datetime": True
        }
    )

    if time_tag:

        return parse_datetime(
            time_tag.get(
                "datetime",
                ""
            )
        )

    return None


# ============================================================
# BBC POLITICS SCRAPER
# ============================================================

class BBCPoliticsScraper:

    def __init__(self, url, domain):

        self.url = url
        self.domain = domain

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/153.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,image/avif,"
                "image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": self.url
        }

        self.session = requests.Session()

        self.session.headers.update(
            self.headers
        )

    def get_section_links(self):

        try:

            response = self.session.get(
                self.url,
                timeout=30
            )

            response.raise_for_status()

        except requests.RequestException as e:

            print(
                f"BBC section failed: {e}"
            )

            return []

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        links = []

        # BBC article links
        articles = soup.find_all(
            "a",
            href=True
        )

        for article in articles:

            href = article.get(
                "href"
            )

            if not href:
                continue

            # Keep BBC news article URLs
            if not href.startswith(
                "/news/"
            ):
                continue

            full_url = urljoin(
                self.domain,
                href
            )

            if full_url not in links:

                links.append(
                    full_url
                )

        return links

    def scrape_content(self, links):

        articles = []

        for link in links:

            try:

                response = self.session.get(
                    link,
                    timeout=30
                )

                response.raise_for_status()

            except requests.RequestException as e:

                print(
                    f"BBC failed: {link}"
                )

                print(e)

                continue

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            # ------------------------------------------------
            # DATETIME
            # ------------------------------------------------

            published_time = get_jsonld_datetime(
                soup,
                [
                    "datePublished",
                    "dateModified"
                ]
            )

            if not published_time:

                published_time = get_html_datetime(
                    soup
                )

            if not published_time:

                continue

            if not is_within_last_24_hours(
                published_time
            ):

                continue

            # ------------------------------------------------
            # TITLE
            # ------------------------------------------------

            headline = soup.find(
                "h1"
            )

            title = ""

            if headline:

                title = headline.get_text(
                    " ",
                    strip=True
                )

            # ------------------------------------------------
            # CONTENT
            # ------------------------------------------------

            paragraphs = soup.find_all(
                "p"
            )

            content = " ".join(
                p.get_text(
                    " ",
                    strip=True
                )
                for p in paragraphs
                if p.get_text(
                    " ",
                    strip=True
                )
            )

            content = re.sub(
                r"\s+",
                " ",
                content
            ).strip()

            if not content:

                print(
                    f"No BBC content found: {link}"
                )

                continue

            articles.append({

                "title": title,

                "date": published_time.strftime(
                    "%Y-%m-%d %H:%M"
                ),

                "content": content,

                "url": link

            })

        return articles


# ============================================================
# CNN POLITICS SCRAPER
# ============================================================

class CNNPoliticsScraper:

    def __init__(self, url, domain):

        self.url = url
        self.domain = domain

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/153.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,image/avif,"
                "image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": self.url
        }

        self.session = requests.Session()

        self.session.headers.update(
            self.headers
        )

    def get_section_links(self):

        try:

            response = self.session.get(
                self.url,
                timeout=30
            )

            response.raise_for_status()

        except requests.RequestException as e:

            print(
                f"CNN section failed: {e}"
            )

            return []

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        links = []

        articles = soup.find_all(
            "a",
            href=True
        )

        for article in articles:

            href = article.get(
                "href"
            )

            if not href:
                continue

            # CNN politics URLs
            if "/politics/" not in href:
                continue

            full_url = urljoin(
                self.domain,
                href
            )

            if full_url not in links:

                links.append(
                    full_url
                )

        return links

    def scrape_content(self, links):

        articles = []

        for link in links:

            try:

                response = self.session.get(
                    link,
                    timeout=30
                )

                response.raise_for_status()

            except requests.RequestException as e:

                print(
                    f"CNN failed: {link}"
                )

                print(e)

                continue

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            # ------------------------------------------------
            # DATETIME
            # ------------------------------------------------

            published_time = get_jsonld_datetime(
                soup,
                [
                    "datePublished",
                    "dateModified"
                ]
            )

            # CNN-specific fallback
            if not published_time:

                script = soup.find(
                    "script",
                    string=lambda x:
                    x and
                    "published_date_formatted" in x
                )

                if script and script.string:

                    match = re.search(
                        r'"published_date_formatted":"([^"]+)"',
                        script.string
                    )

                    if match:

                        published_time = parse_datetime(
                            match.group(1)
                        )

            if not published_time:

                published_time = get_html_datetime(
                    soup
                )

            if not published_time:

                continue

            if not is_within_last_24_hours(
                published_time
            ):

                continue

            # ------------------------------------------------
            # TITLE
            # ------------------------------------------------

            headline = soup.find(
                "h1"
            )

            title = ""

            if headline:

                title = headline.get_text(
                    " ",
                    strip=True
                )

            # ------------------------------------------------
            # CONTENT
            # ------------------------------------------------

            paragraphs = soup.find_all(
                "p",
                class_=lambda value:
                value and
                "paragraph-elevate" in value
            )

            content = " ".join(
                p.get_text(
                    " ",
                    strip=True
                )
                for p in paragraphs
                if p.get_text(
                    " ",
                    strip=True
                )
            )

            content = re.sub(
                r"\s+",
                " ",
                content
            ).strip()

            if not content:

                print(
                    f"No CNN content found: {link}"
                )

                continue

            articles.append({

                "title": title,

                "date": published_time.strftime(
                    "%Y-%m-%d %H:%M"
                ),

                "content": content,

                "url": link

            })

        return articles


# ============================================================
# THE GUARDIAN POLITICS SCRAPER
# ============================================================

class GuardianPoliticsScraper:

    def __init__(self, url, domain):

        self.url = url
        self.domain = domain

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/153.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,image/avif,"
                "image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": self.url
        }

        self.session = requests.Session()

        self.session.headers.update(
            self.headers
        )

    def get_section_links(self):

        try:

            response = self.session.get(
                self.url,
                timeout=30
            )

            response.raise_for_status()

        except requests.RequestException as e:

            print(
                f"Guardian section failed: {e}"
            )

            return []

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        links = []

        # Guardian article links
        articles = soup.find_all(
            "a",
            href=True
        )

        for article in articles:

            href = article.get(
                "href"
            )

            if not href:
                continue

            # Guardian politics URLs
            if "/politics/" not in href:
                continue

            full_url = urljoin(
                self.domain,
                href
            )

            if full_url not in links:

                links.append(
                    full_url
                )

        return links

    def scrape_content(self, links):

        articles = []

        for link in links:

            try:

                response = self.session.get(
                    link,
                    timeout=30
                )

                response.raise_for_status()

            except requests.RequestException as e:

                print(
                    f"Guardian failed: {link}"
                )

                print(e)

                continue

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            # ------------------------------------------------
            # DATETIME
            # ------------------------------------------------

            published_time = get_jsonld_datetime(
                soup,
                [
                    "datePublished",
                    "dateModified"
                ]
            )

            if not published_time:

                published_time = get_html_datetime(
                    soup
                )

            # Guardian meta fallback
            if not published_time:

                meta_tag = soup.find(
                    "meta",
                    attrs={
                        "property":
                        "article:published_time"
                    }
                )

                if meta_tag:

                    published_time = parse_datetime(
                        meta_tag.get(
                            "content",
                            ""
                        )
                    )

            if not published_time:

                continue

            if not is_within_last_24_hours(
                published_time
            ):

                continue

            # ------------------------------------------------
            # TITLE
            # ------------------------------------------------

            headline = soup.find(
                "h1"
            )

            title = ""

            if headline:

                title = headline.get_text(
                    " ",
                    strip=True
                )

            # ------------------------------------------------
            # CONTENT
            # ------------------------------------------------

            article_body = soup.find(
                "div",
                {
                    "id": "maincontent"
                }
            )

            if not article_body:

                article_body = soup

            paragraphs = article_body.find_all(
                "p"
            )

            content = " ".join(
                p.get_text(
                    " ",
                    strip=True
                )
                for p in paragraphs
                if p.get_text(
                    " ",
                    strip=True
                )
            )

            content = re.sub(
                r"\s+",
                " ",
                content
            ).strip()

            if not content:

                print(
                    f"No Guardian content found: {link}"
                )

                continue

            articles.append({

                "title": title,

                "date": published_time.strftime(
                    "%Y-%m-%d %H:%M"
                ),

                "content": content,

                "url": link

            })

        return articles


# ============================================================
# MAIN PEOPLE SCRAPER
# ============================================================

class PoliticsDataScrapper:

    def __init__(self):

        self.output_dir = (
            "data/people_data"
        )

        self.category = "people"

        os.makedirs(
            self.output_dir,
            exist_ok=True
        )

    def scrape_politics_data(self):

        people_data = []

        # ====================================================
        # BBC
        # ====================================================

        BBC = BBCPoliticsScraper(
            url="https://www.bbc.com/news",
            domain="https://www.bbc.com"
        )

        BBC_links = (
            BBC.get_section_links()
        )

        print(
            f"BBC links found: "
            f"{len(BBC_links)}"
        )

        BBC_data = BBC.scrape_content(
            BBC_links
        )

        for article in BBC_data:

            people_data.append({

                "id": (
                    f"pp-"
                    f"{len(people_data) + 1}"
                ),

                "source": "BBC",

                "category": self.category,

                "title": article["title"],

                "date": article["date"],

                "content": article["content"],

                "url": article["url"]

            })

        # ====================================================
        # CNN
        # ====================================================

        CNN = CNNPoliticsScraper(
            url="https://edition.cnn.com/",
            domain="https://edition.cnn.com"
        )

        CNN_links = (
            CNN.get_section_links()
        )

        print(
            f"CNN links found: "
            f"{len(CNN_links)}"
        )

        CNN_data = CNN.scrape_content(
            CNN_links
        )

        for article in CNN_data:

            people_data.append({

                "id": (
                    f"pp-"
                    f"{len(people_data) + 1}"
                ),

                "source": "CNN",

                "category": self.category,

                "title": article["title"],

                "date": article["date"],

                "content": article["content"],

                "url": article["url"]

            })

        # ====================================================
        # THE GUARDIAN
        # ====================================================

        Guardian = GuardianPoliticsScraper(
            url=(
                "https://www.theguardian.com/"
                "international"
            ),
            domain=(
                "https://www.theguardian.com"
            )
        )

        Guardian_links = (
            Guardian.get_section_links()
        )

        print(
            f"Guardian links found: "
            f"{len(Guardian_links)}"
        )

        Guardian_data = (
            Guardian.scrape_content(
                Guardian_links
            )
        )

        for article in Guardian_data:

            people_data.append({

                "id": (
                    f"pp-"
                    f"{len(people_data) + 1}"
                ),

                "source": "The Guardian",

                "category": self.category,

                "title": article["title"],

                "date": article["date"],

                "content": article["content"],

                "url": article["url"]

            })

        # ====================================================
        # SAVE JSON
        # ====================================================

        file_name = (
            datetime.now().strftime("%d%m%Y")
            + "_people_data.json"
        )

        output_path = os.path.join(
            self.output_dir,
            file_name
        )

        with open(
            output_path,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                people_data,
                f,
                ensure_ascii=False,
                indent=4
            )

        print(
            f"\nSaved "
            f"{len(people_data)} "
            f"articles to:"
        )

        print(
            output_path
        )

        return people_data


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    scrapper = PoliticsDataScrapper()

    scrapper.scrape_politics_data()