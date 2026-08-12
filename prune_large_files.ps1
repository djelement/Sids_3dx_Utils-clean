<#
prune_large_files.ps1
Lists large files in the repo (default > 10 MB) and optionally moves them to ../vendor_binaries
Usage examples:
  # show large files (default threshold 10 MB)
  .\prune_large_files.ps1

  # move files > 50 MB to ../vendor_binaries (won't delete)
  .\prune_large_files.ps1 -ThresholdMB 50 -Action move

  # preview only (no changes)
  .\prune_large_files.ps1 -WhatIf
#>
param(
    [int]$ThresholdMB = 10,
    [ValidateSet('list','move','delete')]
    [string]$Action = 'list'
)
$root = (Get-Location).Path
$files = Get-ChildItem -Recurse -File | Where-Object { ($_.Length/1MB) -ge $ThresholdMB } | Sort-Object Length -Descending
if (-not $files) {
    Write-Host "No files >= ${ThresholdMB}MB found."
    exit 0
}
Write-Host "Files >= ${ThresholdMB}MB:`n" -ForegroundColor Cyan
$files | ForEach-Object { Write-Host ("{0:N2} MB - {1}" -f ($_.Length/1MB), $_.FullName) }

if ($Action -eq 'list') { exit 0 }

$destRoot = Join-Path $root "..\vendor_binaries"
if ($Action -eq 'move') {
    if (-not (Test-Path $destRoot)) { New-Item -ItemType Directory -Path $destRoot | Out-Null }
    foreach ($f in $files) {
        $rel = $f.FullName.Substring($root.Length+1)
        $t = Join-Path $destRoot $rel
        $tdir = Split-Path $t -Parent
        if (-not (Test-Path $tdir)) { New-Item -ItemType Directory -Path $tdir -Force | Out-Null }
        Write-Host "Moving $($f.FullName) -> $t"
        Move-Item -LiteralPath $f.FullName -Destination $t -Force
    }
    Write-Host "Moved files to: $destRoot"
} elseif ($Action -eq 'delete') {
    foreach ($f in $files) {
        Write-Host "Deleting $($f.FullName)"
        Remove-Item -LiteralPath $f.FullName -Force
    }
    Write-Host "Deleted listed files."
}
