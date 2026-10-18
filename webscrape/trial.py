import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timezone, timedelta, date



from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def get_section_links(url, domain):
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    cutoff = datetime.now() - timedelta(hours=24)
    links = []

    for article in soup.find_all("article", class_="post"):
        time_tag = article.find("div", class_="totalView")
        time_tag = time_tag.find("p") if time_tag else None

        if not time_tag:
            continue

        try:
            published = datetime.strptime(
                time_tag.get_text(strip=True),
                "%B %d, %Y %I:%M %p"
            )
        except ValueError:
            continue

        if published >= cutoff:
            link = article.find("a", href=True)
            if link:
                full_url = urljoin(domain, link["href"])
                if full_url not in links:
                    links.append(full_url)

    return links

    
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

if __name__ == "__main__":
    print(get_section_links("https://newsonair.gov.in/category/sports/", "https://newsonair.gov.in/"))