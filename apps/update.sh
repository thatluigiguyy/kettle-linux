#!/bin/sh
# Kettle Linux updater: downloads the newest Kettle Studio, Kettle Store, app runner
# and Kettle SDK from GitHub, and adds MP3 export. Run it with:  kettle-update
# (or, on a Kettle that doesn't have kettle-update yet:
#   curl -fsSL https://raw.githubusercontent.com/thatluigiguyy/kettle-linux/main/apps/update.sh | sudo sh )
set -e

if [ "$(id -u)" -ne 0 ]; then
    echo "Please run this with sudo."
    exit 1
fi

BASE="https://raw.githubusercontent.com/thatluigiguyy/kettle-linux/main/apps"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "Downloading the newest Kettle tools..."
for f in common.py run.py sdk.py store.py studio.py templates.py ui.py; do
    curl -fsSL "$BASE/kettle/$f" -o "$TMP/$f"
done
for f in kettle-run kettle-store kettle-studio kettle-update; do
    curl -fsSL "$BASE/bin/$f" -o "$TMP/$f"
done

mkdir -p /usr/lib/kettle
install -m 644 "$TMP"/*.py /usr/lib/kettle/
install -m 755 "$TMP/kettle-run" "$TMP/kettle-store" "$TMP/kettle-studio" "$TMP/kettle-update" /usr/bin/

if ! command -v lame >/dev/null 2>&1; then
    echo "Adding MP3 export..."
    apt-get update -qq
    apt-get install -y -qq lame
fi

echo "Kettle is up to date!"
