import requests
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timedelta, timezone
import json
import re


def combine_data(main_list, source, content, category):
    serial_number = len(main_list) + 1

    main_list.append({
        "id": f"{category.lower()}-{serial_number}",
        "source": source,
        "category": category,
        "content": content
    })

    return main_list


# ============================================================
# DATETIME HELPERS
# ============================================================

def get_24_hour_window():
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)

    return now, cutoff


def parse_datetime(value):
    """
    Convert different datetime formats into timezone-aware UTC datetime.
    """

    if not value:
        return None

    value = value.strip()

    try:
        # Handle trailing Z
        value = value.replace("Z", "+00:00")

        parsed = datetime.fromisoformat(value)

        # If website does not provide timezone,
        # treat it as UTC rather than comparing naive/aware datetimes.
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed.astimezone(timezone.utc)

    except ValueError:
        pass

    # Additional common formats
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
            parsed = datetime.strptime(value, fmt)
            return parsed.replace(tzinfo=timezone.utc)

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
    Find publication/modification datetime from JSON-LD.
    """

    scripts = soup.find_all(
        "script",
        type="application/ld+json"
    )

    for script in scripts:

        if not script.string:
            continue

        try:
            data = json.loads(script.string)

        except json.JSONDecodeError:
            continue

        if isinstance(data, list):
            data_list = data
        else:
            data_list = [data]

        for item in data_list:

            if not isinstance(item, dict):
                continue

            for key in keys:

                value = item.get(key)

                if value:
                    parsed = parse_datetime(value)

                    if parsed:
                        return parsed

    return None


# ============================================================
# BBC HEALTH SCRAPER
# ============================================================

class BBCScraper:

    def __init__(self, url, domain, title_class):

        self.url = url
        self.domain = domain
        self.title_class = title_class

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/153.0.0.0 Safari/537.36"
            )
        }

    def get_section_links(self):

        response = requests.get(
            self.url,
            headers=self.headers,
            timeout=10
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        links = []

        sections = soup.find_all(
            "a",
            href=True
        )

        for section in sections:

            if section.find(self.title_class):

                link = section.get("href")

                links.append(
                    urljoin(
                        self.domain,
                        link
                    )
                )

        return links

    def scrape_content(self, links):

        articles = []

        for link in links:

            response = requests.get(
                link,
                headers=self.headers,
                timeout=10
            )

            response.raise_for_status()

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            # ------------------------------------------------
            # PUBLICATION DATETIME
            # ------------------------------------------------

            published_time = get_jsonld_datetime(
                soup,
                [
                    "datePublished",
                    "dateModified"
                ]
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

            headline = soup.find("h1")

            title = ""

            if headline:

                title = headline.get_text(
                    " ",
                    strip=True
                )

            # ------------------------------------------------
            # CONTENT
            # ------------------------------------------------

            paragraphs = soup.find_all("p")

            article_content = ""

            for content in paragraphs[:20]:

                text = content.get_text(
                    " ",
                    strip=True
                )

                if text:
                    article_content += text + "\n"

            if article_content.strip():

                articles.append({
                    "title": title,
                    "date": published_time.strftime(
                        "%Y-%m-%d %H:%M"
                    ),
                    "content": article_content.strip(),
                    "url": link
                })

        articles.sort(
            key=lambda x: x["date"],
            reverse=True
        )

        return articles


# ============================================================
# WHO HEALTH SCRAPER
# ============================================================

class WHOScraper:

    def __init__(self, url, domain, title_class):

        self.url = url
        self.domain = domain
        self.title_class = title_class

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/153.0.0.0 Safari/537.36"
            )
        }

    def get_section_links(self):

        response = requests.get(
            self.url,
            headers=self.headers,
            timeout=10
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        sections = soup.find_all(
            "a",
            href=True
        )

        links = [
            urljoin(
                self.domain,
                section.get("href")
            )
            for section in sections
            if section.find(self.title_class)
        ]

        return list(dict.fromkeys(links))

    def check_todays_content(self, links):

        selected_content = []

        for link in links:

            try:

                response = requests.get(
                    link,
                    headers=self.headers,
                    timeout=10
                )

                response.raise_for_status()

                soup = BeautifulSoup(
                    response.text,
                    "html.parser"
                )

                # ------------------------------------------------
                # PUBLICATION DATETIME
                # ------------------------------------------------

                published_time = get_jsonld_datetime(
                    soup,
                    [
                        "datePublished",
                        "dateModified"
                    ]
                )

                # Fallback to common HTML datetime fields
                if not published_time:

                    time_tag = soup.find(
                        "time",
                        attrs={
                            "datetime": True
                        }
                    )

                    if time_tag:

                        published_time = parse_datetime(
                            time_tag.get(
                                "datetime",
                                ""
                            )
                        )

                if not published_time:
                    continue

                if not is_within_last_24_hours(
                    published_time
                ):
                    continue

                selected_content.append(
                    link
                )

            except requests.RequestException as e:

                print(
                    f"WHO datetime check failed: {link}"
                )

                print(e)

                continue

        return selected_content

    def scrape_content(self, links):

        articles = []

        for link in links:

            response = requests.get(
                link,
                headers=self.headers,
                timeout=10
            )

            response.raise_for_status()

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            headline = soup.find("h1")

            title = ""

            if headline:

                title = headline.get_text(
                    " ",
                    strip=True
                )

            paragraphs = soup.find_all("p")

            content = []

            for paragraph in paragraphs:

                text = paragraph.get_text(
                    " ",
                    strip=True
                )

                if text:
                    content.append(text)

            article_content = "\n".join(
                content
            )

            matched_text = re.search(
                r"^(.*?)Media Contacts WHO Media Team",
                article_content,
                re.DOTALL
            )

            if matched_text:

                article_content = (
                    matched_text.group(1).strip()
                )

            # ------------------------------------------------
            # PUBLICATION DATETIME
            # ------------------------------------------------

            published_time = get_jsonld_datetime(
                soup,
                [
                    "datePublished",
                    "dateModified"
                ]
            )

            if not published_time:

                time_tag = soup.find(
                    "time",
                    attrs={
                        "datetime": True
                    }
                )

                if time_tag:

                    published_time = parse_datetime(
                        time_tag.get(
                            "datetime",
                            ""
                        )
                    )

            if not published_time:
                continue

            if not is_within_last_24_hours(
                published_time
            ):
                continue

            if article_content:

                articles.append({
                    "title": title,
                    "date": published_time.strftime(
                        "%Y-%m-%d %H:%M"
                    ),
                    "content": article_content,
                    "url": link
                })

        return articles


# ============================================================
# CNN HEALTH SCRAPER
# ============================================================

class CNNScraper:

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
            "Referer": "https://edition.cnn.com/"
        }

        self.session = requests.Session()

        self.session.headers.update(
            self.headers
        )

    def get_section_links(self):

        response = self.session.get(
            self.url,
            timeout=30
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        links = []

        sections = soup.find_all(
            "a",
            href=True
        )

        for section in sections:

            href = section["href"]

            # ------------------------------------------------
            # Keep original URL selection logic.
            # It is only used to find candidate articles.
            # Exact 24-hour filtering happens on article page.
            # ------------------------------------------------

            full_url = urljoin(
                self.domain,
                href
            )

            if full_url not in links:

                links.append(
                    full_url
                )

        print(
            "CNN Links are:",
            links
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
            # PUBLICATION DATETIME
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
                    string=lambda x: (
                        x and
                        "published_date_formatted" in x
                    )
                )

                if script:

                    match = re.search(
                        r'"published_date_formatted":"([^"]+)"',
                        script.string
                    )

                    if match:

                        published_time = parse_datetime(
                            match.group(1)
                        )

            if not published_time:
                continue

            if not is_within_last_24_hours(
                published_time
            ):
                continue

            # ------------------------------------------------
            # CONTENT
            # ------------------------------------------------

            sections = soup.find_all(
                "p",
                class_=lambda value: (
                    value and
                    "paragraph-elevate" in value
                )
            )

            paragraph = ""

            for section in sections:

                text = section.get_text(
                    " ",
                    strip=True
                )

                if text:
                    paragraph += text + " "

            paragraph = re.sub(
                r"\s+",
                " ",
                paragraph
            ).strip()

            if not paragraph:

                print(
                    f"No CNN content found: {link}"
                )

                continue

            # ------------------------------------------------
            # TITLE
            # ------------------------------------------------

            headline = soup.find("h1")

            title = ""

            if headline:

                title = headline.get_text(
                    " ",
                    strip=True
                )

            articles.append({
                "title": title,
                "date": published_time.strftime(
                    "%Y-%m-%d %H:%M"
                ),
                "content": paragraph,
                "url": link
            })

        return articles


# ============================================================
# GUARDIAN HEALTH SCRAPER
# ============================================================

class GuardianScraper:

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
            "Referer": (
                "https://www.theguardian.com/"
                "global-development/global-health/"
            )
        }

        self.session = requests.Session()

        self.session.headers.update(
            self.headers
        )

    def get_section_links(self):

        response = self.session.get(
            self.url,
            timeout=30
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        links = []

        sections = soup.find_all(
            "a",
            href=True
        )

        for section in sections:

            href = section["href"]

            full_url = urljoin(
                self.domain,
                href
            )

            if full_url not in links:

                links.append(
                    full_url
                )

        print(
            "Guardian Links are:",
            links
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
                    f"Gurdian failed: {link}"
                )

                print(e)

                continue

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            # ------------------------------------------------
            # PUBLICATION DATETIME
            # ------------------------------------------------

            published_time = get_jsonld_datetime(
                soup,
                [
                    "datePublished",
                    "dateModified"
                ]
            )

            # Guardian HTML fallback
            if not published_time:

                time_tag = soup.find(
                    "time",
                    attrs={
                        "datetime": True
                    }
                )

                if time_tag:

                    published_time = parse_datetime(
                        time_tag.get(
                            "datetime",
                            ""
                        )
                    )

            # Meta tag fallback
            if not published_time:

                meta_tag = soup.find(
                    "meta",
                    attrs={
                        "property": "article:published_time"
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
            # CONTENT
            # ------------------------------------------------

            sections = soup.find_all(
                "p",
                class_=lambda value: (
                    value and
                    "dcr-1s160rg" in value
                )
            )

            paragraph = ""

            for section in sections:

                text = section.get_text(
                    " ",
                    strip=True
                )

                if text:

                    paragraph += (
                        text + " "
                    )

            paragraph = re.sub(
                r"\s+",
                " ",
                paragraph
            ).strip()

            if not paragraph:

                print(
                    f"No Guardian content found: {link}"
                )

                continue

            # ------------------------------------------------
            # TITLE
            # ------------------------------------------------

            headline = soup.find("h1")

            title = ""

            if headline:

                title = headline.get_text(
                    " ",
                    strip=True
                )

            articles.append({
                "title": title,
                "date": published_time.strftime(
                    "%Y-%m-%d %H:%M"
                ),
                "content": paragraph,
                "url": link
            })

        return articles


# ============================================================
# MAIN HEALTH SCRAPER
# ============================================================

class HealthDataScrapper:

    def __init__(self):

        self.output_dir = (
            "data/health_data"
        )

        self.category = "health"

        os.makedirs(
            self.output_dir,
            exist_ok=True
        )

    def scrape_health_data(self):

        health_data = []

        # =====================================
        # BBC
        # =====================================

        BBCHealth = BBCScraper(
            url="https://www.bbc.com/news/health",
            domain="https://www.bbc.com",
            title_class="h2"
        )

        BBCHealth_links = (
            BBCHealth.get_section_links()
        )

        BBC_data = (
            BBCHealth.scrape_content(
                BBCHealth_links
            )
        )

        for article in BBC_data:

            health_data.append({
                "id": (
                    f"{self.category}-"
                    f"{len(health_data) + 1}"
                ),
                "source": 
                    "BBC"
                ,
                "category": self.category,
                "title": article["title"],
                "date": article["date"],
                "content": article["content"],
                "url": article["url"]
            })

        # =====================================
        # WHO
        # =====================================

        WHOHealth = WHOScraper(
            url="https://www.who.int/news-room",
            domain="https://www.who.int",
            title_class="p"
        )

        WHOHealth_links = (
            WHOHealth.get_section_links()
        )

        todays_links = (
            WHOHealth.check_todays_content(
                WHOHealth_links
            )
        )

        WHO_data = (
            WHOHealth.scrape_content(
                todays_links
            )
        )

        for article in WHO_data:

            health_data.append({
                "id": (
                    f"{self.category}-"
                    f"{len(health_data) + 1}"
                ),
                "source": 
                    "World Health Organization"
                ,
                "category": self.category,
                "title": article["title"],
                "date": article["date"],
                "content": article["content"],
                "url": article["url"]
            })

        # =====================================
        # CNN
        # =====================================

        CNNHealth = CNNScraper(
            url="https://edition.cnn.com/health",
            domain="https://edition.cnn.com"
        )

        CNNHealth_links = (
            CNNHealth.get_section_links()
        )

        CNN_data = (
            CNNHealth.scrape_content(
                CNNHealth_links
            )
        )

        for article in CNN_data:

            health_data.append({
                "id": (
                    f"{self.category}-"
                    f"{len(health_data) + 1}"
                ),
                "source": "CNN",
                "category": self.category,
                "title": article["title"],
                "date": article["date"],
                "content": article["content"],
                "url": article["url"]
            })

        # =====================================
        # GUARDIAN
        # =====================================

        GuardianHealth = GuardianScraper(
            url=(
                "https://www.theguardian.com/"
                "global-development/global-health"
            ),
            domain=(
                "https://www.theguardian.com/"
                "global-development/"
            )
        )

        Guardian_links = (
            GuardianHealth.get_section_links()
        )

        Guardian_data = (
            GuardianHealth.scrape_content(
                Guardian_links
            )
        )

        for article in Guardian_data:

            health_data.append({
                "id": (
                    f"{self.category}-"
                    f"{len(health_data) + 1}"
                ),
                "source": "Guardian",
                "category": self.category,
                "title": article["title"],
                "date": article["date"],
                "content": article["content"],
                "url": article["url"]
            })

        # =====================================
        # SAVE
        # =====================================

        file_name = (
            datetime.now().strftime("%d%m%Y")
            + "_health_data.json"
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
                health_data,
                f,
                ensure_ascii=False,
                indent=4
            )

        print(
            f"\nSaved "
            f"{len(health_data)} "
            f"articles to "
            f"{output_path}"
        )

        return health_data


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    scrapper = HealthDataScrapper()

    scrapper.scrape_health_data()