
import requests
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timedelta
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


class BBCScraper:

    def __init__(self, url, domain, title_class):
        self.url = url
        self.domain = domain
        self.title_class = title_class

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
        }

    def get_section_links(self):
        response = requests.get(self.url, headers=self.headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        links = []
        sections = soup.find_all("a", href=True)

        for section in sections:
            if section.find(self.title_class):
                link = section.get("href")
                links.append(urljoin(self.domain, link))

        return links

    def scrape_content(self, links):
        articles = []

        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        for link in links:
            response = requests.get(link, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            date_modified = None

            scripts = soup.find_all("script", type="application/ld+json")

            for script in scripts:
                if not script.string:
                    continue

                if "dateModified" not in script.string:
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

                    value = item.get("dateModified")

                    if value:
                        try:
                            date_modified = datetime.fromisoformat(value.rstrip("Z"))
                            break
                        except ValueError:
                            continue

                if date_modified:
                    break

            if not date_modified:
                continue

            article_date = date_modified.date()

            if article_date not in (today, yesterday):
                continue

            headline = soup.find("h1")
            title = ""

            if headline:
                title = headline.get_text(" ", strip=True)

            paragraphs = soup.find_all("p")
            article_content = ""

            for content in paragraphs[:20]:
                text = content.get_text(" ", strip=True)

                if text:
                    article_content += text + "\n"

            if article_content.strip():
                articles.append({
                    "title": title,
                    "date": date_modified.strftime("%Y-%m-%d %H:%M"),
                    "content": article_content.strip(),
                    "url": link
                })

        articles.sort(key=lambda x: x["date"], reverse=True)

        return articles


class WHOScraper:

    def __init__(self, url, domain, title_class):
        self.url = url
        self.domain = domain
        self.title_class = title_class

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
        }

    def get_section_links(self):
        response = requests.get(
            self.url,
            headers=self.headers,
            timeout=10
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        sections = soup.find_all("a", href=True)

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
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        today_str = today.strftime("%d-%m-%Y")
        yesterday_str = yesterday.strftime("%d-%m-%Y")

        selected_content = []

        for link in links:
            if today_str in link or yesterday_str in link:
                selected_content.append(link)

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

            article_content = "\n".join(content)

            matched_text = re.search(
                r"^(.*?)Media Contacts WHO Media Team",
                article_content,
                re.DOTALL
            )

            if matched_text:
                article_content = matched_text.group(1).strip()

            if article_content:
                articles.append({
                    "title": title,
                    "date": datetime.now().strftime(
                        "%Y-%m-%d %H:%M"
                    ),
                    "content": article_content,
                    "url": link
                })

        return articles


class CNNScraper:

    def __init__(self, url, domain):
        self.url = url
        self.domain = domain

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://edition.cnn.com/"
        }

        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def get_section_links(self):
        response = self.session.get(self.url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        links = []

        today = datetime.now().strftime("%Y/%m/%d")

        sections = soup.find_all("a", href=True)

        for section in sections:
            href = section["href"]

            if today in href:
                full_url = urljoin(self.domain, href)

                if full_url not in links:
                    links.append(full_url)

        print("CNN Links are:", links)

        return links

    def scrape_content(self, links):
        articles = []

        for link in links:

            try:
                response = self.session.get(link, timeout=30)
                response.raise_for_status()

            except requests.RequestException as e:
                print(f"CNN failed: {link}")
                print(e)
                continue

            soup = BeautifulSoup(response.text, "html.parser")

            sections = soup.find_all(
                "p",
                class_=lambda value: value and "paragraph-elevate" in value
            )

            paragraph = ""

            for section in sections:
                text = section.get_text(" ", strip=True)

                if text:
                    paragraph += text + " "

            paragraph = re.sub(r"\s+", " ", paragraph).strip()

            if not paragraph:
                print(f"No CNN content found: {link}")
                continue

            published_date = ""

            script = soup.find(
                "script",
                string=lambda x: x and "published_date_formatted" in x
            )

            if script:
                match = re.search(
                    r'"published_date_formatted":"([^"]+)"',
                    script.string
                )

                if match:
                    published_date = match.group(1)

            articles.append({
                "date": published_date,
                "content": paragraph,
                "url": link
            })

        return articles



class GuardianScraper:

    def __init__(self, url, domain):
        self.url = url
        self.domain = domain

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.theguardian.com/global-development/global-health/"
        }

        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def get_section_links(self):
        response = self.session.get(self.url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        links = []

        today = datetime.now().strftime("%Y/%b/%d")

        sections = soup.find_all("a", href=True)

        for section in sections:
            href = section["href"]

            if today in href:
                full_url = urljoin(self.domain, href)

                if full_url not in links:
                    links.append(full_url)

        print("Guardian Links are:", links)

        return links

    def scrape_content(self, links):
        articles = []

        for link in links:

            try:
                response = self.session.get(link, timeout=30)
                response.raise_for_status()

            except requests.RequestException as e:
                print(f"Gurdian failed: {link}")
                print(e)
                continue

            soup = BeautifulSoup(response.text, "html.parser")

            sections = soup.find_all(
                "p",
                class_=lambda value: value and "dcr-1s160rg" in value
            )

            paragraph = ""

            for section in sections:
                text = section.get_text(" ", strip=True)

                if text:
                    paragraph += text + " "

            paragraph = re.sub(r"\s+", " ", paragraph).strip()

            if not paragraph:
                print(f"No Guardian content found: {link}")
                continue

            published_date = datetime.now().strftime("%b %d,%d")

            # script = soup.find(
            #     "script",
            #     string=lambda x: x and "Last modified on  :" in x
            # )

            # if script:
            #     match = re.search(
            #         r'"published_date_formatted":"([^"]+)"',
            #         script.string
            #     )

            #     if match:
            #         published_date = match.group(1)

            articles.append({
                "date": published_date,
                "content": paragraph,
                "url": link
            })

        return articles   


class HealthDataScrapper:

    def __init__(self):
        self.output_dir = "data/health_data"
        self.category = "health"

        os.makedirs(self.output_dir, exist_ok=True)

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

        BBCHealth_links = BBCHealth.get_section_links()
        BBC_data = BBCHealth.scrape_content(BBCHealth_links)

        for article in BBC_data:
            health_data.append({
                "id": f"{self.category}-{len(health_data) + 1}",
                "source": "British Broadcasting Company",
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

        WHOHealth_links = WHOHealth.get_section_links()
        todays_links = WHOHealth.check_todays_content(WHOHealth_links)
        WHO_data = WHOHealth.scrape_content(todays_links)

        for article in WHO_data:
            health_data.append({
                "id": f"{self.category}-{len(health_data) + 1}",
                "source": "World Health Organization",
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

        CNNHealth_links = CNNHealth.get_section_links()
        CNN_data = CNNHealth.scrape_content(CNNHealth_links)

        for article in CNN_data:
            health_data.append({
                "id": f"{self.category}-{len(health_data) + 1}",
                "source": "CNN",
                "category": self.category,
                "date": article["date"],
                "content": article["content"],
                "url": article["url"]
            })


        GuardianHealth = GuardianScraper(
            url="https://www.theguardian.com/global-development/global-health",
            domain="https://www.theguardian.com/global-development/"
        )

        Guardian_links = GuardianHealth.get_section_links()
        Guardian_data = GuardianHealth.scrape_content(Guardian_links)
        
        for article in Guardian_data:
            health_data.append({
                "id": f"{self.category}-{len(health_data) + 1}",
                "source": "Guardian",
                "category": self.category,
                "date": article["date"],
                "content": article["content"],
                "url": article["url"]
            })

        # =====================================
        # SAVE
        # =====================================

        file_name = datetime.now().strftime("%d%m%Y") + "_health_data.json"

        with open(os.path.join(self.output_dir, file_name), "w", encoding="utf-8") as f:
            json.dump(health_data, f, ensure_ascii=False, indent=4)

        print(f"\nSaved {len(health_data)} articles to {os.path.join(self.output_dir, file_name)}")


if __name__ == "__main__":
    scrapper = HealthDataScrapper()
    scrapper.scrape_health_data()
