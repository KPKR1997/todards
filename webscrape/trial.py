import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timezone, timedelta, date



def get_section_links():
    url = "https://press.oscars.org/tag/press-release"
    domain = "https://press.oscars.org/"
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
    article_urls = []
    seen_urls = set()

    today = date.today()
    allowed_dates = {today, today - timedelta(days=3)}

    for card in soup.select("div.card-article"):
        date_element = card.select_one("div.card-article__date")
        if not date_element:
            continue

        date_text = date_element.get_text(" ", strip=True)

        parsed_date = None
        for fmt in ("%A, %B %d, %Y", "%B %d, %Y"):
            try:
                parsed_date = datetime.strptime(date_text, fmt).date()
                break
            except ValueError:
                continue

        if parsed_date not in allowed_dates:
            continue

        link = card.select_one("a.card-article__link[href], a[href]")
        if not link:
            continue

        article_url = urljoin(domain, link["href"])

        if article_url not in seen_urls:
            seen_urls.add(article_url)
            article_urls.append(article_url)

    return article_urls

    



def scrape_content(url_list):
    paragraphs = []
    for url in url_list:
        domain = "https://press.oscars.org/"
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
        sections = soup.find("div", class_="news__body").find("p")
        text = ""
        for section in sections:
                para = section.get_text(strip=True)
                text += para + " "
        paragraphs.append(text)
    print(paragraphs)
    return paragraphs

