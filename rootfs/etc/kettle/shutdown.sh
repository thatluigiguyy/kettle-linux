#!/bin/sh
# Runs when you type poweroff or reboot
printf '\n  \033[1;33mKettle is cooling down... bye!\033[0m\n'
sync
umount -a -r 2>/dev/null
