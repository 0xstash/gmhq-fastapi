from __future__ import annotations

import os
import time
from typing import Any, Literal
from urllib.parse import urljoin

import requests
from attrs import Factory, define, field

from griptape.artifacts import ImageArtifact
from griptape.drivers import BaseImageGenerationDriver
from griptape.utils import import_optional_dependency


def steps_validator(instance, attribute, value):
    if value and (value < 1 or value > 50):
        raise ValueError("steps must be between 1 and 50")


def size_validator(instance, attribute, value):
    if value and value % 32 != 0:
        raise ValueError(f"{attribute} must be a multiple of 32")
    if value and value < 256 or value > 1440:
        raise ValueError(f"{attribute} must be between 256 and 1440")


def safety_validator(instance, attribute, value):
    if value and (value < 0 or value > 6):
        raise ValueError("safety_tolerance must be between 0 and 6")


def aspect_ratio_validator(instance, attribute, value):
    if value:
        width, height = value.split(":")
        if int(width) < 9 or int(width) > 21 or int(height) < 9 or int(height) > 21:
            raise ValueError("aspect_ratio must be between 9:21 and 21:9")


def guidance_validator(instance, attribute, value):
    if value and (value < 1.5 or value > 5):
        raise ValueError("guidance must be between 1.5 and 5")


def guidance_canny_validator(instance, attribute, value):
    if value and (value < 1 or value > 100):
        raise ValueError("guidance-canny must be between 1 and 100")


def interval_validator(instance, attribute, value):
    if value and (value < 1 or value > 4):
        raise ValueError("interval must be between 1 and 4")


def image_prompt_strength_validator(instance, attribute, value):
    if value and (value < 0 or value > 1):
        raise ValueError("image_prompt_strength must be between 0 and 1")


@define
class BlackForestImageGenerationDriver(BaseImageGenerationDriver):
    """Driver for the Black Forest Labs image generation API.

    Attributes:
        model: Black Forest model, for example 'flux-pro-1.1', 'flux-pro', 'flux-dev', 'flux-pro-1.1-ultra', 'flux-pro-1.0-canny'. Note - for inpainting, use 'flux-pro-1.0'.
        width: Width of the generated image. Valid for 'flux-pro-1.1', 'flux-pro', 'flux-dev' models only. Integer range from 256 to 1440. Must be a multiple of 32. Default is 1024.
        height: Height of the generated image. Valid for 'flux-pro-1.1', 'flux-pro', 'flux-dev' models only. Integer range from 256 to 1440. Must be a multiple of 32. Default is 1024.
        aspect_ratio: Aspect ratio of the generated image between 21:9 and 9:21. Valid for 'flux-pro-1.1-ultra' model only. Default is 16:9.
        prompt_upsampling: Optional flag to perform upsampling on the prompt. Valid for `flux-pro-1.1', 'flux-pro', 'flux-dev' models only. If active, automatically modifies the prompt for more creative generation.
        safety_tolerance: Optional tolerance level for input and output moderation. Between 0 and 6, 0 being most strict, 6 being least strict.
        seed: Optional seed for reproducing results. Default is None.
        steps: Optional number of steps for the image generation process. Valid for 'flux-dev' and `flux-pro` models only. Can be a value between 1 and 50. Default is None.
        guidance: Optional guidance scale for image generation. High guidance scales improve prompt adherence at the cost of reduced realism. For 'flux-dev' and 'flux-pro', values are 1.5-5. For 'flux-pro-1.0-canny' and 'flux-pro-1.0-depth' values are 1-100.
        guidance-canny: Optional guidance scale for canny image generation. Valid for 'flux-pro-1.0-canny'. Min: 1, max: 100
        interval: Optional interval parameter for guidance control. Valid for 'flux-pro' model only. Value is an integer between 1 and 4. Default is None.
        raw: Optional flag to generate less processed, more natural-looking images. Valid for 'flux-pro-1.1-ultra' model only. Default is False.
        output_format: Output format of the generated image. Can be 'jpeg' or 'png'. Default is 'jpeg'.
        image_prompt_strength: Optional flag to control the strength of the image prompt. Valid for 'flux-pro-1.1-ultra' model only. Valid is float between 0 and 1. Default is 0.1.
        canny: Optional flag to manipulate an image using canny control net. Valid for 'flux-pro-1.0' model only. Default is False.
    """

    base_url: str = field(
        default="https://api.bfl.ml",
        kw_only=True,
        metadata={"serializable": False},
    )
    api_key: str | None = field(
        default=Factory(lambda: os.environ["BFL_API_KEY"]),
        kw_only=True,
        metadata={"serializable": False},
    )
    width: int = field(default=1024, kw_only=True, validator=size_validator)
    height: int = field(default=768, kw_only=True, validator=size_validator)
    sleep_interval: float = field(default=0.5, kw_only=True)
    safety_tolerance: int | None = field(
        default=None, kw_only=True, validator=safety_validator
    )
    aspect_ratio: str = field(
        default=None, kw_only=True, validator=aspect_ratio_validator
    )
    seed: int | None = field(default=None, kw_only=True)
    prompt_upsampling: bool = field(default=False, kw_only=True)
    steps: int | None = field(default=None, kw_only=True, validator=steps_validator)
    guidance: float | None = field(default=None, kw_only=True)
    # guidance_canny: float | None = field(
    #     default=None, kw_only=True, validator=guidance_canny_validator
    # )
    interval: int | None = field(
        default=None, kw_only=True, validator=interval_validator
    )
    raw: bool = field(default=False, kw_only=True)
    output_format: str = field(default="jpeg", kw_only=True)
    image_prompt_strength: float = field(default=0.1, kw_only=True)

    def _build_base_payload(self, prompts: list[str]) -> dict[str, Any]:
        """Build the base payload with common parameters."""
        data: dict[str, Any] = {
            "prompt": " ".join(prompts),
        }

        if self.seed:
            data["seed"] = self.seed
        if self.safety_tolerance:
            data["safety_tolerance"] = self.safety_tolerance
        if self.output_format:
            data["output_format"] = self.output_format

        # Ultra model specific settings
        if self.model == "flux-pro-1.1-ultra":
            if self.aspect_ratio:
                data["aspect_ratio"] = self.aspect_ratio
                data["image_prompt_strength"] = self.image_prompt_strength
            if self.raw:
                data["raw"] = self.raw

        # Pro model specific setting
        if self.model == "flux-pro":
            if self.interval:
                data["interval"] = int(self.interval)

        # Pro/Dev/canny/depth model specific settings
        if self.model in [
            "flux-dev",
            "flux-pro",
            "flux-pro-1.0-canny",
            "flux-pro-1.0-depth",
        ]:
            if self.guidance:
                data["guidance"] = float(self.guidance)
            if self.steps:
                data["steps"] = int(self.steps)
            if self.prompt_upsampling:
                data["prompt_upsampling"] = self.prompt_upsampling

        # Settings for specific model types
        if self.model in ["flux-pro-1.1", "flux-pro", "flux-dev"]:
            data["width"] = self.width
            data["height"] = self.height

        return data

    def _make_request(
        self,
        endpoint: str,
        data: dict[str, Any],
        operation: Literal["generate", "fill"],
    ) -> ImageArtifact:
        """Make API request and handle response."""
        url_suffix = f"-{operation}" if operation == "fill" else ""
        request = requests.post(
            urljoin(self.base_url, f"v1/{endpoint}{url_suffix}"),
            headers={
                "accept": "application/json",
                "x-key": self.api_key,
                "Content-Type": "application/json",
            },
            json=data,
        ).json()

        # Poll for results
        request_id = request["id"]
        while True:
            time.sleep(self.sleep_interval)
            result = requests.get(
                urljoin(self.base_url, "v1/get_result"),
                headers={"accept": "application/json", "x-key": self.api_key},
                params={"id": request_id},
            ).json()
            if result["status"] == "Ready":
                image_url = result["result"]["sample"]
                break

        # Get final image
        image_response = requests.get(image_url)
        return ImageArtifact(
            value=image_response.content,
            format=self.output_format,
            width=self.width,
            height=self.height,
        )

    def _validate_base64(self, image_data: str) -> None:
        """Validate base64 encoded image data."""
        if not self._is_base64(image_data):
            raise ValueError("Image data is not base64 encoded.")

    def try_text_to_image(
        self, prompts: list[str], negative_prompts: list[str] | None = None
    ) -> ImageArtifact:
        data = self._build_base_payload(prompts)

        return self._make_request(self.model, data, "generate")

    def try_image_variation(
        self,
        prompts: list[str],
        image: ImageArtifact,
        negative_prompts: list[str] | None = None,
    ) -> ImageArtifact:
        # Get the base64 encoded image data
        image_data = image.base64

        self._validate_base64(image_data)

        data = self._build_base_payload(prompts)

        if self.model in ["flux-pro-1.0-canny", "flux-pro-1.0-depth"]:
            data["control_image"] = image_data
        else:
            data["image_prompt"] = image_data

        return self._make_request(self.model, data, "generate")

    def try_image_inpainting(
        self,
        prompts: list[str],
        image: ImageArtifact,
        mask: ImageArtifact,
        negative_prompts: list[str] | None = None,
    ) -> ImageArtifact:
        image_data = image.base64
        mask_data = mask.base64
        self._validate_base64(image_data)

        data = self._build_base_payload(prompts)
        data.update({"image": image_data, "mask": mask_data})

        return self._make_request(self.model, data, "fill")

    def try_image_outpainting(
        self,
        prompts: list[str],
        image: ImageArtifact,
        mask: ImageArtifact,
        negative_prompts: list[str] | None = None,
    ) -> ImageArtifact:
        # outpainting is done using the same method as inpainting
        return self.try_image_inpainting(prompts, image, mask, negative_prompts)

    def _is_base64(self, s: str) -> bool:
        base64 = import_optional_dependency("base64")

        if len(s) % 4 != 0:
            return False

        try:
            # Decode and then re-encode to check if it matches the original
            return base64.b64encode(base64.b64decode(s)).decode("utf-8") == s
        except Exception:
            return False
