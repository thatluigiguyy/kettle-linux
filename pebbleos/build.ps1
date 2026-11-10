# Builds build\pebble.img: a 1.44 MB floppy image (boot sector + kernel)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot

function Find-Tool($name, $candidates, $hint) {
    $c = Get-Command $name -ErrorAction SilentlyContinue
    if ($c) { return $c.Source }
    foreach ($p in $candidates) { if (Test-Path $p) { return $p } }
    throw "$name not found. Install it with: $hint"
}

$nasm = Find-Tool 'nasm' @(
    "$env:ProgramFiles\NASM\nasm.exe",
    "${env:ProgramFiles(x86)}\NASM\nasm.exe",
    "$env:LOCALAPPDATA\bin\NASM\nasm.exe"
) 'winget install NASM.NASM'

New-Item -ItemType Directory -Force "$root\build" | Out-Null

& $nasm -f bin "$root\boot.asm" -o "$root\build\boot.bin"
if ($LASTEXITCODE) { throw 'boot.asm failed to assemble' }
& $nasm -f bin "$root\kernel.asm" -o "$root\build\kernel.bin"
if ($LASTEXITCODE) { throw 'kernel.asm failed to assemble' }

$img  = New-Object byte[] 1474560
$boot = [IO.File]::ReadAllBytes("$root\build\boot.bin")
$kern = [IO.File]::ReadAllBytes("$root\build\kernel.bin")
[Array]::Copy($boot, 0, $img, 0, $boot.Length)
[Array]::Copy($kern, 0, $img, 512, $kern.Length)
[IO.File]::WriteAllBytes("$root\build\pebble.img", $img)

Write-Host "Built build\pebble.img (boot: $($boot.Length) bytes, kernel: $($kern.Length) bytes)"
