#!/bin/bash
# Double-click this file in Finder to run the downloader.
# On first run it will install all dependencies automatically.

# Always run from the folder where this script lives
cd "$(dirname "$0")"

echo "============================================================"
echo " YouTube Downloader"
echo "============================================================"
echo ""

# Auto-install dependencies if yt-dlp is missing
if ! python3 -c "import yt_dlp" 2>/dev/null; then
    echo "First run — installing dependencies..."
    echo ""
    python3 setup.py --install
    echo ""
fi

# Run the downloader
python3 downloader.py

echo ""
echo "============================================================"
echo " Done. Press any key to close this window."
echo "============================================================"
read -n 1 -s
