import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timezone, timedelta



def get_section_links():
    url = "https://www.unep.org/en/news-and-stories/press-release"
    domain = "https://www.unep.org/en/"
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
    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )
    urls = []

    # Current UTC time
    now = datetime.now(timezone.utc)
    # Time 24 hours ago
    cutoff = now - timedelta(hours=24)

    sections = soup.find_all(
        "div", class_ = "views-row"
    )

    print(f"Found {len(sections)} headline links")



    for section in sections:
        # Get publication time from the same views-row
        time_tag = section.find("time", class_="datetime")

        if not time_tag or not time_tag.get("datetime"):
            continue

        published_at = datetime.fromisoformat(
            time_tag["datetime"]
        )

        # Convert publication time to UTC
        published_at = published_at.astimezone(timezone.utc)

        # Keep articles published within the past 24 hours
        if cutoff <= published_at <= now:
            link_tag = section.find("a", href=True)

            if link_tag:
                link = urljoin(domain, link_tag["href"])
                urls.append(link)

    print(f"Found {len(urls)} links published in the past 24 hours")

    return urls


def scrape_content(url_list):
    paragraphs = []
    for url in url_list:
        domain = "https://www.unep.org/en/"
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
        # scrape_content(links)