"""Tool: fetch YouTube video transcripts, with Whisper fallback for videos without captions."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import httpx

from agent_framework import tool

from deep_research.config import get_settings
from deep_research.log import log


@tool
def youtube_transcript(video_id: str) -> str:
    """Fetch transcript from a YouTube video. Tries auto-captions first, falls back to Whisper.

    Args:
        video_id: YouTube video ID (e.g. 'dQw4w9WgXcQ' from youtube.com/watch?v=dQw4w9WgXcQ)
    """
    # Try captions first (free, fast)
    transcript = _fetch_captions(video_id)
    if transcript:
        return transcript

    # Fallback: download audio + Whisper
    log.info("No captions for %s, trying Whisper...", video_id)
    transcript = _whisper_transcribe(video_id)
    if transcript:
        return transcript

    return json.dumps({"error": f"Could not get transcript for {video_id}"})


@tool
def youtube_search(query: str, max_results: int = 5) -> str:
    """Search YouTube for videos and return titles, IDs, and descriptions."""
    try:
        resp = httpx.get(
            "https://www.youtube.com/results",
            params={"search_query": query, "sp": "EgIQAQ=="},  # filter: videos only
            headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en"},
            timeout=15,
        )
        # Extract video IDs from page
        import re
        video_ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', resp.text)
        seen = []
        for vid in video_ids:
            if vid not in seen:
                seen.append(vid)
            if len(seen) >= max_results:
                break

        results = []
        for vid in seen:
            title_match = re.search(rf'"videoId":"{vid}".*?"title":\{{"runs":\[\{{"text":"(.*?)"', resp.text)
            title = title_match.group(1) if title_match else vid
            results.append({"video_id": vid, "title": title, "url": f"https://youtube.com/watch?v={vid}"})

        log.info("YouTube search '%s': %d results", query, len(results))
        return json.dumps({"results": results})
    except Exception as e:
        log.warning("YouTube search failed: %s", e)
        return json.dumps({"error": str(e), "results": []})


def _fetch_captions(video_id: str) -> str | None:
    """Try to get transcript via youtube-transcript-api."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id)
        text = " ".join([s.text for s in transcript])
        log.info("YouTube captions for %s: %d chars", video_id, len(text))
        return json.dumps({
            "video_id": video_id,
            "source": "captions",
            "text": text[:15000],  # cap to avoid token explosion
            "total_chars": len(text),
        })
    except Exception as e:
        log.debug("Captions unavailable for %s: %s", video_id, e)
        return None


def _whisper_transcribe(video_id: str) -> str | None:
    """Download audio with yt-dlp and transcribe with Azure Whisper."""
    settings = get_settings()

    # Download audio
    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = Path(tmpdir) / "audio.m4a"
        try:
            proc = subprocess.run(
                ["yt-dlp", "-x", "--audio-format", "m4a", "-o", str(audio_path),
                 f"https://youtube.com/watch?v={video_id}"],
                capture_output=True, text=True, timeout=120,
            )
            if proc.returncode != 0 or not audio_path.exists():
                log.warning("yt-dlp failed for %s: %s", video_id, proc.stderr[:200])
                return None
        except (subprocess.TimeoutExpired, FileNotFoundError):
            log.warning("yt-dlp not available or timed out")
            return None

        # Send to Azure Whisper
        try:
            endpoint = (
                "https://kustoassistant.cognitiveservices.azure.com"
                "/openai/deployments/whisper/audio/translations?api-version=2024-06-01"
            )
            with open(audio_path, "rb") as f:
                resp = httpx.post(
                    endpoint,
                    headers={"api-key": settings.azure_api_key},
                    files={"file": ("audio.m4a", f, "audio/m4a")},
                    timeout=300,
                )
            resp.raise_for_status()
            text = resp.json().get("text", "")
            log.info("Whisper transcribed %s: %d chars", video_id, len(text))
            return json.dumps({
                "video_id": video_id,
                "source": "whisper",
                "text": text[:15000],
                "total_chars": len(text),
            })
        except Exception as e:
            log.warning("Whisper failed for %s: %s", video_id, e)
            return None
