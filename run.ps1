# Builds Kettle Linux and boots it in a QEMU virtual PC
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot

& "$root\build.ps1"

$qemu = (Get-Command 'qemu-system-x86_64' -ErrorAction SilentlyContinue).Source
if (-not $qemu -and (Test-Path "$env:ProgramFiles\qemu\qemu-system-x86_64.exe")) {
    $qemu = "$env:ProgramFiles\qemu\qemu-system-x86_64.exe"
}
if (-not $qemu) { throw 'QEMU not found. Install it with: winget install SoftwareFreedomConservancy.QEMU' }

& $qemu -name 'Kettle Linux' -m 512 `
    -kernel "$root\build\vmlinuz" `
    -initrd "$root\build\kettle.cpio.gz" `
    -append 'quiet loglevel=3' `
    -rtc base=localtime
