import httpx
import base64
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
        quality: str = "high"
    ) -> bytes:
        """
        Generate an image using GPT Image 1.5.

        Args:
            prompt: The image generation prompt
            size: Image size (1024x1024, 1024x1536, or 1536x1024)
            quality: "low", "medium", or "high"

        Returns:
            Image bytes
        """
        # Enhance prompt for ad-quality images
        enhanced_prompt = self._enhance_prompt(prompt)

        # Generate image with GPT Image 1.5 (returns base64 by default)
        response = self.client.images.generate(
            model="gpt-image-1.5",
            prompt=enhanced_prompt,
            size=size,
            quality=quality,
            n=1
        )

        # Decode base64 to bytes
        image_b64 = response.data[0].b64_json
        if not image_b64:
            raise ValueError(f"No b64_json returned from GPT Image 1.5. Response: {response}")

        print(f"Generated image successfully (base64 length: {len(image_b64)})")
        return base64.b64decode(image_b64)

    def _enhance_prompt(self, prompt: str) -> str:
        """Enhance the prompt with Send247 brand template for realistic ad photography."""
        # Focus on REALISTIC photography, not AI/CGI graphics
        photography_requirements = [
            "Professional commercial product photography, photorealistic style",
            "Shot on high-end camera with natural studio lighting",
            "Real-world scene, authentic photography aesthetic",
            "Clean minimal background with soft focus and negative space",
            "Modern DTC e-commerce product shot style",
            "Warm natural colors, professional color grading",
            "Shallow depth of field, professional composition",
            "NO text, NO digital graphics, NO network visualizations, NO CGI elements",
            "NO futuristic overlays, NO wireframes, NO abstract tech imagery",
            "Looks like real commercial photography for social media ads"
        ]
        return f"{prompt}. {' '.join(photography_requirements)}"

    async def generate_image_url(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "high"
    ) -> str:
        """
        Generate an image and return a temporary URL.

        Note: OpenAI URLs expire after 1 hour, so download and store elsewhere.

        Args:
            prompt: The image generation prompt
            size: Image size (1024x1024, 1024x1536, or 1536x1024)
            quality: "low", "medium", or "high"

        Returns:
            Temporary URL to the generated image
        """
        enhanced_prompt = self._enhance_prompt(prompt)

        response = self.client.images.generate(
            model="gpt-image-1.5",
            prompt=enhanced_prompt,
            size=size,
            quality=quality,
            n=1
        )

        return response.data[0].url


async def download_image(url: str) -> bytes:
    """Download an image from a URL."""
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.content
