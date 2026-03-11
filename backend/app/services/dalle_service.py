import httpx
import base64
from typing import Optional
from openai import OpenAI

from app.config import get_settings


class DalleService:
    def __init__(self):
        settings = get_settings()
        self.client = OpenAI(api_key=settings.openai_api_key)

    async def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard"
    ) -> bytes:
        """
        Generate an image using DALL-E 3.

        Args:
            prompt: The image generation prompt
            size: Image size (1024x1024 for square ads)
            quality: "standard" or "hd" (hd is 2x cost)

        Returns:
            Image bytes
        """
        # Enhance prompt for ad-quality images
        enhanced_prompt = self._enhance_prompt(prompt)

        # Generate image
        response = self.client.images.generate(
            model="dall-e-3",
            prompt=enhanced_prompt,
            size=size,
            quality=quality,
            response_format="b64_json",
            n=1
        )

        # Decode base64 to bytes
        image_b64 = response.data[0].b64_json
        return base64.b64decode(image_b64)

    def _enhance_prompt(self, prompt: str) -> str:
        """Enhance the prompt for better ad-quality images."""
        enhancements = [
            "professional product advertisement",
            "clean background",
            "no text overlay",
            "suitable for Facebook ad",
            "high quality",
            "modern aesthetic",
            "well-lit"
        ]
        return f"{prompt}. {', '.join(enhancements)}"

    async def generate_image_url(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard"
    ) -> str:
        """
        Generate an image and return a temporary URL.

        Note: OpenAI URLs expire after 1 hour, so download and store elsewhere.

        Args:
            prompt: The image generation prompt
            size: Image size
            quality: Image quality

        Returns:
            Temporary URL to the generated image
        """
        enhanced_prompt = self._enhance_prompt(prompt)

        response = self.client.images.generate(
            model="dall-e-3",
            prompt=enhanced_prompt,
            size=size,
            quality=quality,
            response_format="url",
            n=1
        )

        return response.data[0].url


async def download_image(url: str) -> bytes:
    """Download an image from a URL."""
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.content
