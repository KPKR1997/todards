import torch
from PIL import Image
from transformers import AutoProcessor, AutoModel


class SigLIPMatcher:

    def __init__(
        self,
        model_name="google/siglip-base-patch16-224"
    ):
        self.device = (
            "cuda"
            if torch.cuda.is_available()
            else "cpu"
        )

        self.processor = AutoProcessor.from_pretrained(
            model_name
        )

        self.model = AutoModel.from_pretrained(
            model_name
        ).to(self.device)

        self.model.eval()

    def score(
        self,
        image_path: str,
        paragraph: str
    ) -> float:

        image = Image.open(
            image_path
        ).convert("RGB")

        inputs = self.processor(
            text=[paragraph],
            images=image,
            padding="max_length",
            return_tensors="pt"
        ).to(self.device)

        with torch.no_grad():

            outputs = self.model(**inputs)

            logit = outputs.logits_per_image[0][0]

            score = torch.sigmoid(logit).item()

        return score


