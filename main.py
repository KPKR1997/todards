import json
import copy
from datetime import datetime

from backend.processing.process_pipeline import MainProcessPipeline
from webscrape.health_scrape import HealthDataScrapper
from webscrape.tech_scrapper import TechDataScrapper
from webscrape.politics import PoliticsDataScrapper
from backend.post_processing.deduplication import ArticleDuplicateRemover
from backend.post_processing.ranking.ranker import NewsRanker


if __name__ == "__main__":

    model = "llama3:latest"
    url = "http://localhost:11434"

    # ============================================================
    # 1. SCRAPE
    # ============================================================

    print("\n========== HEALTH SCRAPER ==========\n")

    health_scrapper = HealthDataScrapper()
    health_scrapper.scrape_health_data()

    health_filename = (
        datetime.now().strftime("%d%m%Y")
        + "_health_data.json"
    )

    health_data_path = (
        f"data/health_data/{health_filename}"
    )


    print("\n========== SCIENCE & TECHNOLOGY SCRAPER ==========\n")

    tech_scrapper = TechDataScrapper()
    tech_scrapper.scrape_tech_data()

    tech_filename = (
        datetime.now().strftime("%d%m%Y")
        + "_tech_data.json"
    )

    tech_data_path = (
        f"data/tech_data/{tech_filename}"
    )


    print("\n========== PEOPLE / POLITICS SCRAPER ==========\n")

    politics_scrapper = PoliticsDataScrapper()
    politics_scrapper.scrape_politics_data()

    politics_filename = (
        datetime.now().strftime("%d%m%Y")
        + "_people_data.json"
    )

    politics_data_path = (
        f"data/people_data/{politics_filename}"
    )


    # Deduplicate articles in the scraped data
    deduplicator = ArticleDuplicateRemover(
        data_root="data",
        similarity_threshold=0.8,
        model_name="all-MiniLM-L6-v2"
    )

    deduplicator.run()


    # Rank the processed articles

    print(
    "\n========== NEWS RANKING ==========\n"
    )

    ranker = NewsRanker(
        data_root="data",
        backup_root="data/backup",
        top_n=3,
        similarity_threshold=0.78,
        ollama_url=url,
        model=model,
    )

    ranked_articles = ranker.run()



    # ============================================================
    # 2. PROCESS
    # ============================================================

    processor = MainProcessPipeline(
        url,
        model
    )


    print("\n========== PROCESSING HEALTH ==========\n")

    health_output = processor.run_pipeline(
        health_data_path
    )


    print(
        "\n========== PROCESSING SCIENCE & TECHNOLOGY ==========\n"
    )

    tech_output = processor.run_pipeline(
        tech_data_path
    )


    print("\n========== PROCESSING PEOPLE / POLITICS ==========\n")

    politics_output = processor.run_pipeline(
        politics_data_path
    )


    # ============================================================
    # 3. COMBINE OUTPUT
    # ============================================================

    output = (
        health_output
        + tech_output
        + politics_output
    )


    # ============================================================
    # 4. LOAD TODARDS JSON
    # ============================================================

    output_path = (
        "frontend/public/data/todards.json"
    )

    with open(
        output_path,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)

    copy_data = copy.deepcopy(data)


    # ============================================================
    # 5. GROUP OUTPUT BY CATEGORY
    # ============================================================

    output_by_category = {}

    for card in output:

        category = (
            card["category"]
            .strip()
            .lower()
        )

        if category not in output_by_category:

            output_by_category[category] = []

        output_by_category[category].append(
            card
        )


    # ============================================================
    # 6. UPDATE FRONTEND CARDS
    # ============================================================

    for section in copy_data["sections"]:

        section_id = (
            section["id"]
            .strip()
            .lower()
        )

        if section_id not in output_by_category:
            continue

        new_cards = output_by_category[
            section_id
        ]

        existing_cards = section["cards"]


        for index, new_card in enumerate(
            new_cards
        ):

            if index >= len(existing_cards):
                break

            existing_card = existing_cards[
                index
            ]

            existing_card["title"] = (
                new_card["title"]
            )

            existing_card["image"] = (
                new_card["image"]
            )

            existing_card["place"] = (
                new_card["place"]
            )

            existing_card["time"] = (
                new_card["time"]
            )

            existing_card["content"] = (
                new_card["content"]
            )


    # ============================================================
    # 7. SAVE TODARDS JSON
    # ============================================================

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            copy_data,
            f,
            ensure_ascii=False,
            indent=2
        )


    print(
        f"\nUpdated Todards data saved to: "
        f"{output_path}"
    )