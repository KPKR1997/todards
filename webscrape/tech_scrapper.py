import os
import json
import re
import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime


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
        self.session.headers.update(self.headers)


    def get_section_links(self):

        try:
            response = self.session.get(
                self.url,
                timeout=30
            )
            response.raise_for_status()

        except requests.RequestException as e:
            print(f"CNBC section failed: {e}")
            return []

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        today = datetime.now().strftime("%Y/%m/%d")

        links = []

        sections = soup.find_all(
            "a",
            class_="Card-title"
        )

        for section in sections:

            href = section.get("href")

            if not href:
                continue

            if today not in href:
                continue

            full_url = urljoin(
                self.domain,
                href
            )

            if full_url not in links:
                links.append(full_url)

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
                print(f"CNBC failed: {link}")
                print(e)
                continue

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            # Title
            headline = soup.find("h1")

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
                for p in group.find_all("p")
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

            articles.append({
                "title": title,
                "date": datetime.now().strftime(
                    "%Y-%m-%d %H:%M"
                ),
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
        self.session.headers.update(self.headers)


    def get_section_links(self):

        try:
            response = self.session.get(
                self.url,
                timeout=30
            )
            response.raise_for_status()

        except requests.RequestException as e:
            print(f"NASA section failed: {e}")
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

            href = section.get("href")

            if not href:
                continue

            full_url = urljoin(
                self.domain,
                href
            )

            if full_url not in links:
                links.append(full_url)

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
                print(f"NASA failed: {link}")
                print(e)
                continue

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            # Title
            headline = soup.find("h1")

            title = ""

            if headline:
                title = headline.get_text(
                    " ",
                    strip=True
                )

            # Content
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

            articles.append({
                "title": title,
                "date": datetime.now().strftime(
                    "%Y-%m-%d %H:%M"
                ),
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
        self.session.headers.update(self.headers)


    def get_section_links(self):

        try:
            response = self.session.get(
                self.url,
                timeout=30
            )
            response.raise_for_status()

        except requests.RequestException as e:
            print(f"SciTechDaily section failed: {e}")
            return []

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        today = datetime.now().strftime(
            "%Y-%m-%d"
        )

        links = []

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

            if not datetime_value.startswith(today):
                continue

            a_tag = div.select_one(
                "h2.post-title a[href]"
            )

            if not a_tag:
                continue

            href = a_tag.get("href")

            if not href:
                continue

            full_url = urljoin(
                self.domain,
                href
            )

            if full_url not in links:
                links.append(full_url)

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
                print(f"SciTechDaily failed: {link}")
                print(e)
                continue

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            article = soup.find("article")

            if not article:
                print(
                    f"No article element found: {link}"
                )
                continue

            # Title
            headline = article.find("h1")

            title = ""

            if headline:
                title = headline.get_text(
                    " ",
                    strip=True
                )

            # Content
            content = " ".join(
                p.get_text(
                    " ",
                    strip=True
                )
                for p in article.find_all("p")
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

            articles.append({
                "title": title,
                "date": datetime.now().strftime(
                    "%Y-%m-%d %H:%M"
                ),
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
        self.session.headers.update(self.headers)


    def get_section_links(self):

        try:
            response = self.session.get(
                self.url,
                timeout=30
            )
            response.raise_for_status()

        except requests.RequestException as e:
            print(f"CNN section failed: {e}")
            return []

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        today = datetime.now().strftime(
            "%Y/%m/%d"
        )

        links = []

        sections = soup.find_all(
            "a",
            href=True
        )

        for section in sections:

            href = section.get("href")

            if not href:
                continue

            if today not in href:
                continue

            full_url = urljoin(
                self.domain,
                href
            )

            if full_url not in links:
                links.append(full_url)

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
                print(f"CNN failed: {link}")
                print(e)
                continue

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            # Title
            headline = soup.find("h1")

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
                    published_date = match.group(1)

            if not published_date:
                published_date = datetime.now().strftime(
                    "%Y-%m-%d %H:%M"
                )

            articles.append({
                "title": title,
                "date": published_date,
                "content": content,
                "url": link
            })

        return articles


# ============================================================
# MAIN SCIENCE AND TECHNOLOGY SCRAPER
# ============================================================

class TechDataScrapper:

    def __init__(self):

        self.output_dir = "data/tech_data"

        # Changed from "technology"
        self.category = "science and technology"

        os.makedirs(
            self.output_dir,
            exist_ok=True
        )


    def scrape_tech_data(self):

        tech_data = []

        # ====================================================
        # CNBC
        # ====================================================

        CNBCTech = CNBCTechScraper(
            url="https://www.cnbc.com/technology/",
            domain="https://www.cnbc.com"
        )

        CNBC_links = CNBCTech.get_section_links()

        print(
            f"CNBC links found: {len(CNBC_links)}"
        )

        CNBC_data = CNBCTech.scrape_content(
            CNBC_links
        )

        for article in CNBC_data:

            tech_data.append({
                "id": f"st-{len(tech_data) + 1}",
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

        NASATech = NASATechScraper(
            url="https://www.nasa.gov/news-release/",
            domain="https://www.nasa.gov"
        )

        NASA_links = NASATech.get_section_links()

        print(
            f"NASA links found: {len(NASA_links)}"
        )

        NASA_data = NASATech.scrape_content(
            NASA_links
        )

        for article in NASA_data:

            tech_data.append({
                "id": f"st-{len(tech_data) + 1}",
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

        SciTech = SciTechDailyScraper(
            url="https://scitechdaily.com/",
            domain="https://scitechdaily.com"
        )

        SciTech_links = SciTech.get_section_links()

        print(
            f"SciTechDaily links found: {len(SciTech_links)}"
        )

        SciTech_data = SciTech.scrape_content(
            SciTech_links
        )

        for article in SciTech_data:

            tech_data.append({
                "id": f"st-{len(tech_data) + 1}",
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
            url="https://edition.cnn.com/technology",
            domain="https://edition.cnn.com"
        )

        CNN_links = CNNTech.get_section_links()

        print(
            f"CNN links found: {len(CNN_links)}"
        )

        CNN_data = CNNTech.scrape_content(
            CNN_links
        )

        for article in CNN_data:

            tech_data.append({
                "id": f"st-{len(tech_data) + 1}",
                "source": "CNN",
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
            f"\nSaved {len(tech_data)} articles to:"
        )
        print(output_path)

        return tech_data


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    scrapper = TechDataScrapper()

    scrapper.scrape_tech_data()