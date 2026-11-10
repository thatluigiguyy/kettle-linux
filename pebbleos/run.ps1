# Builds PebbleOS and boots it in a QEMU virtual PC
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot

& "$root\build.ps1"

$qemu = (Get-Command 'qemu-system-i386' -ErrorAction SilentlyContinue).Source
if (-not $qemu) {
    foreach ($p in "$env:ProgramFiles\qemu\qemu-system-i386.exe", "$env:ProgramFiles\qemu\qemu-system-x86_64.exe") {
        if (Test-Path $p) { $qemu = $p; break }
    }
}
if (-not $qemu) { throw 'QEMU not found. Install it with: winget install SoftwareFreedomConservancy.QEMU' }

& $qemu -name PebbleOS -drive "format=raw,file=$root\build\pebble.img,if=floppy" -boot a -rtc base=localtime
