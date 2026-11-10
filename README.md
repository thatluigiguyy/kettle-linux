# Kettle Linux

![Kettle Linux wallpaper](kettle-os/branding/preview.png)

A homemade Linux distribution, built step by step.

## Download

Grab the newest `.iso` from **[Releases](../../releases)**.

Boot it in VirtualBox:

1. **New** VM. Pick type **Linux** and version **Debian (64-bit)**.
2. Give it **4 GB RAM** and **2 or more CPUs**.
3. Under **Display**, set the graphics controller to **VMSVGA** and video memory to **128 MB**.
4. Under **System**, tick **Enable EFI**.
5. Attach the `.iso` as the optical drive, then **Start**.

## What's inside

| Folder | What it is |
| --- | --- |
| [`kettle-os/`](kettle-os) | **Kettle Linux 1.0 "Rolling Boil"**: Debian 13 + KDE Plasma 6 with Kettle's own wallpaper, logo, floating dock, splash screens and theme. It's built automatically by GitHub Actions. |
| [`rootfs/`](rootfs), `build.ps1` | **Kettle Linux 0.1 "First Boil"**: a tiny Linux (kernel + BusyBox) with a hand-made init system and the `kettle` command. |

## Building

Every push to `main` that changes `kettle-os/` builds a fresh ISO and publishes it as a release.
To build by hand on Debian/WSL, run `bash kettle-os/build.sh`.
