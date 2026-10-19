import os
import json
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timezone, timedelta, date
 
# COMMON DATE HELPERS
 
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
 
# CNBC ENTERTAINMENT SCRAPER
 
class CNBCEntertainmentScraper:
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
                f"CNBC section failed: {e}"
            )
            return []
        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )
        links = []
        # CNBC URLs contain the publication date,
        # but the date in the URL alone cannot guarantee
        # the article is within the last 24 hours.
        sections = soup.find_all(
            "a",
            class_="Card-title"
        )
        for section in sections:
            href = section.get(
                "href"
            )
            if not href:
                continue
            full_url = urljoin(
                self.domain,
                href
            )
             
            # Check article's actual publication datetime
             
            try:
                article_response = (
                    self.session.get(
                        full_url,
                        timeout=30
                    )
                )
                article_response.raise_for_status()
            except requests.RequestException:
                continue
            article_soup = BeautifulSoup(
                article_response.text,
                "html.parser"
            )
            published_time = None
             
            # JSON-LD
             
            json_ld_scripts = (
                article_soup.find_all(
                    "script",
                    type="application/ld+json"
                )
            )
            for script in json_ld_scripts:
                try:
                    raw = script.string
                    if not raw:
                        continue
                    data = json.loads(raw)
                    objects = (
                        data
                        if isinstance(data, list)
                        else [data]
                    )
                    for obj in objects:
                        if not isinstance(
                            obj,
                            dict
                        ):
                            continue
                        date_value = (
                            obj.get(
                                "datePublished"
                            )
                        )
                        if date_value:
                            published_time = (
                                parse_datetime(
                                    date_value
                                )
                            )
                            if published_time:
                                break
                    if published_time:
                        break
                except Exception:
                    continue
             
            # Meta fallback
             
            if not published_time:
                meta = article_soup.find(
                    "meta",
                    attrs={
                        "property":
                        "article:published_time"
                    }
                )
                if meta:
                    published_time = (
                        parse_datetime(
                            meta.get(
                                "content",
                                ""
                            )
                        )
                    )
            if not is_within_last_24_hours(
                published_time
            ):
                continue
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
                    f"CNBC failed: {link}"
                )
                print(e)
                continue
            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )
             
            # Title
             
            headline = soup.find(
                "h1"
            )
            title = ""
            if headline:
                title = headline.get_text(
                    " ",
                    strip=True
                )
             
            # Content
             
            groups = soup.find_all(
                "div",
                class_="group"
            )
            content = " ".join(
                p.get_text(
                    " ",
                    strip=True
                )
                for group in groups
                for p in group.find_all(
                    "p"
                )
            )
            content = re.sub(
                r"\s+",
                " ",
                content
            ).strip()
            if not content:
                print(
                    f"No CNBC content found: {link}"
                )
                continue
             
            # Actual publication date
             
            published_date = ""
            json_ld_scripts = (
                soup.find_all(
                    "script",
                    type="application/ld+json"
                )
            )
            for script in json_ld_scripts:
                try:
                    raw = script.string
                    if not raw:
                        continue
                    data = json.loads(raw)
                    objects = (
                        data
                        if isinstance(data, list)
                        else [data]
                    )
                    found = False
                    for obj in objects:
                        if not isinstance(
                            obj,
                            dict
                        ):
                            continue
                        date_value = obj.get(
                            "datePublished"
                        )
                        if date_value:
                            published_date = (
                                date_value
                            )
                            found = True
                            break
                    if found:
                        break
                except Exception:
                    continue
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
 
# CNN ENTERTAINMENT SCRAPER
 
class CNNEntertainmentScraper:
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
                f"CNN section failed: {e}"
            )
            return []
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
            href = section.get(
                "href"
            )
            if not href:
                continue
            full_url = urljoin(
                self.domain,
                href
            )
             
            # CNN publication date must be checked from
            # article page.
             
            try:
                article_response = (
                    self.session.get(
                        full_url,
                        timeout=30
                    )
                )
                article_response.raise_for_status()
            except requests.RequestException:
                continue
            article_soup = BeautifulSoup(
                article_response.text,
                "html.parser"
            )
            published_time = None
             
            # CNN JSON data
             
            script = article_soup.find(
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
                    published_time = (
                        parse_datetime(
                            match.group(1)
                        )
                    )
             
            # JSON-LD fallback
             
            if not published_time:
                scripts = (
                    article_soup.find_all(
                        "script",
                        type="application/ld+json"
                    )
                )
                for script in scripts:
                    try:
                        if not script.string:
                            continue
                        data = json.loads(
                            script.string
                        )
                        objects = (
                            data
                            if isinstance(data, list)
                            else [data]
                        )
                        for obj in objects:
                            if not isinstance(
                                obj,
                                dict
                            ):
                                continue
                            date_value = (
                                obj.get(
                                    "datePublished"
                                )
                            )
                            if date_value:
                                published_time = (
                                    parse_datetime(
                                        date_value
                                    )
                                )
                                if published_time:
                                    break
                        if published_time:
                            break
                    except Exception:
                        continue
            if not is_within_last_24_hours(
                published_time
            ):
                continue
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
                    f"CNN failed: {link}"
                )
                print(e)
                continue
            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )
             
            # Title
             
            headline = soup.find(
                "h1"
            )
            title = ""
            if headline:
                title = headline.get_text(
                    " ",
                    strip=True
                )
             
            # Content
             
            sections = soup.find_all(
                "p",
                class_=lambda value:
                value and
                "paragraph-elevate" in value
            )
            content = " ".join(
                section.get_text(
                    " ",
                    strip=True
                )
                for section in sections
                if section.get_text(
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
             
            # Published date
             
            published_date = ""
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
                    published_date = (
                        match.group(1)
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
 
# BBC HEALTH SCRAPER
 
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
class BBCEntertainmentScraper:
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
            try:
                response = requests.get(
                    link,
                    headers=self.headers,
                    timeout=10
                )
                response.raise_for_status()
            except requests.RequestException as e:
                print(f"Request failed: {link}")
                print(e)
                continue
            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )
             
            # PUBLICATION DATETIME
             
            published_time = get_jsonld_datetime(
                soup,
                [
                    "datePublished",
                    "dateModified"
                ]
            )
            if not published_time:
                continue
            if not is_within_last_24_hours(published_time):
                continue
             
            # TITLE
             
            headline = soup.find("h1")
            title = ""
            if headline:
                title = headline.get_text(
                    " ",
                    strip=True
                )
             
            # CONTENT
             
            if "videos" in link.lower():
                # Video pages: use only the specified text container.
                content_container = soup.find(
                    "div",
                    class_=(
                        "VideoDetailsPage-styles__TextStyled-sc-85e5b49-3 "
                        "fsrCoa"
                    )
                )
                paragraphs = (
                    content_container.find_all("p")
                    if content_container
                    else []
                )
            elif "articles" in link.lower():
                # Article pages: use only paragraphs inside <article>.
                article_tag = soup.find("article")
                paragraphs = (
                    article_tag.find_all("p")
                    if article_tag
                    else []
                )
            else:
                # Preserve existing behavior for other URLs.
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
            else:
                print(f"No article content found: {link}")
         
        # SORT BY PUBLICATION DATE
         
        articles.sort(
            key=lambda x: x["date"],
            reverse=True
        )
        return articles


 
# ACADEMY AWARDS / OSCARS SCRAPER
 
class AcademyAwardsEntertainmentScraper:
    """Fetch Oscars press-release cards dated today or yesterday."""
    def __init__(self, url="https://press.oscars.org/tag/press-release", domain="https://press.oscars.org/"):
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
            "Referer": url,
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    @staticmethod
    def _parse_card_date(value):
        if not value:
            return None
        value = re.sub(r"\s+", " ", value).strip()
        for fmt in ("%A, %B %d, %Y", "%B %d, %Y", "%A, %b %d, %Y", "%b %d, %Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        return None
    def get_section_links(self):
        try:
            response = self.session.get(self.url, timeout=20)
            response.raise_for_status()
        except requests.RequestException as exc:
            print(f"Academy Awards section failed: {exc}")
            return []
        soup = BeautifulSoup(response.text, "html.parser")
        today = date.today()
        allowed_dates = {today, today - timedelta(days=1)}
        article_urls = []
        seen_urls = set()
        for card in soup.select("div.card-article"):
            date_element = card.select_one("div.card-article__date")
            if date_element is None:
                continue
            published_date = self._parse_card_date(
                date_element.get_text(" ", strip=True)
            )
            if published_date not in allowed_dates:
                continue
            link = card.select_one("a.card-article__link[href], a[href]")
            if link is None:
                continue
            article_url = urljoin(self.domain, link.get("href", "").strip())
            if not article_url.startswith(("http://", "https://")):
                continue
            if article_url not in seen_urls:
                seen_urls.add(article_url)
                article_urls.append(article_url)
        return article_urls
    def scrape_content(self, links):
        articles = []
        for link in links:
            try:
                response = self.session.get(link, timeout=20)
                response.raise_for_status()
            except requests.RequestException as exc:
                print(f"Academy Awards article failed: {link} ({exc})")
                continue
            soup = BeautifulSoup(response.text, "html.parser")
            headline = soup.find("h1")
            title = headline.get_text(" ", strip=True) if headline else ""
            body = soup.select_one("div.news__body")
            if body is None:
                # Fallback selectors in case the publisher changes its markup.
                body = soup.select_one("article")
            if body is None:
                print(f"No Academy Awards article body found: {link}")
                continue
            paragraphs = [
                paragraph.get_text(" ", strip=True)
                for paragraph in body.find_all("p")
            ]
            content = re.sub(r"\s+", " ", " ".join(p for p in paragraphs if p)).strip()
            if not content:
                print(f"No Academy Awards article text found: {link}")
                continue
            # Keep the publisher's displayed card date as the article date where
            # available; the URL list already guarantees today/yesterday.
            published_date = ""
            date_meta = soup.find("meta", attrs={"property": "article:published_time"})
            if date_meta and date_meta.get("content"):
                published_date = date_meta["content"].strip()
            if not published_date:
                published_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
            articles.append({
                "title": title,
                "date": published_date,
                "content": content,
                "url": link,
            })
        return articles
 
# MAIN NTERTAINMENT SCRAPER
 
class EntertainmentDataScrapper:
    def __init__(self):
        self.output_dir = (
            "data/entertainment_data"
        )
        self.category = (
            "entertainment"
        )
        os.makedirs(
            self.output_dir,
            exist_ok=True
        )
    # ========================================================
    # MAIN SCRAPE
    # ========================================================
    def scrape_entertainment_data(self):
        entertainment_data = []
        # ====================================================
        # CNBC
        # ====================================================
        # print(
        #     "\n========== CNBC ==========\n"
        # )
        # CNBCEntertainment = CNBCEntertainmentScraper(
        #     url=(
        #         "https://www.cnbc.com/media/"
        #     ),
        #     domain=(
        #         "https://www.cnbc.com"
        #     )
        # )
        # CNBC_links = (
        #     CNBCEntertainment.get_section_links()
        # )
        # print(
        #     f"CNBC links found: ",
        #     f"{len(CNBC_links)}",
        #     CNBC_links
        # )
        # CNBC_data = (
        #     CNBCEntertainment.scrape_content(
        #         CNBC_links
        #     )
        # )
        # for article in CNBC_data:
        #     entertainment_data.append({
        #         "id": (
        #             f"st-{len(entertainment_data) + 1}"
        #         ),
        #         "source": "CNBC",
        #         "category": self.category,
        #         "title": article["title"],
        #         "date": article["date"],
        #         "content": article["content"],
        #         "url": article["url"]
        #     })
        # ====================================================
        # CNN
        # ====================================================
        CNNEntertainment = CNNEntertainmentScraper(
            url="https://edition.cnn.com/entertainment",
            domain="https://edition.cnn.com"
        )
        CNN_links = (
            CNNEntertainment.get_section_links()
        )
        print(
            f"CNN links found: "
            f"{len(CNN_links)}"
        )
        CNN_data = (
            CNNEntertainment.scrape_content(
                CNN_links
            )
        )
        for article in CNN_data:
            entertainment_data.append({
                "id":
                f"st-{len(entertainment_data) + 1}",
                "source": "CNN",
                "category": self.category,
                "title": article["title"],
                "date": article["date"],
                "content": article["content"],
                "url": article["url"]
            })

        # ====================================================
        # CNN
        # ====================================================
        CNNEntertainment = CNNEntertainmentScraper(
            url="https://edition.cnn.com/sport",
            domain="https://edition.cnn.com"
        )
        CNN_links = (
            CNNEntertainment.get_section_links()
        )
        print(
            f"CNN links found: "
            f"{len(CNN_links)}"
        )
        CNN_data = (
            CNNEntertainment.scrape_content(
                CNN_links
            )
        )
        for article in CNN_data:
            entertainment_data.append({
                "id":
                f"st-{len(entertainment_data) + 1}",
                "source": "CNN",
                "category": self.category,
                "title": article["title"],
                "date": article["date"],
                "content": article["content"],
                "url": article["url"]
            })
        #BBC Scrapper
        BBCEntertainment = BBCEntertainmentScraper(
                    url="https://www.bbc.com/culture/entertainment-news",
                    domain="https://www.bbc.com",
                    title_class="h2"
                )
        BBCEntertainment_links = (
            BBCEntertainment.get_section_links()
        )
        print(BBCEntertainment_links)
        BBC_data = (
            BBCEntertainment.scrape_content(
                BBCEntertainment_links
            )
        )
        print(BBC_data)
        for article in BBC_data:
            entertainment_data.append({
                "id": (
                    f"{self.category}-"
                    f"{len(entertainment_data) + 1}"
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
        #BBC Music Scrapper
        BBCEntertainment = BBCEntertainmentScraper(
                    url="https://www.bbc.com/culture/music",
                    domain="https://www.bbc.com",
                    title_class="h2"
                )
        BBCEntertainment_links = (
            BBCEntertainment.get_section_links()
        )
        print(BBCEntertainment_links)
        BBC_data = (
            BBCEntertainment.scrape_content(
                BBCEntertainment_links
            )
        )
        print(BBC_data)
        for article in BBC_data:
            entertainment_data.append({
                "id": (
                    f"{self.category}-"
                    f"{len(entertainment_data) + 1}"
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
        #BBC Film & TV Scrapper
        BBCEntertainment = BBCEntertainmentScraper(
                    url="https://www.bbc.com/culture/film-tv",
                    domain="https://www.bbc.com",
                    title_class="h2"
                )
        BBCEntertainment_links = (
            BBCEntertainment.get_section_links()
        )
        print(BBCEntertainment_links)
        BBC_data = (
            BBCEntertainment.scrape_content(
                BBCEntertainment_links
            )
        )
        print(BBC_data)
        for article in BBC_data:
            entertainment_data.append({
                "id": (
                    f"{self.category}-"
                    f"{len(entertainment_data) + 1}"
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
        # ====================================================
        # ACADEMY AWARDS / OSCARS PRESS RELEASES
        # ====================================================
        try:
            AcademyAwards = AcademyAwardsEntertainmentScraper(
                url="https://press.oscars.org/tag/press-release",
                domain="https://press.oscars.org/",
            )
            AcademyAwards_links = AcademyAwards.get_section_links()
            print(f"Academy Awards links found: {len(AcademyAwards_links)}")
            AcademyAwards_data = AcademyAwards.scrape_content(AcademyAwards_links)
            for article in AcademyAwards_data:
                entertainment_data.append({
                    "id": f"{self.category}-{len(entertainment_data) + 1}",
                    "source": "Academy Awards",
                    "category": self.category,
                    "title": article["title"],
                    "date": article["date"],
                    "content": article["content"],
                    "url": article["url"],
                })
        except Exception as exc:
            # A failure in this additional source must not prevent other
            # entertainment sources from being saved.
            print(f"Academy Awards scraper failed: {exc}")
        # ====================================================
        # SAVE JSON
        # ====================================================
        file_name = (
            datetime.now().strftime(
                "%d%m%Y"
            )
            + "_entertainment_data.json"
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
                entertainment_data,
                f,
                ensure_ascii=False,
                indent=4
            )
        print(
            f"\nSaved "
            f"{len(entertainment_data)} "
            f"articles to:"
        )
        print(
            output_path
        )
        return entertainment_data
 
# RUN
 
if __name__ == "__main__":
    scrapper = EntertainmentDataScrapper()
    scrapper.scrape_entertainment_data()