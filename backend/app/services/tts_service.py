import io
from typing import Literal
from openai import OpenAI

from app.config import get_settings


# Available OpenAI TTS voices
TTSVoice = Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"]


class TTSService:
    """OpenAI Text-to-Speech service for generating voiceovers."""

    def __init__(self):
        settings = get_settings()
        self.client = OpenAI(api_key=settings.openai_api_key)
        # Default voice - 'nova' is clean and neutral, good for ads
        self.default_voice: TTSVoice = "nova"

    async def generate_voiceover(
        self,
        text: str,
        voice: TTSVoice = None,
        speed: float = 1.0
    ) -> bytes:
        """
        Generate a voiceover from text using OpenAI TTS.

        Args:
            text: The voiceover script
            voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
            speed: Speech speed (0.25 to 4.0, default 1.0)

        Returns:
            Audio bytes (MP3 format)
        """
        if voice is None:
            voice = self.default_voice

        # OpenAI TTS has a 4096 character limit
        if len(text) > 4096:
            text = text[:4096]

        response = self.client.audio.speech.create(
            model="tts-1",  # Use tts-1-hd for higher quality
            voice=voice,
            input=text,
            speed=speed,
            response_format="mp3"
        )

        # Read the streaming response into bytes
        audio_bytes = io.BytesIO()
        for chunk in response.iter_bytes():
            audio_bytes.write(chunk)

        return audio_bytes.getvalue()

    async def generate_voiceover_hd(
        self,
        text: str,
        voice: TTSVoice = None,
        speed: float = 1.0
    ) -> bytes:
        """
        Generate high-quality voiceover using TTS-1-HD model.

        Higher quality but more expensive and slower.

        Args:
            text: The voiceover script
            voice: Voice to use
            speed: Speech speed

        Returns:
            Audio bytes (MP3 format)
        """
        if voice is None:
            voice = self.default_voice

        if len(text) > 4096:
            text = text[:4096]

        response = self.client.audio.speech.create(
            model="tts-1-hd",
            voice=voice,
            input=text,
            speed=speed,
            response_format="mp3"
        )

        audio_bytes = io.BytesIO()
        for chunk in response.iter_bytes():
            audio_bytes.write(chunk)

        return audio_bytes.getvalue()

    def estimate_duration(self, text: str, speed: float = 1.0) -> float:
        """
        Estimate voiceover duration in seconds.

        Average speaking rate is about 150 words per minute.

        Args:
            text: The voiceover script
            speed: Speech speed multiplier

        Returns:
            Estimated duration in seconds
        """
        words = len(text.split())
        # 150 words per minute = 2.5 words per second
        base_duration = words / 2.5
        return base_duration / speed


# Voice descriptions for reference
VOICE_DESCRIPTIONS = {
    "alloy": "Neutral, balanced - good for general use",
    "echo": "Warm, conversational - good for storytelling",
    "fable": "Expressive, dynamic - good for engaging content",
    "onyx": "Deep, authoritative - good for professional/B2B",
    "nova": "Clear, friendly - great for ads and marketing",
    "shimmer": "Bright, energetic - good for upbeat content"
}
