#!/usr/bin/env python3
"""
Setup & Self-Update Script
Installs, verifies, and updates all dependencies for the downloader.
Usage: python setup.py [--install] [--update] [--check]
"""

import argparse
import logging
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "setup.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Required packages
# ---------------------------------------------------------------------------
REQUIRED_PACKAGES = [
    "yt-dlp",
]

PYTHON_MIN = (3, 9)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(cmd: list[str], capture: bool = False) -> subprocess.CompletedProcess:
    log.debug("Running: %s", " ".join(cmd))
    result = subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
    )
    return result


def pip(*args: str) -> subprocess.CompletedProcess:
    return run([sys.executable, "-m", "pip", *args])


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_python() -> bool:
    current = sys.version_info[:2]
    ok = current >= PYTHON_MIN
    status = "OK" if ok else "FAIL"
    log.info("[%s] Python %s (need >= %s)", status, ".".join(map(str, current)), ".".join(map(str, PYTHON_MIN)))
    if not ok:
        log.error("Please upgrade Python to %s or newer.", ".".join(map(str, PYTHON_MIN)))
    return ok


def install_ffmpeg() -> bool:
    """Attempt to install ffmpeg using the platform's package manager."""
    log.info("Installing ffmpeg…")
    system = platform.system()

    if system == "Darwin":
        if shutil.which("brew"):
            result = run(["brew", "install", "ffmpeg"])
        else:
            log.error("Homebrew not found. Install it from https://brew.sh, then re-run --install.")
            return False
    elif system == "Linux":
        # Try apt-get first, then dnf, then pacman
        for mgr, cmd in [
            ("apt-get", ["sudo", "apt-get", "install", "-y", "ffmpeg"]),
            ("dnf",     ["sudo", "dnf",     "install", "-y", "ffmpeg"]),
            ("pacman",  ["sudo", "pacman",  "-S",  "--noconfirm", "ffmpeg"]),
        ]:
            if shutil.which(mgr):
                result = run(cmd)
                break
        else:
            log.error("No supported package manager found (apt-get / dnf / pacman).")
            return False
    elif system == "Windows":
        if shutil.which("winget"):
            result = run(["winget", "install", "--id", "Gyan.FFmpeg", "-e", "--silent"])
        elif shutil.which("choco"):
            result = run(["choco", "install", "ffmpeg", "-y"])
        else:
            log.error(
                "Neither winget nor Chocolatey found.\n"
                "  Install ffmpeg manually from https://ffmpeg.org/download.html\n"
                "  or install Chocolatey from https://chocolatey.org and re-run --install."
            )
            return False
    else:
        log.error("Unsupported OS: %s. Install ffmpeg manually.", system)
        return False

    if result.returncode == 0:
        log.info("[OK] ffmpeg installed successfully.")
        return True
    log.error("[FAIL] ffmpeg installation failed (exit %d).", result.returncode)
    return False


def check_ffmpeg() -> bool:
    path = shutil.which("ffmpeg")
    if path:
        result = run(["ffmpeg", "-version"], capture=True)
        version_line = result.stdout.splitlines()[0] if result.stdout else "unknown"
        log.info("[OK] ffmpeg found: %s (%s)", path, version_line)
        return True
    log.warning("[MISS] ffmpeg not found — audio extraction and video merging will not work.")
    return False


def check_package(name: str) -> bool:
    result = run([sys.executable, "-m", "pip", "show", name], capture=True)
    if result.returncode == 0:
        for line in result.stdout.splitlines():
            if line.startswith("Version:"):
                version = line.split(":", 1)[1].strip()
                log.info("[OK] %s %s", name, version)
                break
        return True
    log.warning("[MISS] %s is not installed.", name)
    return False


def _install_node() -> bool:
    """Attempt to install Node.js using the platform's package manager."""
    system = platform.system()
    if system == "Darwin":
        if shutil.which("brew"):
            result = run(["brew", "install", "node"])
        else:
            log.warning("Homebrew not found; skipping node install. Install from https://nodejs.org")
            return False
    elif system == "Linux":
        for mgr, cmd in [
            ("apt-get", ["sudo", "apt-get", "install", "-y", "nodejs"]),
            ("dnf",     ["sudo", "dnf",     "install", "-y", "nodejs"]),
            ("pacman",  ["sudo", "pacman",  "-S", "--noconfirm", "nodejs"]),
        ]:
            if shutil.which(mgr):
                result = run(cmd)
                break
        else:
            log.warning("No supported package manager found; skipping node install.")
            return False
    elif system == "Windows":
        if shutil.which("winget"):
            result = run(["winget", "install", "--id", "OpenJS.NodeJS", "-e", "--silent"])
        elif shutil.which("choco"):
            result = run(["choco", "install", "nodejs", "-y"])
        else:
            log.warning("No package manager found; install Node.js from https://nodejs.org")
            return False
    else:
        log.warning("Unsupported OS: %s; install Node.js manually.", system)
        return False

    if result.returncode == 0:
        log.info("[OK] node installed.")
        return True
    log.warning("[WARN] node installation failed (exit %d).", result.returncode)
    return False


def check_js_runtime() -> bool:
    """yt-dlp needs a JS runtime (node or deno) for some YouTube formats."""
    for runtime in ("node", "deno"):
        path = shutil.which(runtime)
        if path:
            result = run([runtime, "--version"], capture=True)
            version = (result.stdout or result.stderr).strip().splitlines()[0]
            log.info("[OK] JS runtime found: %s (%s)", path, version)
            return True
    log.warning(
        "[WARN] No JS runtime found (node or deno). Some YouTube formats may be missing.\n"
        "  macOS:   brew install node\n"
        "  Ubuntu:  sudo apt install nodejs\n"
        "  Windows: https://nodejs.org"
    )
    return False


def check_all() -> dict[str, bool]:
    log.info("─" * 50)
    log.info("Dependency check")
    log.info("─" * 50)

    results = {
        "python": check_python(),
        "ffmpeg": check_ffmpeg(),
        "js-runtime": check_js_runtime(),
    }
    for pkg in REQUIRED_PACKAGES:
        results[pkg] = check_package(pkg)

    log.info("─" * 50)
    # js-runtime is optional — don't block on it
    blocking = {k: v for k, v in results.items() if k != "js-runtime"}
    all_ok = all(blocking.values())
    if all_ok:
        log.info("All required dependencies satisfied.")
    else:
        missing = [k for k, v in blocking.items() if not v]
        log.warning("Issues found: %s", ", ".join(missing))
    return results


# ---------------------------------------------------------------------------
# Install / Update
# ---------------------------------------------------------------------------

def install_packages() -> None:
    log.info("─" * 50)
    log.info("Installing packages")
    log.info("─" * 50)

    # Install ffmpeg if missing
    if not shutil.which("ffmpeg"):
        install_ffmpeg()
    else:
        log.info("[OK] ffmpeg already present, skipping.")

    # Install node if no JS runtime is present (needed by yt-dlp for some YouTube formats)
    if not shutil.which("node") and not shutil.which("deno"):
        log.info("No JS runtime found — installing node…")
        _install_node()
    else:
        log.info("[OK] JS runtime already present, skipping.")

    log.info("Upgrading pip…")
    pip("install", "--upgrade", "pip")

    for pkg in REQUIRED_PACKAGES:
        log.info("Installing %s…", pkg)
        result = pip("install", pkg)
        if result.returncode == 0:
            log.info("[OK] %s installed successfully.", pkg)
        else:
            log.error("[FAIL] Could not install %s.", pkg)


def update_packages() -> None:
    log.info("─" * 50)
    log.info("Updating packages")
    log.info("─" * 50)

    log.info("Upgrading pip…")
    pip("install", "--upgrade", "pip")

    for pkg in REQUIRED_PACKAGES:
        log.info("Updating %s…", pkg)
        result = pip("install", "--upgrade", pkg)
        if result.returncode == 0:
            # Print new version
            check_package(pkg)
            log.info("[OK] %s updated.", pkg)
        else:
            log.error("[FAIL] Could not update %s.", pkg)


def update_self() -> None:
    """Update yt-dlp binary via its own self-update mechanism if available."""
    log.info("─" * 50)
    log.info("Self-updating yt-dlp")
    log.info("─" * 50)

    # yt-dlp supports `yt-dlp -U` for self-update when installed as a binary,
    # but when installed via pip we just upgrade the package.
    ytdlp = shutil.which("yt-dlp")
    if ytdlp:
        log.info("Running yt-dlp -U via binary at %s", ytdlp)
        result = run([ytdlp, "-U"])
        if result.returncode == 0:
            log.info("[OK] yt-dlp self-update complete.")
        else:
            log.warning("yt-dlp -U returned non-zero; falling back to pip upgrade.")
            pip("install", "--upgrade", "yt-dlp")
    else:
        log.info("yt-dlp binary not on PATH; upgrading via pip.")
        pip("install", "--upgrade", "yt-dlp")


def create_sample_urls() -> None:
    sample = Path("urls.txt")
    if sample.exists():
        log.info("urls.txt already exists, skipping sample creation.")
        return
    sample.write_text(
        "# Add one YouTube URL per line (lines starting with # are comments)\n"
        "# Example:\n"
        "# https://www.youtube.com/watch?v=dQw4w9WgXcQ\n",
        encoding="utf-8",
    )
    log.info("Created sample urls.txt — add your URLs there.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Set up and update downloader dependencies.")
    parser.add_argument("--install", action="store_true", help="Install all required Python packages")
    parser.add_argument("--update", action="store_true", help="Upgrade all Python packages to latest versions")
    parser.add_argument("--self-update", action="store_true", help="Run yt-dlp self-update mechanism")
    parser.add_argument("--check", action="store_true", help="Check that all dependencies are present")
    args = parser.parse_args()

    # Default to --check when no flag given
    if not any([args.install, args.update, args.self_update, args.check]):
        args.check = True

    log.info("=" * 50)
    log.info("Downloader Setup")
    log.info("=" * 50)

    if args.install:
        install_packages()
        create_sample_urls()

    if args.update:
        update_packages()

    if args.self_update:
        update_self()

    if args.check or args.install or args.update:
        results = check_all()
        if not all(results.values()):
            log.info("Run  python setup.py --install  to install missing packages.")
            sys.exit(1)

    log.info("Setup complete.")


if __name__ == "__main__":
    main()
