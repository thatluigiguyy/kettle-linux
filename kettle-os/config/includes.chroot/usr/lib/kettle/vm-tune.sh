#!/bin/sh
# Kettle Linux: runs once per user at login.
# Inside a virtual machine there is no real graphics card, so the screen is drawn by
# the CPU. Blur and long animations then make everything laggy, so turn them down.
# On real hardware this does nothing.

virt="$(systemd-detect-virt 2>/dev/null || echo none)"
[ "$virt" = none ] && exit 0

done_flag="$HOME/.config/kettle-vm-tuned"
[ -f "$done_flag" ] && exit 0

kwriteconfig6 --file kwinrc --group Plugins --key blurEnabled false
kwriteconfig6 --file kwinrc --group Plugins --key contrastEnabled false
kwriteconfig6 --file kwinrc --group Plugins --key slidingpopupsEnabled false
kwriteconfig6 --file kdeglobals --group KDE --key AnimationDurationFactor 0.4
# the file search indexer reads every file in the background: heavy in a VM
kwriteconfig6 --file baloofilerc --group "Basic Settings" --key "Indexing-Enabled" false
balooctl6 disable >/dev/null 2>&1 || true

# apply to the running desktop right away
qdbus6 org.kde.KWin /KWin reconfigure >/dev/null 2>&1 || true

mkdir -p "$HOME/.config"
echo "$virt" > "$done_flag"
