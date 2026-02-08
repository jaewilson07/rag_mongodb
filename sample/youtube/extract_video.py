"""Sample script to extract YouTube video metadata and transcript.

Demonstrates the YouTubeExtractor pipeline:
1. Extract video ID from any YouTube URL format
2. Fetch metadata via oEmbed API
3. Enrich with yt-dlp (duration, chapters, views)
4. Extract transcript via youtube-transcript-api

Usage:
    uv run python sample/youtube/extract_video.py
    uv run python sample/youtube/extract_video.py --url "https://youtu.be/PAh870We7tI"
    uv run python sample/youtube/extract_video.py --url "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
"""

from __future__ import annotations

import argparse
import asyncio

from mdrag.integrations.youtube import YouTubeExtractor, extract_video_id, is_youtube_url

DEFAULT_URL = "https://youtu.be/PAh870We7tI"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract YouTube video metadata and transcript.",
    )
    parser.add_argument(
        "--url", default=DEFAULT_URL, help="YouTube video URL"
    )
    parser.add_argument(
        "--transcript-only",
        action="store_true",
        help="Print only the transcript text",
    )
    return parser.parse_args()


async def _run() -> None:
    args = _parse_args()
    url = args.url

    # Step 1: Validate and extract video ID
    print(f"URL: {url}")
    print(f"Is YouTube: {is_youtube_url(url)}")

    video_id = extract_video_id(url)
    print(f"Video ID: {video_id}")

    if not video_id:
        print("Error: Could not extract video ID from URL")
        return

    # Step 2: Full extraction
    print("\nExtracting video data...")
    extractor = YouTubeExtractor()
    data = await extractor.extract(url)

    if data.error:
        print(f"Error: {data.error}")
        return

    if args.transcript_only:
        if data.transcript_text:
            print(data.transcript_text)
        else:
            print("No transcript available.")
        return

    # Step 3: Display results
    print(f"\nTitle: {data.title}")
    print(f"Channel: {data.channel}")
    print(f"Duration: {data.duration_display} ({data.duration_seconds}s)")
    print(f"Views: {data.view_count:,}" if data.view_count else "Views: N/A")
    print(f"Upload Date: {data.upload_date or 'N/A'}")
    print(f"Thumbnail: {data.thumbnail_url}")
    print(f"Transcript Language: {data.transcript_language or 'N/A'}")
    print(f"Transcript Words: {data.word_count}")

    if data.tags:
        print(f"Tags: {', '.join(data.tags[:10])}")

    if data.chapters:
        print(f"\nChapters ({len(data.chapters)}):")
        for ch in data.chapters:
            start = ch.get("start_time", 0)
            m, s = divmod(int(start), 60)
            h, m = divmod(m, 60)
            ts = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
            print(f"  [{ts}] {ch.get('title', 'Untitled')}")

    if data.transcript_text:
        preview = data.transcript_text[:500]
        print(f"\nTranscript Preview ({data.word_count} words):")
        print("-" * 60)
        print(preview)
        if len(data.transcript_text) > 500:
            print("...")
    else:
        print("\nNo transcript available for this video.")

    if data.description:
        preview = data.description[:300]
        print(f"\nDescription Preview:")
        print("-" * 60)
        print(preview)
        if len(data.description) > 300:
            print("...")


if __name__ == "__main__":
    asyncio.run(_run())
