#!/usr/bin/env bash
# =====================================================================
#  Builds the Kettle Linux ISO.  Run inside WSL (Debian):
#      bash build.sh
#  Takes 30-60 minutes the first time (it downloads ~1.5 GB of packages).
#  The finished ISO is copied to kettle-os/out/.
# =====================================================================
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="$HOME/kettle-build"          # build on the Linux disk: much faster than /mnt/c
OUT="$SRC/out"
INC="$WORK/config/includes.chroot"

step() { printf '\n\033[1;33m==> %s\033[0m\n' "$1"; }

# inside the GitHub build container we are already root and there is no sudo
if [ "$(id -u)" -eq 0 ]; then sudo() { "$@"; }; fi

step "Installing build tools"
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update
sudo apt-get install -y live-build debootstrap librsvg2-bin xorriso squashfs-tools rsync ca-certificates

step "Copying the Kettle recipe to $WORK"
mkdir -p "$WORK"
rsync -a --delete "$SRC/auto/"     "$WORK/auto/"
rsync -a --delete "$SRC/config/"   "$WORK/config/"
rsync -a --delete "$SRC/branding/" "$WORK/branding/"
# files edited on Windows may have CRLF line endings; Linux needs LF
find "$WORK/auto" "$WORK/config" -type f \( -name '*.png' -o -name '*.jpg' \) -prune -o -type f -exec sed -i 's/\r$//' {} +
chmod +x "$WORK"/auto/* "$WORK"/config/hooks/normal/*

step "Rendering wallpaper, logo and splash"
WP="$INC/usr/share/wallpapers/Kettle/contents"
LNF="$INC/usr/share/plasma/look-and-feel/org.kettle.desktop/contents"
mkdir -p "$WP/images" "$LNF/previews" "$INC/usr/share/icons/hicolor/scalable/apps" "$INC/usr/share/pixmaps" "$INC/usr/share/kettle"
for size in 3840x2160 2560x1440 1920x1080; do
    rsvg-convert -w "${size%x*}" -h "${size#*x}" "$WORK/branding/wallpaper.svg" -o "$WP/images/$size.png"
done
rsvg-convert -w 640 -h 360 "$WORK/branding/wallpaper.svg" -o "$WP/screenshot.png"
cp "$WP/screenshot.png" "$LNF/previews/preview.png"
cp "$WP/screenshot.png" "$LNF/previews/fullscreenpreview.jpg"
cp "$WORK/branding/kettle-logo.svg" "$INC/usr/share/icons/hicolor/scalable/apps/kettle-logo.svg"
cp "$WORK/branding/kettle-logo.svg" "$INC/usr/share/pixmaps/kettle-logo.svg"
rsvg-convert -w 160 -h 160 "$WORK/branding/kettle-logo.svg" -o "$INC/usr/share/kettle/kettle-splash.png"

step "Adding Kettle Studio and the Kettle Store"
APPS="$SRC/../apps"
install -d "$INC/usr/lib/kettle" "$INC/usr/bin" "$INC/usr/share/applications" \
           "$INC/usr/share/icons/hicolor/scalable/apps"
install -m 644 "$APPS"/kettle/*.py          "$INC/usr/lib/kettle/"
install -m 755 "$APPS"/bin/*                "$INC/usr/bin/"
install -m 644 "$APPS"/desktop/*.desktop    "$INC/usr/share/applications/"
install -m 644 "$APPS"/icons/*.svg          "$INC/usr/share/icons/hicolor/scalable/apps/"
sed -i 's/\r$//' "$INC"/usr/lib/kettle/*.py "$INC"/usr/bin/kettle-* "$INC"/usr/share/applications/org.kettle.*

step "Building the ISO (grab a cup of tea...)"
cd "$WORK"
sudo lb clean
lb config
sudo lb build

step "Copying the ISO back to Windows"
mkdir -p "$OUT"
cp -v "$WORK"/*.iso "$OUT/"
ls -lh "$OUT"
printf '\n\033[1;32mDone!\033[0m\n'
