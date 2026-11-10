# Boots the newest Kettle Linux ISO from kettle-os\out\ in QEMU
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot

$iso = Get-ChildItem "$root\out\*.iso" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime | Select-Object -Last 1
if (-not $iso) { throw 'No ISO found in out\. Build one first: in WSL, run  bash build.sh' }

$qemu = "$env:ProgramFiles\qemu\qemu-system-x86_64.exe"
if (-not (Test-Path $qemu)) { throw 'QEMU not found. Install it with: winget install SoftwareFreedomConservancy.QEMU' }

# A virtual disk so the installed system (later) has somewhere to live
$disk = "$root\out\kettle-disk.qcow2"
if (-not (Test-Path $disk)) { & "$env:ProgramFiles\qemu\qemu-img.exe" create -f qcow2 $disk 30G | Out-Null }

Write-Host "Booting $($iso.Name) ..."
& $qemu -name 'Kettle Linux' `
    -accel whpx,kernel-irqchip=off -accel tcg `
    -machine q35 -cpu max -smp 2 -m 3072 `
    -device virtio-vga -display sdl `
    -device qemu-xhci -device usb-tablet `
    -nic user,model=virtio-net-pci `
    -audiodev dsound,id=snd -device intel-hda -device hda-duplex,audiodev=snd `
    -drive "file=$disk,if=virtio" `
    -cdrom $iso.FullName -boot d `
    -rtc base=localtime
