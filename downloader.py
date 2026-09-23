#!/usr/bin/env python3
"""
YouTube Video & Audio Downloader
Downloads videos or audio from a list of URLs in a text file.
Usage: python downloader.py --urls-file urls.txt [options]
"""

import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
log_filename = LOG_DIR / f"downloader_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_filename, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


def check_dependencies() -> bool:
    try:
        import yt_dlp  # noqa: F401
        return True
    except ImportError:
        log.error("yt-dlp is not installed. Run: python setup.py --install")
        return False


def load_urls(path: str) -> list[str]:
    """Read non-empty, non-comment lines from a URL file."""
    file = Path(path)
    if not file.exists():
        log.error("URL file not found: %s", path)
        sys.exit(1)

    urls = []
    with open(file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)

    log.info("Loaded %d URL(s) from %s", len(urls), path)
    return urls


def _base_opts(output_dir: str) -> dict:
    """Shared yt-dlp options applied to every download."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    return {
        "outtmpl": str(Path(output_dir) / "%(uploader)s - %(title)s.%(ext)s"),
        "ignoreerrors": False,
        "noplaylist": False,
        "quiet": False,
        "no_warnings": False,
        "progress_hooks": [progress_hook],
        # android+web avoids both 403s and YouTube's SABR streaming experiment
        # that breaks the iOS client (https://github.com/yt-dlp/yt-dlp/issues/12482)
        "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
        # Pause between HTTP requests to reduce rate-limit errors
        "sleep_interval_requests": 1,
    }


def build_video_opts(output_dir: str, quality: str) -> dict:
    opts = _base_opts(output_dir)
    fmt = "bestvideo+bestaudio/best" if quality == "best" else f"bestvideo[height<={quality}]+bestaudio/best"
    opts.update({"format": fmt, "merge_output_format": "mp4"})
    return opts


def build_audio_opts(output_dir: str, keep_source: bool = False) -> dict:
    opts = _base_opts(output_dir)
    opts.update(
        {
            "format": "bestaudio/best",
            "keepvideo": keep_source,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }
    )
    return opts


def progress_hook(d: dict) -> None:
    if d["status"] == "downloading":
        pct = d.get("_percent_str", "?%").strip()
        speed = d.get("_speed_str", "?").strip()
        eta = d.get("_eta_str", "?").strip()
        log.debug("  Progress: %s  Speed: %s  ETA: %s", pct, speed, eta)
    elif d["status"] == "finished":
        log.info("  Download finished: %s", d.get("filename", ""))
    elif d["status"] == "error":
        log.error("  Download error for: %s", d.get("filename", "unknown"))


def download_url(ydl, url: str, index: int, total: int, label: str = "") -> bool:
    tag = f" [{label}]" if label else ""
    log.info("─" * 60)
    log.info("[%d/%d]%s Downloading: %s", index, total, tag, url)
    try:
        ydl.download([url])
        log.info("[%d/%d]%s Done: %s", index, total, tag, url)
        return True
    except Exception as exc:
        log.error("[%d/%d]%s Failed: %s — %s", index, total, tag, url, exc)
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Download YouTube videos or audio from a URL list.")
    parser.add_argument("--urls-file", "-f", default="urls.txt", help="Path to text file with URLs (default: urls.txt)")
    parser.add_argument(
        "--mode", "-m",
        choices=["video", "audio", "both"],
        default="both",
        help="Download mode: video, audio (mp3), or both (default: both)",
    )
    script_dir = Path(__file__).parent
    parser.add_argument(
        "--output-dir", "-o",
        default=str(script_dir / "downloads"),
        help="Output directory (default: <script folder>/downloads)",
    )
    parser.add_argument(
        "--quality", "-q",
        default="best",
        help="Video quality: best, 1080, 720, 480, 360 (default: best). Ignored in audio mode.",
    )
    parser.add_argument("--delay", "-d", type=float, default=1.0, help="Seconds to wait between downloads (default: 1)")
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("YouTube Downloader started")
    log.info("Mode: %s | Quality: %s | Output: %s", args.mode, args.quality, args.output_dir)
    log.info("Log file: %s", log_filename)
    log.info("=" * 60)

    if not check_dependencies():
        sys.exit(1)

    import yt_dlp

    urls = load_urls(args.urls_file)
    if not urls:
        log.warning("No URLs found in %s. Exiting.", args.urls_file)
        sys.exit(0)

    # Determine which passes to run
    passes: list[tuple[str, dict]] = []
    if args.mode in ("video", "both"):
        passes.append(("video", build_video_opts(args.output_dir, args.quality)))
    if args.mode in ("audio", "both"):
        passes.append(("audio", build_audio_opts(args.output_dir, keep_source=args.mode == "both")))

    success, failed = 0, 0

    for pass_label, ydl_opts in passes:
        if len(passes) > 1:
            log.info("=" * 60)
            log.info("Pass: %s", pass_label.upper())

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            for i, url in enumerate(urls, start=1):
                label = pass_label if len(passes) > 1 else ""
                ok = download_url(ydl, url, i, len(urls), label)
                if ok:
                    success += 1
                else:
                    failed += 1
                if i < len(urls) and args.delay > 0:
                    log.debug("Waiting %.1fs before next download…", args.delay)
                    time.sleep(args.delay)

    total_ops = len(urls) * len(passes)
    log.info("=" * 60)
    log.info("Finished. Success: %d  Failed: %d  Total: %d", success, failed, total_ops)
    log.info("Files saved to: %s", Path(args.output_dir).resolve())
    log.info("=" * 60)

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
