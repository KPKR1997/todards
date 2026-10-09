import base64

import json

import logging

from pathlib import Path

from typing import List, Dict, Any, Optional



import requests



from config.settings import OLLAMA_BASE_URL





logger = logging.getLogger("todards.image_safety")





class ImageSafetyGuard:

    """

    Local image-safety screening for Todards.



    Uses a local Ollama vision model to classify images.



    Current model:

        gemma3:4b



    The model evaluates:

        - sexual content

        - nudity

        - graphic violence

        - severe injury

        - abuse

        - disturbing imagery



    This is separate from ArticleSafetyGuard.



    ArticleSafetyGuard:

        Text safety



    ImageSafetyGuard:

        Visual safety

    """



    def __init__(

        self,

        model: str = "gemma3:4b",

        ollama_url: str = OLLAMA_BASE_URL,

        timeout: int = 120,

    ):

        self.model = model

        self.ollama_url = ollama_url.rstrip("/")

        self.timeout = timeout



        self.api_url = (

            f"{self.ollama_url}/api/chat"

        )



    # ============================================================

    # IMAGE ENCODING

    # ============================================================



    def _encode_image(
        self,
        image_path: str,
    ) -> str:
        """
        Convert a local image or remote image URL into base64.

        Remote images are downloaded to a temporary file, read for
        safety analysis, and ALWAYS deleted afterwards.

        Local images are read directly and are never deleted.
        """

        if not image_path:
            raise ValueError("Image path/URL is empty.")

        # ------------------------------------------------------------
        # Remote image URL
        # ------------------------------------------------------------

        if image_path.startswith(("http://", "https://")):

            temp_path = None

            try:
                import tempfile

                # Preserve a useful extension where possible.
                suffix = (
                    Path(
                        image_path.split("?", 1)[0]
                    ).suffix
                    or ".jpg"
                )

                # Download to a temporary file.
                with tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=suffix,
                ) as temp_file:

                    temp_path = Path(
                        temp_file.name
                    )

                logger.debug(
                    "Downloading remote image for safety check: %s",
                    image_path,
                )

                response = requests.get(
                    image_path,
                    timeout=self.timeout,
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 "
                            "(Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 "
                            "(KHTML, like Gecko) "
                            "Chrome/154.0 Safari/537.36"
                        )
                    },
                )

                response.raise_for_status()

                temp_path.write_bytes(
                    response.content
                )

                image_bytes = temp_path.read_bytes()

                if not image_bytes:
                    raise ValueError(
                        f"Downloaded image is empty: {image_path}"
                    )

                return base64.b64encode(
                    image_bytes
                ).decode("utf-8")

            finally:
                # IMPORTANT:
                # Always delete the temporary downloaded image.
                if temp_path is not None:

                    try:
                        temp_path.unlink(
                            missing_ok=True
                        )

                        logger.debug(
                            "Deleted temporary image: %s",
                            temp_path,
                        )

                    except Exception as cleanup_error:

                        logger.warning(
                            "Could not delete temporary "
                            "image '%s': %s",
                            temp_path,
                            cleanup_error,
                        )

        # ------------------------------------------------------------
        # Local image path
        # ------------------------------------------------------------

        path = Path(image_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Image not found: {image_path}"
            )

        if not path.is_file():
            raise ValueError(
                f"Image path is not a file: {image_path}"
            )

        with open(
            path,
            "rb",
        ) as f:

            image_bytes = f.read()

        if not image_bytes:
            raise ValueError(
                f"Image is empty: {image_path}"
            )

        return base64.b64encode(
            image_bytes
        ).decode("utf-8")

    # PROMPT

    # ============================================================



    def _build_prompt(self) -> str:

        """

        Build the image safety classification prompt.

        """



        return """

You are a visual safety classifier for a professional

news publishing platform.



Analyze ONLY the image.



The image may be a legitimate news photograph.



Classify whether the image contains any of the following:



1\. Sexual content

   - sexually explicit activity

   - clearly sexual imagery

   - sexually explicit poses



2\. Nudity

   - explicit or clearly visible nudity

   - do not classify ordinary clothing as nudity



3\. Graphic violence

   - visible severe injury

   - dismemberment

   - exposed bodily tissue

   - graphic death

   - extreme blood or gore



4\. Abuse

   - clearly depicted physical abuse

   - torture

   - severe mistreatment



5\. Disturbing content

   - extremely disturbing imagery that would be

     inappropriate for a general-audience news homepage



IMPORTANT:



Do NOT reject an image merely because it depicts:



\- ordinary people

\- celebrities

\- politicians

\- protests

\- crowds

\- police

\- military personnel

\- hospitals

\- doctors

\- scientific research

\- medical equipment

\- ordinary accidents without graphic detail

\- sports

\- normal beach/swimwear clothing

\- historical events

\- buildings

\- vehicles

\- disasters without graphic imagery



Newsworthiness is NOT part of this classification.



Return ONLY valid JSON.



Use exactly this structure:



{

    "safe": true,

    "sexual_content": false,

    "nudity": false,

    "graphic_violence": false,

    "abuse": false,

    "disturbing_content": false,

    "confidence": 0.95

}



Set "safe" to false if any of the following are

clearly present:



\- sexual_content

\- nudity

\- graphic_violence

\- abuse

\- disturbing_content



If you cannot confidently determine the classification,

set "safe" to false.



Do not provide an explanation.

"""



    # ============================================================

    # JSON EXTRACTION

    # ============================================================



    def _extract_json(

        self,

        response_text: str,

    ) -> dict:

        """

        Extract JSON from the vision model response.

        """



        if not response_text:

            raise ValueError(

                "Vision model returned an empty response."

            )



        text = response_text.strip()



        # Remove markdown code fences.

        if text.startswith("\`\`\`"):



            lines = text.splitlines()



            if lines:

                lines = lines[1:]



            if (

                lines

                and lines[-1]

                .strip()

                .startswith("\`\`\`")

            ):

                lines = lines[:-1]



            text = "\n".join(

                lines

            ).strip()



        start = text.find("{")

        end = text.rfind("}")



        if start == -1 or end == -1:

            raise ValueError(

                "No JSON object found in vision response."

            )



        json_text = text[

            start:end + 1

        ]



        result = json.loads(

            json_text

        )



        if not isinstance(

            result,

            dict,

        ):

            raise ValueError(

                "Vision response JSON is not an object."

            )



        return result



    # ============================================================

    # IMAGE CHECK

    # ============================================================



    def check_image(
        self,
        image_path: str,
    ) -> Optional[bool]:
        """
        Analyze one image.

        Returns:

            True
                Image explicitly classified as safe.

            False
                Image explicitly classified as unsafe.

            None
                Safety check failed.
        """

        try:

            image_base64 = self._encode_image(
                image_path
            )

            prompt = self._build_prompt()

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                        "images": [
                            image_base64
                        ],
                    }
                ],
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0,
                },
            }

            response = requests.post(
                self.api_url,
                json=payload,
                timeout=self.timeout,
            )

            response.raise_for_status()

            data = response.json()

            message = data.get(
                "message",
                {},
            )

            content = message.get(
                "content",
                "",
            )

            result = self._extract_json(
                content
            )

            if "safe" not in result:
                raise ValueError(
                    "Vision model response does not contain "
                    "'safe'."
                )

            safe = result["safe"]

            if isinstance(
                safe,
                str,
            ):

                safe = (
                    safe.strip().lower()
                    in {
                        "true",
                        "yes",
                        "1",
                        "safe",
                    }
                )

            else:

                safe = bool(safe)

            # --------------------------------------------------------
            # Additional deterministic safety check
            # --------------------------------------------------------

            dangerous_flags = [
                "sexual_content",
                "nudity",
                "graphic_violence",
                "abuse",
                "disturbing_content",
            ]

            for flag in dangerous_flags:

                value = result.get(
                    flag,
                    False,
                )

                if isinstance(
                    value,
                    str,
                ):

                    value = (
                        value.strip().lower()
                        in {
                            "true",
                            "yes",
                            "1",
                        }
                    )

                if value:

                    safe = False

                    logger.warning(
                        f"Image safety flag '{flag}' "
                        f"detected: {image_path}"
                    )

            # --------------------------------------------------------
            # Confidence
            # --------------------------------------------------------

            confidence = result.get(
                "confidence",
                0,
            )

            try:

                confidence = float(
                    confidence
                )

            except (
                ValueError,
                TypeError,
            ):

                confidence = 0

            confidence = max(
                0.0,
                min(
                    1.0,
                    confidence,
                ),
            )

            # Conservative policy:
            # If the model says safe but has very low confidence,
            # don't publish the image.

            if safe and confidence < 0.50:

                logger.warning(
                    f"Low-confidence image safety result "
                    f"({confidence:.2f}): {image_path}"
                )

                return False

            logger.debug(
                f"Image safety result: "
                f"safe={safe}, "
                f"confidence={confidence:.2f}, "
                f"path={image_path}"
            )

            return safe

        except Exception as e:

            logger.error(
                f"Image safety inference failed for "
                f"'{image_path}': {e}"
            )

            return None


    # RUN

    # ============================================================



    def run(

        self,

        articles: List[Dict[str, Any]],

    ) -> List[Dict[str, Any]]:

        """

        Run image safety screening over processed articles.



        Policy:



            No image

                -> KEEP article



            Safe image

                -> KEEP article



            Unsafe image

                -> REMOVE article



            Safety-model error

                -> KEEP article and log error



        Keeping an article on model error prevents a temporary

        vision-model failure from deleting an entire news issue.

        """



        if not articles:



            logger.info(

                "Image safety guard received 0 articles."

            )



            return []



        safe_articles = []



        total_checked = 0

        total_safe = 0

        total_rejected = 0

        total_errors = 0

        total_no_image = 0



        for article in articles:



            image_path = article.get(

                "image"

            )



            # ----------------------------------------------------

            # No image

            # ----------------------------------------------------



            if not image_path:



                total_no_image += 1



                safe_articles.append(

                    article

                )



                continue



            # ----------------------------------------------------

            # Check image

            # ----------------------------------------------------



            total_checked += 1



            result = self.check_image(

                str(image_path)

            )



            # ----------------------------------------------------

            # SAFE

            # ----------------------------------------------------



            if result is True:



                total_safe += 1



                safe_articles.append(

                    article

                )



            # ----------------------------------------------------

            # UNSAFE

            # ----------------------------------------------------



            elif result is False:



                total_rejected += 1



                logger.warning(

                    "Image rejected by safety guard: "

                    f"{article.get('title', '')[:100]}"

                )



                # Article is removed because its only available

                # image failed the configured safety policy.



            # ----------------------------------------------------

            # ERROR

            # ----------------------------------------------------



            else:



                total_errors += 1



                logger.error(

                    "Image safety unavailable; "

                    "keeping article: "

                    f"{article.get('title', '')[:100]}"

                )



                safe_articles.append(

                    article

                )



        logger.info(

            "Image safety completed: "

            f"input={len(articles)}, "

            f"checked={total_checked}, "

            f"safe={total_safe}, "

            f"rejected={total_rejected}, "

            f"errors={total_errors}, "

            f"no_image={total_no_image}, "

            f"output={len(safe_articles)}"

        )



        return safe_articles