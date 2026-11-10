#!/bin/sh
# Kettle Linux boot script: runs once at startup (sysinit in /etc/inittab)

. /etc/os-release

ok() { printf '  [\033[1;32m OK \033[0m] %s\n' "$1"; }

clear
printf '\033[1;33m'
cat /etc/kettle/logo
printf '\033[0m\n'
printf '  Booting \033[1m%s\033[0m\n\n' "$PRETTY_NAME"

ok "Mounted /proc, /sys, /dev, /tmp and /run"

hostname -F /etc/hostname && ok "Set hostname to $(hostname)"

ip link set lo up 2>/dev/null && ok "Brought up loopback network"

mkdir -p /root /home /var/log
dmesg > /var/log/boot.log 2>/dev/null && ok "Saved kernel log to /var/log/boot.log"

ok "Running Linux $(uname -r) with $(busybox --list | wc -l) BusyBox tools"
ok "Kettle has boiled. Ready!"
echo
