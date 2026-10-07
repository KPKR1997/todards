import os
import json
import re
import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timezone, timedelta


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