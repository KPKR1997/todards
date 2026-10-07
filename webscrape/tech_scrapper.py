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
# CNBC TECHNOLOGY SCRAPER
# ============================================================

class CNBCTechScraper:

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


            # ------------------------------------------------
            # Check article's actual publication datetime
            # ------------------------------------------------

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


            # ------------------------------------------------
            # JSON-LD
            # ------------------------------------------------

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


            # ------------------------------------------------
            # Meta fallback
            # ------------------------------------------------

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


            # ------------------------------------------------
            # Title
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
            # Content
            # ------------------------------------------------

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


            # ------------------------------------------------
            # Actual publication date
            # ------------------------------------------------

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


# ============================================================
# NASA TECHNOLOGY SCRAPER
# ============================================================

class NASATechScraper:

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
                f"NASA section failed: {e}"
            )

            return []


        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )


        links = []


        sections = soup.find_all(
            "a",
            class_="hds-content-item-heading"
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


            # ------------------------------------------------
            # NASA listing does not reliably expose the
            # publication datetime, so check article page.
            # ------------------------------------------------

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


            # ------------------------------------------------
            # JSON-LD
            # ------------------------------------------------

            scripts = (
                article_soup.find_all(
                    "script",
                    type="application/ld+json"
                )
            )


            for script in scripts:

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

                        date_value = obj.get(
                            "datePublished"
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


            # ------------------------------------------------
            # Meta fallback
            # ------------------------------------------------

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
                    f"NASA failed: {link}"
                )

                print(e)

                continue


            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )


            # ------------------------------------------------
            # Title
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
            # Content
            # ------------------------------------------------

            paragraphs = soup.find_all(
                "p",
                class_="wp-block-paragraph"
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


            content = re.sub(
                r"\s+",
                " ",
                content
            ).strip()


            if not content:

                print(
                    f"No NASA content found: {link}"
                )

                continue


            # ------------------------------------------------
            # Published date
            # ------------------------------------------------

            published_date = ""


            script = soup.find(
                "script",
                type="application/ld+json"
            )


            if script and script.string:

                try:

                    data = json.loads(
                        script.string
                    )

                    objects = (
                        data
                        if isinstance(data, list)
                        else [data]
                    )

                    for obj in objects:

                        if isinstance(
                            obj,
                            dict
                        ):

                            if obj.get(
                                "datePublished"
                            ):

                                published_date = (
                                    obj[
                                        "datePublished"
                                    ]
                                )

                                break

                except Exception:
                    pass


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
# CNN TECHNOLOGY SCRAPER
# ============================================================

class CNNTechScraper:

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


            # ------------------------------------------------
            # CNN publication date must be checked from
            # article page.
            # ------------------------------------------------

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


            # ------------------------------------------------
            # CNN JSON data
            # ------------------------------------------------

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


            # ------------------------------------------------
            # JSON-LD fallback
            # ------------------------------------------------

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


            # ------------------------------------------------
            # Title
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
            # Content
            # ------------------------------------------------

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


            # ------------------------------------------------
            # Published date
            # ------------------------------------------------

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


# ============================================================
# BBC HEALTH SCRAPER
# ============================================================

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

class BBCTechScraper:

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
# MAIN SCIENCE AND TECHNOLOGY SCRAPER
# ============================================================

class TechDataScrapper:

    def __init__(self):

        self.output_dir = (
            "data/tech_data"
        )

        self.category = (
            "science and technology"
        )

        os.makedirs(
            self.output_dir,
            exist_ok=True
        )


    # ========================================================
    # MAIN SCRAPE
    # ========================================================

    def scrape_tech_data(self):

        tech_data = []


        # ====================================================
        # CNBC
        # ====================================================

        print(
            "\n========== CNBC ==========\n"
        )


        CNBCTech = CNBCTechScraper(

            url=(
                "https://www.cnbc.com/technology/"
            ),

            domain=(
                "https://www.cnbc.com"
            )
        )


        CNBC_links = (
            CNBCTech.get_section_links()
        )


        print(
            f"CNBC links found: "
            f"{len(CNBC_links)}"
        )


        CNBC_data = (
            CNBCTech.scrape_content(
                CNBC_links
            )
        )


        for article in CNBC_data:

            tech_data.append({

                "id": (
                    f"st-{len(tech_data) + 1}"
                ),

                "source": "CNBC",

                "category": self.category,

                "title": article["title"],

                "date": article["date"],

                "content": article["content"],

                "url": article["url"]

            })


        # ====================================================
        # NASA
        # ====================================================

        print(
            "\n========== NASA ==========\n"
        )


        NASATech = NASATechScraper(

            url=(
                "https://www.nasa.gov/news-release/"
            ),

            domain=(
                "https://www.nasa.gov"
            )
        )


        NASA_links = (
            NASATech.get_section_links()
        )


        print(
            f"NASA links found: "
            f"{len(NASA_links)}"
        )


        NASA_data = (
            NASATech.scrape_content(
                NASA_links
            )
        )


        for article in NASA_data:

            tech_data.append({

                "id": (
                    f"st-{len(tech_data) + 1}"
                ),

                "source": "NASA",

                "category": self.category,

                "title": article["title"],

                "date": article["date"],

                "content": article["content"],

                "url": article["url"]

            })


        # ====================================================
        # SCI TECH DAILY
        # ====================================================

        print(
            "\n========== SCI TECH DAILY ==========\n"
        )


        SciTech = SciTechDailyScraper(

            url=(
                "https://scitechdaily.com/news/science/"
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

            tech_data.append({

                "id": (
                    f"st-{len(tech_data) + 1}"
                ),

                "source": "SciTechDaily",

                "category": self.category,

                "title": article["title"],

                "date": article["date"],

                "content": article["content"],

                "url": article["url"]

            })


        SciTech = SciTechDailyScraper(

            url=(
                "https://scitechdaily.com/news/technology/"
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

            tech_data.append({

                "id": (
                    f"st-{len(tech_data) + 1}"
                ),

                "source": "SciTechDaily",

                "category": self.category,

                "title": article["title"],

                "date": article["date"],

                "content": article["content"],

                "url": article["url"]

            })
            


        # ====================================================
        # CNN
        # ====================================================

        CNNTech = CNNTechScraper(
        
            url="https://edition.cnn.com/science",
        
            domain="https://edition.cnn.com"
        )
        
        
        CNN_links = (
            CNNTech.get_section_links()
        )
        
        
        print(
            f"CNN links found: "
            f"{len(CNN_links)}"
        )
        
        
        CNN_data = (
            CNNTech.scrape_content(
                CNN_links
            )
        )
        
        
        for article in CNN_data:
        
            tech_data.append({
        
                "id":
                f"st-{len(tech_data) + 1}",
        
                "source": "CNN",
        
                "category": self.category,
        
                "title": article["title"],
        
                "date": article["date"],
        
                "content": article["content"],
        
                "url": article["url"]
        
            })



        BBCHealth = BBCTechScraper(
                    url="https://www.bbc.com/technology",
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

            tech_data.append({
                "id": (
                    f"{self.category}-"
                    f"{len(tech_data) + 1}"
                ),
                "source": (
                    "British Broadcasting Company"
                ),
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
            datetime.now().strftime(
                "%d%m%Y"
            )
            + "_tech_data.json"
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
                tech_data,
                f,
                ensure_ascii=False,
                indent=4
            )


        print(
            f"\nSaved "
            f"{len(tech_data)} "
            f"articles to:"
        )

        print(
            output_path
        )


        return tech_data


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    scrapper = TechDataScrapper()

    scrapper.scrape_tech_data()