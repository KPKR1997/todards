import os
import json
from datetime import datetime


from backend.processing.llm_summarize import LlmSummarizer
from backend.processing.llm_place import LlmPlacefinder
from backend.processing.llm_headline import LlmHeadlineEditor
from backend.processing.llm_image_keywords import LlmImageKeywordsGenerator
from backend.processing.fetch_image import ImageFetcher
from backend.processing.image_match_scorer import SigLIPMatcher


class MainProcessPipeline():
    def __init__(self, url, model):
        self.url = url
        self.model = model


    def run_pipeline(self, data_path:str):
        self.data_path = data_path

        content_summerizer = LlmSummarizer(self.url, self.model)
        content_place_finder = LlmPlacefinder(self.url, self.model)
        content_headline_writer = LlmHeadlineEditor(self.url, self.model)
        content_image_keyword_generator = LlmImageKeywordsGenerator(self.url, self.model)
        content_image_fetcher = ImageFetcher(model="llama3:latest")
    



        with open(data_path, 'r+', encoding="utf-8") as f:
            data = json.load(f)

        data = data[:3]

        feed_data = []

        for section in data:
            content = section["content"]
            id = section["id"]
            category = section["category"]
            summarized_content = content_summerizer.summarize(content)
            place = content_place_finder.trace_location(content, "")
            headline_draft = content_headline_writer.write_headline(summarized_content, "")
            print(headline_draft)
            headline = content_headline_writer.validate_headline(summarized_content, headline_draft)
            image_keywords = content_image_keyword_generator.generate_keywords(content)
            image_keywords = image_keywords.split(",")
            print(image_keywords)
            images = content_image_fetcher.get_images(keywords=image_keywords,image_id=id, pexels_per_keyword=3, unsplash_per_keyword=2)

            content_image_match_scorer = SigLIPMatcher()
            image_scores = []
            for image in images:
                candidate_image_path = image["local_path"]
                score = content_image_match_scorer.score(candidate_image_path, headline)
                image_scores.append(score)

            matched_image = images[image_scores.index(max(image_scores))]["url"]

            feed_data.append({
                "id": id,
                "category": category,
                "title": headline,
                "image": matched_image,
                "place": place,
                "time": datetime.now().strftime("%b %d, %Y"),
                "content": summarized_content,
            })

        return feed_data







