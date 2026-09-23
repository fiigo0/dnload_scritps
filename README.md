# YouTube Downloader

Download YouTube videos and audio from a list of URLs. Produces MP4 video and MP3 audio files.

## Requirements

- Python 3.9+
- ffmpeg — installed automatically by `setup.py`
- Node.js — installed automatically by `setup.py` (needed by yt-dlp for some YouTube formats)

## Quick start

```bash
python3 setup.py --install
```

Add URLs to `urls.txt` (one per line), then:

```bash
python3 downloader.py
```

Files land in `downloads/` next to the scripts.

---

## setup.py

Manages all dependencies. Run it whenever something breaks or you need to update.

| Flag | What it does |
|------|-------------|
| `--install` | Install ffmpeg, Node.js, and all Python packages |
| `--update` | Upgrade all Python packages to latest versions |
| `--self-update` | Run yt-dlp's own update mechanism |
| `--check` | Verify all dependencies are present (default) |

```bash
# First-time setup
python3 setup.py --install

# Check health
python3 setup.py --check

# Update everything
python3 setup.py --update

# Fix a broken yt-dlp
python3 setup.py --self-update
```

---

## downloader.py

| Flag | Default | Description |
|------|---------|-------------|
| `--urls-file` / `-f` | `urls.txt` | Path to the URL list file |
| `--mode` / `-m` | `both` | `video` (MP4), `audio` (MP3), or `both` |
| `--output-dir` / `-o` | `downloads/` | Where to save files |
| `--quality` / `-q` | `best` | `best`, `1080`, `720`, `480`, `360` |
| `--delay` / `-d` | `1.0` | Seconds between downloads |

```bash
# Download both MP4 and MP3 (default)
python3 downloader.py

# Download video only
python3 downloader.py --mode video

# Download audio only (MP3)
python3 downloader.py --mode audio

# Download 720p from a custom list
python3 downloader.py --urls-file my_list.txt --quality 720

# Increase delay to avoid rate limiting
python3 downloader.py --delay 3
```

### How `both` mode works

Runs two passes per URL:

1. **Video pass** — downloads best quality merged MP4
2. **Audio pass** — extracts MP3 from the cached video (no re-download)

Both `Title.mp4` and `Title.mp3` are saved to the output directory.

---

## urls.txt format

```
# Lines starting with # are ignored
https://www.youtube.com/watch?v=...
https://www.youtube.com/playlist?list=...
https://youtu.be/...
```

Playlist URLs are supported and download all videos in the playlist.

---

## Output

Files are saved as `<uploader> - <title>.<ext>` inside the output directory.

Logs are written to `logs/` on every run:
- `downloader_YYYYMMDD_HHMMSS.log` — one file per downloader run
- `setup.log` — appended on every setup run
