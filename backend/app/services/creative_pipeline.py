import uuid
from typing import Optional, Tuple
import httpx

from app.models import AdFormat, CreativeUrls
from app.services.dalle_service import DalleService, download_image
from app.services.tts_service import TTSService
from app.services.video_assembler import VideoAssembler
from app.db.supabase_client import upload_file


class CreativePipeline:
    """Orchestrates the creative generation pipeline."""

    def __init__(self):
        self.dalle = DalleService()
        self.tts = TTSService()
        self.video = VideoAssembler()

    async def generate_creative(
        self,
        job_id: str,
        format: AdFormat,
        image_prompt: str,
        voiceover_script: Optional[str] = None,
        demo_video_url: Optional[str] = None,
        demo_image_url: Optional[str] = None,
        logo_url: Optional[str] = None
    ) -> CreativeUrls:
        """
        Generate all creative assets for an ad.

        Decision tree:
        1. If demo video uploaded -> use it as base, add voiceover
        2. If demo image uploaded:
           - If format is video -> Ken Burns effect + voiceover
           - If format is image -> use as static ad
        3. If neither uploaded:
           - Generate image with DALL-E
           - If format is video -> Ken Burns effect + voiceover

        Args:
            job_id: Unique job identifier
            format: image or video
            image_prompt: DALL-E prompt for image generation
            voiceover_script: Script for TTS (required for video)
            demo_video_url: User-uploaded demo video URL
            demo_image_url: User-uploaded product image URL
            logo_url: Brand logo URL

        Returns:
            CreativeUrls with URLs to all generated assets
        """
        image_url = None
        video_url = None
        voiceover_url = None

        # Download logo if provided
        logo_bytes = None
        if logo_url:
            logo_bytes = await self._download_asset(logo_url)

        # Case 1: Demo video uploaded
        if demo_video_url:
            video_bytes = await self._download_asset(demo_video_url)

            if voiceover_script:
                # Generate voiceover
                audio_bytes = await self.tts.generate_voiceover(voiceover_script)
                voiceover_url = await self._upload_asset(
                    job_id, "voiceover.mp3", audio_bytes, "audio/mpeg"
                )

                # Overlay voiceover on video
                final_video = await self.video.create_video_with_overlay(
                    video_bytes, audio_bytes, logo_bytes
                )
                video_url = await self._upload_asset(
                    job_id, "video.mp4", final_video, "video/mp4"
                )
            else:
                # Just upload the demo video as-is
                video_url = await self._upload_asset(
                    job_id, "video.mp4", video_bytes, "video/mp4"
                )

            return CreativeUrls(
                video_url=video_url,
                voiceover_url=voiceover_url
            )

        # Case 2: Demo image uploaded
        if demo_image_url:
            image_bytes = await self._download_asset(demo_image_url)

            if format == AdFormat.VIDEO and voiceover_script:
                # Generate voiceover
                audio_bytes = await self.tts.generate_voiceover(voiceover_script)
                voiceover_url = await self._upload_asset(
                    job_id, "voiceover.mp3", audio_bytes, "audio/mpeg"
                )

                # Create video with Ken Burns effect
                final_video = await self.video.create_video_from_image(
                    image_bytes, audio_bytes, logo_bytes=logo_bytes
                )
                video_url = await self._upload_asset(
                    job_id, "video.mp4", final_video, "video/mp4"
                )

                return CreativeUrls(
                    video_url=video_url,
                    voiceover_url=voiceover_url
                )
            else:
                # Static image ad
                image_url = await self._upload_asset(
                    job_id, "image.png", image_bytes, "image/png"
                )

                return CreativeUrls(image_url=image_url)

        # Case 3: Generate image with DALL-E
        image_bytes = await self.dalle.generate_image(image_prompt)

        if format == AdFormat.VIDEO and voiceover_script:
            # Generate voiceover
            audio_bytes = await self.tts.generate_voiceover(voiceover_script)
            voiceover_url = await self._upload_asset(
                job_id, "voiceover.mp3", audio_bytes, "audio/mpeg"
            )

            # Create video with Ken Burns effect
            final_video = await self.video.create_video_from_image(
                image_bytes, audio_bytes, logo_bytes=logo_bytes
            )
            video_url = await self._upload_asset(
                job_id, "video.mp4", final_video, "video/mp4"
            )

            # Also save the generated image
            image_url = await self._upload_asset(
                job_id, "image.png", image_bytes, "image/png"
            )

            return CreativeUrls(
                image_url=image_url,
                video_url=video_url,
                voiceover_url=voiceover_url
            )
        else:
            # Static image ad
            image_url = await self._upload_asset(
                job_id, "image.png", image_bytes, "image/png"
            )

            return CreativeUrls(image_url=image_url)

    async def regenerate_image(
        self,
        job_id: str,
        image_prompt: str
    ) -> str:
        """Regenerate just the image with a new DALL-E call."""
        image_bytes = await self.dalle.generate_image(image_prompt)
        return await self._upload_asset(
            job_id, f"image_{uuid.uuid4().hex[:8]}.png", image_bytes, "image/png"
        )

    async def regenerate_voiceover(
        self,
        job_id: str,
        voiceover_script: str
    ) -> str:
        """Regenerate just the voiceover with a new TTS call."""
        audio_bytes = await self.tts.generate_voiceover(voiceover_script)
        return await self._upload_asset(
            job_id, f"voiceover_{uuid.uuid4().hex[:8]}.mp3", audio_bytes, "audio/mpeg"
        )

    async def _download_asset(self, url: str) -> bytes:
        """Download an asset from a URL."""
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content

    async def _upload_asset(
        self,
        job_id: str,
        filename: str,
        data: bytes,
        content_type: str
    ) -> str:
        """Upload an asset to Supabase storage."""
        path = f"{job_id}/{filename}"
        return await upload_file("creatives", path, data, content_type)
