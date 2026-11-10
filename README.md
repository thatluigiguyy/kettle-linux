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
| [`apps/`](apps) | **Kettle Studio**, an app maker with a code editor and a live preview that updates as you type, and the **Kettle Store**, where you install and remix apps other people published. |
| [`rootfs/`](rootfs), `build.ps1` | **Kettle Linux 0.1 "First Boil"**: a tiny Linux (kernel + BusyBox) with a hand-made init system and the `kettle` command. |

## Making and sharing apps

Open **Kettle Studio** from the dock, pick a template (Hello, Counter, Clock, Paint, Tea Timer or Blank) and start typing. The preview on the right updates as you go. Kettle apps are written in [QML](https://doc.qt.io/qt-6/qmlapplications.html), the same language KDE apps use.

To share an app, press **Publish**. It goes to `github.com/<you>/kettle-app-<name>` with the topic `kettle-app`, and every app with that topic shows up in the **Kettle Store**. There, anyone can install it, open it, or **Remix** it into their own copy.

## Building

Every push to `main` that changes `kettle-os/` builds a fresh ISO and publishes it as a release.
To build by hand on Debian/WSL, run `bash kettle-os/build.sh`.
