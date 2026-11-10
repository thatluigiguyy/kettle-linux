# =====================================================================
#  Kettle Linux builder
#  Packs rootfs\ + BusyBox into build\kettle.cpio.gz (the initramfs:
#  the whole OS, loaded into RAM at boot) and copies the kernel.
# =====================================================================
$ErrorActionPreference = 'Stop'
$root    = $PSScriptRoot
$rootfs  = Join-Path $root 'rootfs'
$out     = Join-Path $root 'build'
$busybox = Join-Path $root 'downloads\busybox'
$kernel  = Join-Path $root 'downloads\vmlinuz-virt'

foreach ($f in $busybox, $kernel) { if (-not (Test-Path $f)) { throw "Missing $f" } }
New-Item -ItemType Directory -Force $out | Out-Null

# ---- cpio "newc" archive writer (the format Linux expects) ----------
$script:ms    = New-Object IO.MemoryStream
$script:ino   = 1
$script:seen  = New-Object 'System.Collections.Generic.HashSet[string]'
$script:mtime = [int][double]::Parse((Get-Date -UFormat %s))

function Pad4 { while ($script:ms.Position % 4) { $script:ms.WriteByte(0) } }

function Add-Entry([string]$name, [int]$mode, [byte[]]$data = @(), [int]$rmaj = 0, [int]$rmin = 0) {
    if (-not $script:seen.Add($name)) { return }
    $nameBytes = [Text.Encoding]::ASCII.GetBytes($name + [char]0)
    $nlink = if (($mode -band 0xF000) -eq 0x4000) { 2 } else { 1 }
    $fields = $script:ino, $mode, 0, 0, $nlink, $script:mtime, $data.Length, 0, 0, $rmaj, $rmin, $nameBytes.Length, 0
    $hdr = [Text.Encoding]::ASCII.GetBytes('070701' + (($fields | ForEach-Object { '{0:X8}' -f $_ }) -join ''))
    $script:ms.Write($hdr, 0, $hdr.Length)
    $script:ms.Write($nameBytes, 0, $nameBytes.Length)
    Pad4
    if ($data.Length) { $script:ms.Write($data, 0, $data.Length) }
    Pad4
    $script:ino++
}

$DIR  = 0x41ED   # directory, rwxr-xr-x
$EXE  = 0x81ED   # file,      rwxr-xr-x
$FILE = 0x81A4   # file,      rw-r--r--

# ---- base directory layout ------------------------------------------
foreach ($d in 'bin','sbin','usr','usr/bin','usr/sbin','etc','etc/kettle','dev','proc','sys','run','root','home','var','var/log','mnt') {
    Add-Entry $d $DIR
}
Add-Entry 'tmp' 0x43FF                   # sticky, world-writable
Add-Entry 'dev/console' 0x2180 @() 5 1   # char device, so the kernel can talk to us before /dev is mounted
Add-Entry 'bin/busybox' $EXE ([IO.File]::ReadAllBytes($busybox))

# ---- Kettle's own files from rootfs\ --------------------------------
$items = Get-ChildItem $rootfs -Recurse | Sort-Object FullName
foreach ($item in $items) {
    $rel = $item.FullName.Substring($rootfs.Length + 1).Replace('\', '/')
    if ($item.PSIsContainer) { Add-Entry $rel $DIR; continue }
    $text = [IO.File]::ReadAllText($item.FullName).Replace("`r`n", "`n")
    $data = (New-Object Text.UTF8Encoding $false).GetBytes($text)
    $isExe = $rel -eq 'init' -or $rel -match '^(usr/)?s?bin/' -or $rel.EndsWith('.sh')
    Add-Entry $rel $(if ($isExe) { $EXE } else { $FILE }) $data
}
Add-Entry 'TRAILER!!!' 0

# ---- gzip it ---------------------------------------------------------
$initrd = Join-Path $out 'kettle.cpio.gz'
$fs = [IO.File]::Create($initrd)
$gz = New-Object IO.Compression.GZipStream($fs, [IO.Compression.CompressionLevel]::Optimal)
$bytes = $script:ms.ToArray()
$gz.Write($bytes, 0, $bytes.Length)
$gz.Dispose(); $fs.Dispose()

Copy-Item $kernel (Join-Path $out 'vmlinuz') -Force

$kb = [math]::Round((Get-Item $initrd).Length / 1KB)
Write-Host "Built Kettle Linux: build\vmlinuz + build\kettle.cpio.gz ($kb KB, $($script:ino - 1) files)"
