import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timezone, timedelta


def get_section_links():

    url = "https://www.downtoearth.org.in/climate-change"
    domain = "https://www.downtoearth.org.in/"

    headers = {
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
        "Referer": url
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=10
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    links = []

    # Current UTC time
    now = datetime.now(timezone.utc)

    # Time 24 hours ago
    cutoff = now - timedelta(hours=24)

    # --------------------------------------------------------
    # FIND ALL HEADLINE LINKS
    # --------------------------------------------------------

    sections = soup.select(
        'a[aria-label="headline"][href]'
    )

    print(f"Found {len(sections)} headline links")

    # --------------------------------------------------------
    # PROCESS EACH HEADLINE
    # --------------------------------------------------------

    for section in sections:

        # ----------------------------------------------------
        # FIND THE STORY CARD
        # ----------------------------------------------------

        story_card = section.find_parent(
            "div",
            attrs={
                "data-test-id": "story-card"
            }
        )

        if not story_card:
            continue

        # ----------------------------------------------------
        # FIND PUBLISH TIME INSIDE SAME STORY CARD
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # PARSE DATETIME
        # ----------------------------------------------------

        try:

            published_time = datetime.fromisoformat(
                datetime_value.replace(
                    "Z",
                    "+00:00"
                )
            )

        except ValueError:

            print(
                f"Invalid datetime: {datetime_value}"
            )

            continue

        # ----------------------------------------------------
        # CHECK LAST 24 HOURS
        # ----------------------------------------------------

        if cutoff <= published_time <= now:

            link = section.get("href")

            if link:

                full_link = urljoin(
                    domain,
                    link
                )

                links.append(
                    full_link
                )

                print(
                    f"{published_time} -> {full_link}"
                )

    return links


def scrape_content(url_list):
    paragraphs = []
    for url in url_list:
        domain = "https://www.downtoearth.org.in/"

        headers = {
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
                "Referer": url
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        sections = soup.find("div", class_="arr--story-page-card-wrapper").find_all("p")
        
        text = ""
        for section in sections:
                para = section.get_text(strip=True)
                text += para + " "
        paragraphs.append(text)
    print(paragraphs)
    return paragraphs



if __name__ == "__main__":

        links = get_section_links()

        print("\nFINAL LINKS:")
        print(links)

        scrape_content(links)