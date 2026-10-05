import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


class StoryClusterer:
    """
    Groups semantically similar articles into story clusters.

    Example:

        BBC    -> Earthquake in Japan
        CNN    -> Japan earthquake kills hundreds
        Guardian -> Powerful earthquake strikes Japan

    These become one story cluster.
    """

    def __init__(
        self,
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        similarity_threshold=0.78,
    ):

        self.model = SentenceTransformer(
            model_name
        )

        self.similarity_threshold = (
            similarity_threshold
        )

    def _text_for_embedding(self, article):

        title = article.get(
            "title",
            "",
        )

        content = article.get(
            "content",
            "",
        )

        # Title is highly informative for story identity.
        return (
            f"{title}. {title}. "
            f"{content}"
        )

    def create_embeddings(
        self,
        articles,
    ):

        texts = [
            self._text_for_embedding(article)
            for article in articles
        ]

        if not texts:
            return np.array([])

        return self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=True,
        )

    def cluster(
        self,
        articles,
    ):

        if not articles:
            return []

        embeddings = self.create_embeddings(
            articles
        )

        similarity_matrix = cosine_similarity(
            embeddings
        )

        clusters = []

        assigned = set()

        for i in range(len(articles)):

            if i in assigned:
                continue

            cluster = [i]

            assigned.add(i)

            for j in range(
                i + 1,
                len(articles),
            ):

                if j in assigned:
                    continue

                similarity = float(
                    similarity_matrix[i, j]
                )

                if (
                    similarity
                    >= self.similarity_threshold
                ):

                    cluster.append(j)
                    assigned.add(j)

            clusters.append(cluster)

        return clusters

    def get_source_count(
        self,
        articles,
        cluster,
    ):

        sources = set()

        for index in cluster:

            article = articles[index]

            source = (
                article.get("source")
                or article.get("publisher")
                or article.get("site")
                or ""
            )

            if source:
                sources.add(
                    source.lower().strip()
                )

        # If source isn't explicitly stored,
        # different article IDs/files still count as
        # separate evidence.
        if not sources:

            sources = {
                str(
                    articles[index].get(
                        "id",
                        index,
                    )
                )
                for index in cluster
            }

        return max(
            1,
            len(sources),
        )