"""YouTube video metadata and transcript extraction.

Supports:
- Transcript extraction via youtube-transcript-api (no API key needed)
- Metadata via YouTube oEmbed API (no API key needed)
- Fallback metadata via yt-dlp (no API key needed)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

import httpx

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
#  URL helpers                                                         #
# ------------------------------------------------------------------ #

_YT_PATTERNS = [
    re.compile(r"(?:youtube\.com/watch\?.*v=|youtu\.be/|youtube\.com/embed/|youtube\.com/v/|youtube\.com/shorts/)([a-zA-Z0-9_-]{11})"),
]


def is_youtube_url(url: str) -> bool:
    """Check whether a URL points to a YouTube video."""
    parsed = urlparse(url)
    host = parsed.netloc.lower().replace("www.", "")
    return host in ("youtube.com", "youtu.be", "m.youtube.com", "music.youtube.com")


def extract_video_id(url: str) -> Optional[str]:
    """Extract the 11-char video ID from any YouTube URL variant."""
    for pattern in _YT_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1)
    # Fallback: parse query string
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    v = qs.get("v")
    if v:
        return v[0][:11]
    # youtu.be/<id>
    if "youtu.be" in parsed.netloc:
        path = parsed.path.strip("/")
        if len(path) == 11:
            return path
    return None


# ------------------------------------------------------------------ #
#  Data classes                                                        #
# ------------------------------------------------------------------ #

@dataclass
class TranscriptSegment:
    """A single transcript segment with timing."""

    text: str
    start: float
    duration: float


@dataclass
class YouTubeVideoData:
    """All extracted data for a YouTube video."""

    video_id: str
    url: str
    title: str = "Unknown Video"
    channel: str = ""
    description: str = ""
    thumbnail_url: str = ""
    duration_seconds: int = 0
    upload_date: str = ""
    view_count: int = 0
    transcript_segments: List[TranscriptSegment] = field(default_factory=list)
    transcript_text: str = ""
    transcript_language: str = ""
    chapters: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def duration_display(self) -> str:
        """Human-readable duration string."""
        if not self.duration_seconds:
            return ""
        m, s = divmod(self.duration_seconds, 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"

    @property
    def word_count(self) -> int:
        return len(self.transcript_text.split()) if self.transcript_text else 0


# ------------------------------------------------------------------ #
#  Extractor                                                           #
# ------------------------------------------------------------------ #

class YouTubeExtractor:
    """Extract metadata and transcripts from YouTube videos."""

    async def extract(self, url: str) -> YouTubeVideoData:
        """Full extraction pipeline for a YouTube video.

        Args:
            url: Any YouTube URL

        Returns:
            YouTubeVideoData with metadata and transcript
        """
        video_id = extract_video_id(url)
        if not video_id:
            return YouTubeVideoData(
                video_id="",
                url=url,
                error="Could not extract YouTube video ID from URL",
            )

        canonical_url = f"https://www.youtube.com/watch?v={video_id}"
        data = YouTubeVideoData(video_id=video_id, url=canonical_url)

        # Step 1: Get metadata
        await self._fetch_metadata(data)

        # Step 2: Get transcript
        await self._fetch_transcript(data)

        return data

    async def _fetch_metadata(self, data: YouTubeVideoData) -> None:
        """Fetch video metadata via oEmbed API, fall back to yt-dlp."""
        # Try oEmbed first (fast, no deps)
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    "https://www.youtube.com/oembed",
                    params={"url": data.url, "format": "json"},
                )
                resp.raise_for_status()
                oembed = resp.json()

            data.title = oembed.get("title", data.title)
            data.channel = oembed.get("author_name", "")
            data.thumbnail_url = oembed.get("thumbnail_url", "")
            logger.info("YouTube oEmbed metadata fetched for %s", data.video_id)
        except Exception as e:
            logger.warning("oEmbed failed for %s: %s", data.video_id, str(e))

        # Enrich with yt-dlp if available (gets duration, description, chapters, etc.)
        try:
            await self._enrich_with_ytdlp(data)
        except Exception as e:
            logger.debug("yt-dlp enrichment skipped: %s", str(e))

    async def _enrich_with_ytdlp(self, data: YouTubeVideoData) -> None:
        """Use yt-dlp to extract additional metadata (runs in thread)."""
        import asyncio

        def _extract() -> Dict[str, Any]:
            try:
                import yt_dlp

                opts = {
                    "quiet": True,
                    "no_warnings": True,
                    "skip_download": True,
                    "extract_flat": False,
                }
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(data.url, download=False)
                    return info or {}
            except Exception as exc:
                logger.debug("yt-dlp extract_info failed: %s", exc)
                return {}

        info = await asyncio.to_thread(_extract)
        if not info:
            return

        data.title = info.get("title") or data.title
        data.channel = info.get("channel") or info.get("uploader") or data.channel
        data.description = info.get("description") or ""
        data.duration_seconds = info.get("duration") or 0
        data.upload_date = info.get("upload_date") or ""
        data.view_count = info.get("view_count") or 0
        data.tags = info.get("tags") or []

        # Extract chapters
        chapters_raw = info.get("chapters") or []
        data.chapters = [
            {
                "title": ch.get("title", f"Chapter {i + 1}"),
                "start_time": ch.get("start_time", 0),
                "end_time": ch.get("end_time", 0),
            }
            for i, ch in enumerate(chapters_raw)
        ]

        # Prefer the best thumbnail
        thumbnails = info.get("thumbnails") or []
        if thumbnails:
            best = max(thumbnails, key=lambda t: (t.get("width") or 0) * (t.get("height") or 0))
            data.thumbnail_url = best.get("url") or data.thumbnail_url

        logger.info(
            "yt-dlp metadata enriched for %s: duration=%ds, chapters=%d",
            data.video_id, data.duration_seconds, len(data.chapters),
        )

    async def _fetch_transcript(self, data: YouTubeVideoData) -> None:
        """Fetch transcript via youtube-transcript-api."""
        import asyncio

        def _get_transcript() -> tuple[List[Dict[str, Any]], str]:
            try:
                from youtube_transcript_api import YouTubeTranscriptApi

                # Try English first, then any available language
                try:
                    segments = YouTubeTranscriptApi.get_transcript(
                        data.video_id, languages=["en", "en-US", "en-GB"]
                    )
                    return segments, "en"
                except Exception:
                    # Fall back to any available transcript
                    transcript_list = YouTubeTranscriptApi.list_transcripts(data.video_id)
                    # Prefer manually created over auto-generated
                    for transcript in transcript_list:
                        segments = transcript.fetch()
                        lang = transcript.language_code
                        return [{"text": s.text, "start": s.start, "duration": s.duration} for s in segments], lang

                    return [], ""
            except Exception as e:
                logger.warning("Transcript fetch failed for %s: %s", data.video_id, str(e))
                return [], ""

        segments, lang = await asyncio.to_thread(_get_transcript)

        if segments:
            data.transcript_language = lang
            data.transcript_segments = [
                TranscriptSegment(
                    text=seg.get("text", "") if isinstance(seg, dict) else getattr(seg, "text", ""),
                    start=seg.get("start", 0) if isinstance(seg, dict) else getattr(seg, "start", 0),
                    duration=seg.get("duration", 0) if isinstance(seg, dict) else getattr(seg, "duration", 0),
                )
                for seg in segments
            ]
            data.transcript_text = " ".join(
                seg.text for seg in data.transcript_segments
            )
            logger.info(
                "Transcript fetched for %s: %d segments, %d words, lang=%s",
                data.video_id,
                len(data.transcript_segments),
                data.word_count,
                lang,
            )
        else:
            logger.warning("No transcript available for %s", data.video_id)
