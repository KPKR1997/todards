import os
import json
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timezone, timedelta

# ============================================================
# COMMON DATE HELPERS
# ============================================================
def get_24_hour_window():
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)
    return now, cutoff
def parse_datetime(value):
    if not value:
        return None
    value = value.strip()
    try:
        # ISO format
        parsed = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except ValueError:
        # Common fallback formats
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M",
            "%B %d, %Y %H:%M",
            "%b %d, %Y %H:%M",
        ]
        parsed = None
        for fmt in formats:
            try:
                parsed = datetime.strptime(
                    value,
                    fmt
                )
                break
            except ValueError:
                continue
        if parsed is None:
            return None
    # If datetime has no timezone,
    # treat it as UTC.
    if parsed.tzinfo is None:
        parsed = parsed.replace(
            tzinfo=timezone.utc
        )
    return parsed
def is_within_last_24_hours(published_time):
    if published_time is None:
        return False
    now, cutoff = get_24_hour_window()
    return (
        cutoff
        <= published_time
        <= now
    )
# ============================================================
# DOWN TO EARTH ENVIRONMENT SCRAPER
# ============================================================
class DownToEarthEnvironmentScraper:
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
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": self.url
        }
        self.session = requests.Session()
        self.session.headers.update(
            self.headers
        )
    # ========================================================
    # GET ARTICLE LINKS
    # ========================================================
    def get_section_links(self):
        try:
            response = self.session.get(
                self.url,
                timeout=30
            )
            response.raise_for_status()
        except requests.RequestException as e:
            print(
                f"Down To Earth section failed: {e}"
            )
            return []
        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )
        links = []
        # ----------------------------------------------------
        # Current UTC time
        # ----------------------------------------------------
        now = datetime.now(
            timezone.utc
        )
        cutoff = (
            now -
            timedelta(hours=24)
        )
        # ----------------------------------------------------
        # Find all headline links
        # ----------------------------------------------------
        sections = soup.select(
            'a[aria-label="headline"][href]'
        )
        print(
            f"Down To Earth headline links found: "
            f"{len(sections)}"
        )
        # ----------------------------------------------------
        # Process every headline
        # ----------------------------------------------------
        for section in sections:
            # ------------------------------------------------
            # Find parent story card
            # ------------------------------------------------
            story_card = section.find_parent(
                "div",
                attrs={
                    "data-test-id": "story-card"
                }
            )
            if not story_card:
                continue
            # ------------------------------------------------
            # Find publication time
            # ------------------------------------------------
            time_tag = story_card.find(
                "time",
                attrs={
                    "datetime": True
                }
            )
            if not time_tag:
                continue
            datetime_value = time_tag.get(
                "datetime",
                ""
            )
            # ------------------------------------------------
            # Parse datetime
            # ------------------------------------------------
            try:
                published_time = (
                    datetime.fromisoformat(
                        datetime_value.replace(
                            "Z",
                            "+00:00"
                        )
                    )
                )
            except ValueError:
                print(
                    f"Invalid Down To Earth datetime: "
                    f"{datetime_value}"
                )
                continue
            # ------------------------------------------------
            # Last 24 hours
            # ------------------------------------------------
            if not (
                cutoff
                <= published_time
                <= now
            ):
                continue
            # ------------------------------------------------
            # Get article URL
            # ------------------------------------------------
            href = section.get(
                "href"
            )
            if not href:
                continue
            full_url = urljoin(
                self.domain,
                href
            )
            # ------------------------------------------------
            # Avoid duplicates
            # ------------------------------------------------
            if full_url not in links:
                links.append(
                    full_url
                )
                print(
                    f"{published_time} -> "
                    f"{full_url}"
                )
        return links
    # ========================================================
    # SCRAPE ARTICLE CONTENT
    # ========================================================
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
                    f"Down To Earth failed: {link}"
                )
                print(e)
                continue
            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )
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
            # ARTICLE CONTENT
            # ------------------------------------------------
            article_container = soup.find(
                "div",
                class_="arr--story-page-card-wrapper"
            )
            if not article_container:
                print(
                    f"No Down To Earth article "
                    f"container found: {link}"
                )
                continue
            paragraphs = article_container.find_all(
                "p"
            )
            content = " ".join(
                paragraph.get_text(
                    " ",
                    strip=True
                )
                for paragraph in paragraphs
                if paragraph.get_text(
                    " ",
                    strip=True
                )
            )
            # ------------------------------------------------
            # Clean whitespace
            # ------------------------------------------------
            content = re.sub(
                r"\s+",
                " ",
                content
            ).strip()
            if not content:
                print(
                    f"No Down To Earth content found: "
                    f"{link}"
                )
                continue
            # ------------------------------------------------
            # Published date
            # ------------------------------------------------
            published_date = ""
            time_tag = soup.find(
                "time",
                attrs={
                    "datetime": True
                }
            )
            if time_tag:
                published_date = time_tag.get(
                    "datetime",
                    ""
                )
            if not published_date:
                published_date = datetime.now().strftime(
                    "%Y-%m-%d %H:%M"
                )
            # ------------------------------------------------
            # Save article
            # ------------------------------------------------
            articles.append({
                "title": title,
                "date": published_date,
                "content": content,
                "url": link
            })
        return articles


# ============================================================
# SCI TECH DAILY SCRAPER
# ============================================================
class SciTechDailyScraper:
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
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": self.url
        }
        self.session = requests.Session()
        self.session.headers.update(
            self.headers
        )
    # ========================================================
    # GET ARTICLE LINKS
    # ========================================================
    def get_section_links(self):
        try:
            response = self.session.get(
                self.url,
                timeout=30
            )
            response.raise_for_status()
        except requests.RequestException as e:
            print(
                f"SciTechDaily section failed: {e}"
            )
            return []
        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )
        links = []
        # ----------------------------------------------------
        # Current UTC time
        # ----------------------------------------------------
        now = datetime.now(
            timezone.utc
        )
        cutoff = (
            now -
            timedelta(hours=24)
        )
        content_divs = soup.find_all(
            "div",
            class_="content"
        )
        for div in content_divs:
            time_tag = div.find(
                "time",
                class_="post-date"
            )
            if not time_tag:
                continue
            datetime_value = time_tag.get(
                "datetime",
                ""
            )
            published_time = parse_datetime(
                datetime_value
            )
            if not is_within_last_24_hours(
                published_time
            ):
                continue
            a_tag = div.select_one(
                "h2.post-title a[href]"
            )
            if not a_tag:
                continue
            href = a_tag.get(
                "href"
            )
            if not href:
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
    # ========================================================
    # SCRAPE CONTENT
    # ========================================================
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
                    f"SciTechDaily failed: {link}"
                )
                print(e)
                continue
            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )
            article = soup.find(
                "article"
            )
            if not article:
                print(
                    f"No article element found: {link}"
                )
                continue
            # ------------------------------------------------
            # Title
            # ------------------------------------------------
            headline = article.find(
                "h1"
            )
            title = ""
            if headline:
                title = headline.get_text(
                    " ",
                    strip=True
                )
            # ------------------------------------------------
            # Content
            # ------------------------------------------------
            content = " ".join(
                p.get_text(
                    " ",
                    strip=True
                )
                for p in article.find_all(
                    "p"
                )
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
                    f"No SciTechDaily content found: {link}"
                )
                continue
            # ------------------------------------------------
            # Published date
            # ------------------------------------------------
            published_date = ""
            time_tag = article.find(
                "time",
                datetime=True
            )
            if time_tag:
                published_date = (
                    time_tag.get(
                        "datetime",
                        ""
                    )
                )
            if not published_date:
                published_date = (
                    datetime.now(
                        timezone.utc
                    ).strftime(
                        "%Y-%m-%d %H:%M"
                    )
                )
            articles.append({
                "title": title,
                "date": published_date,
                "content": content,
                "url": link
            })
        return articles
# ============================================================
# MAIN ENVIRONMENT SCRAPER
# ============================================================
class EnvironmentDataScrapper:
    def __init__(self):
        self.output_dir = (
            "data/environment_data"
        )
        self.category = "environment"
        os.makedirs(
            self.output_dir,
            exist_ok=True
        )
    # ========================================================
    # MAIN SCRAPE
    # ========================================================
    def scrape_environment_data(self):
        environment_data = []
        # ====================================================
        # DOWN TO EARTH
        # ====================================================
        print(
            "\n========== DOWN TO EARTH ==========\n"
        )
        down_to_earth = (
            DownToEarthEnvironmentScraper(
                url=(
                    "https://www.downtoearth.org.in/"
                    "climate-change"
                ),
                domain=(
                    "https://www.downtoearth.org.in"
                )
            )
        )
        down_to_earth_links = (
            down_to_earth.get_section_links()
        )
        print(
            f"Down To Earth links found: "
            f"{len(down_to_earth_links)}"
        )
        down_to_earth_data = (
            down_to_earth.scrape_content(
                down_to_earth_links
            )
        )
        for article in down_to_earth_data:
            environment_data.append({
                "id": (
                    f"env-{len(environment_data) + 1}"
                ),
                "source": "Down To Earth",
                "category": self.category,
                "title": article["title"],
                "date": article["date"],
                "content": article["content"],
                "url": article["url"]
            })

        #SciTech daily space section
                
        SciTech = SciTechDailyScraper(
            url=(
                "https://scitechdaily.com/news/earth/"
            ),
            domain=(
                "https://scitechdaily.com"
            )
        )
        SciTech_links = (
            SciTech.get_section_links()
        )
        print(
            f"SciTechDaily links found: "
            f"{len(SciTech_links)}"
        )
        SciTech_data = (
            SciTech.scrape_content(
                SciTech_links
            )
        )
        for article in SciTech_data:
            environment_data.append({
                "id": (
                    f"st-{len(environment_data) + 1}"
                ),
                "source": "SciTechDaily",
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
            + "_environment_data.json"
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
                environment_data,
                f,
                ensure_ascii=False,
                indent=4
            )
        print(
            f"\nSaved "
            f"{len(environment_data)} "
            f"articles to:"
        )
        print(
            output_path
        )
        return environment_data
# ============================================================
# RUN
# ============================================================
if __name__ == "__main__":
    scrapper = EnvironmentDataScrapper()
    scrapper.scrape_environment_data()