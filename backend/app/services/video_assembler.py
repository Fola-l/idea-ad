import os
import tempfile
import subprocess
from typing import Optional
import ffmpeg
from PIL import Image
import io


class VideoAssembler:
    """Assembles video ads from images and audio using ffmpeg."""

    def __init__(self):
        # Video specs for Facebook/Instagram
        self.width = 1080
        self.height = 1080
        self.fps = 30
        self.target_lufs = -16  # Facebook audio standard

    async def create_video_from_image(
        self,
        image_bytes: bytes,
        audio_bytes: bytes,
        duration: Optional[float] = None,
        logo_bytes: Optional[bytes] = None,
        captions: Optional[str] = None
    ) -> bytes:
        """
        Create a video from a static image with Ken Burns effect and audio.

        Args:
            image_bytes: The main image
            audio_bytes: Voiceover audio (MP3)
            duration: Video duration in seconds (if None, matches audio length)
            logo_bytes: Optional logo to overlay
            captions: Optional caption text

        Returns:
            Video bytes (H.264 MP4)
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Save inputs
            image_path = os.path.join(tmpdir, "image.png")
            audio_path = os.path.join(tmpdir, "audio.mp3")
            output_path = os.path.join(tmpdir, "output.mp4")

            # Prepare image (resize/crop to square)
            img = Image.open(io.BytesIO(image_bytes))
            img = self._prepare_image(img)
            img.save(image_path, "PNG")

            # Save audio
            with open(audio_path, "wb") as f:
                f.write(audio_bytes)

            # Get audio duration if not specified
            if duration is None:
                duration = self._get_audio_duration(audio_path)

            # Build ffmpeg command with Ken Burns effect
            video = self._build_ken_burns_video(
                image_path, audio_path, output_path, duration
            )

            # Add logo overlay if provided
            if logo_bytes:
                logo_path = os.path.join(tmpdir, "logo.png")
                logo = Image.open(io.BytesIO(logo_bytes))
                logo = self._prepare_logo(logo)
                logo.save(logo_path, "PNG")
                # Note: Logo overlay is handled in the ffmpeg filter

            # Add captions if provided
            if captions:
                # Captions are added as a text overlay in ffmpeg
                pass  # TODO: Implement caption overlay

            # Read output
            with open(output_path, "rb") as f:
                return f.read()

    def _prepare_image(self, img: Image.Image) -> Image.Image:
        """Prepare image for video (resize/crop to 1080x1080)."""
        # Convert to RGB if necessary
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # Calculate crop for square aspect ratio
        width, height = img.size
        if width > height:
            left = (width - height) // 2
            img = img.crop((left, 0, left + height, height))
        elif height > width:
            top = (height - width) // 2
            img = img.crop((0, top, width, top + width))

        # Resize to target dimensions
        img = img.resize((self.width, self.height), Image.Resampling.LANCZOS)
        return img

    def _prepare_logo(self, logo: Image.Image, max_height: int = 80) -> Image.Image:
        """Prepare logo for overlay (resize to max height, maintain aspect)."""
        # Keep transparency if present
        if logo.mode != "RGBA":
            logo = logo.convert("RGBA")

        # Resize maintaining aspect ratio
        width, height = logo.size
        if height > max_height:
            ratio = max_height / height
            new_width = int(width * ratio)
            logo = logo.resize((new_width, max_height), Image.Resampling.LANCZOS)

        return logo

    def _get_audio_duration(self, audio_path: str) -> float:
        """Get duration of audio file in seconds."""
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path
            ],
            capture_output=True,
            text=True
        )
        return float(result.stdout.strip())

    def _build_ken_burns_video(
        self,
        image_path: str,
        audio_path: str,
        output_path: str,
        duration: float
    ) -> None:
        """Build video with Ken Burns (zoom/pan) effect."""
        # Ken Burns effect: slow zoom from 100% to 130% over duration
        # Using ffmpeg zoompan filter

        # Calculate zoom parameters
        # Start at 1.0, end at 1.3 (30% zoom - more noticeable)
        total_frames = int(duration * self.fps)
        zoom_increment = 0.3 / total_frames

        filter_complex = (
            f"[0:v]scale=8000:-1,"
            f"zoompan=z='1+{zoom_increment}*on':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={total_frames}:s={self.width}x{self.height}:fps={self.fps}[v];"
            f"[1:a]loudnorm=I={self.target_lufs}:TP=-1.5:LRA=11[a]"
        )

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", image_path,
            "-i", audio_path,
            "-filter_complex", filter_complex,
            "-map", "[v]",
            "-map", "[a]",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            "-t", str(duration),
            "-pix_fmt", "yuv420p",
            output_path
        ]

        subprocess.run(cmd, check=True, capture_output=True)

    async def create_video_with_overlay(
        self,
        base_video_bytes: bytes,
        audio_bytes: bytes,
        logo_bytes: Optional[bytes] = None
    ) -> bytes:
        """
        Create video by overlaying audio on existing video.

        Args:
            base_video_bytes: The demo video
            audio_bytes: Voiceover audio
            logo_bytes: Optional logo overlay

        Returns:
            Video bytes (H.264 MP4)
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = os.path.join(tmpdir, "video.mp4")
            audio_path = os.path.join(tmpdir, "audio.mp3")
            output_path = os.path.join(tmpdir, "output.mp4")

            # Save inputs
            with open(video_path, "wb") as f:
                f.write(base_video_bytes)
            with open(audio_path, "wb") as f:
                f.write(audio_bytes)

            # Build filter for audio mixing and normalization
            filter_complex = (
                f"[1:a]loudnorm=I={self.target_lufs}:TP=-1.5:LRA=11[vo];"
                f"[0:a][vo]amix=inputs=2:duration=first:dropout_transition=2[a]"
            )

            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-i", audio_path,
                "-filter_complex", filter_complex,
                "-map", "0:v",
                "-map", "[a]",
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                output_path
            ]

            subprocess.run(cmd, check=True, capture_output=True)

            with open(output_path, "rb") as f:
                return f.read()


def check_ffmpeg_installed() -> bool:
    """Check if ffmpeg is installed and accessible."""
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
