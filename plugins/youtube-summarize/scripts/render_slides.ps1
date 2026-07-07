<#
  render_slides.ps1 — .pptx 각 슬라이드를 PNG 로 export (PowerPoint COM)
  build_video.py 가 호출한다. 보호된 보기 hang 회피를 위해 %TEMP% 로 복사 후 연다.
#>
param(
  [Parameter(Mandatory=$true)][string]$Src,
  [Parameter(Mandatory=$true)][string]$OutDir,
  [int]$Width = 1754,
  [int]$Height = 1240
)
$ErrorActionPreference = 'Stop'

$tmp = Join-Path $env:TEMP ("vid_" + [System.IO.Path]::GetFileName($Src))
Copy-Item -LiteralPath $Src -Destination $tmp -Force

if (Test-Path $OutDir) { Remove-Item $OutDir -Recurse -Force }
New-Item -ItemType Directory -Path $OutDir | Out-Null

$pp = New-Object -ComObject PowerPoint.Application
try {
  $ro = [Microsoft.Office.Core.MsoTriState]::msoTrue
  $no = [Microsoft.Office.Core.MsoTriState]::msoFalse
  $pres = $pp.Presentations.Open($tmp, $ro, $no, $no)
  $i = 1
  foreach ($s in $pres.Slides) {
    $s.Export((Join-Path $OutDir ("slide-$i.png")), 'PNG', $Width, $Height)
    $i++
  }
  $pres.Close()
  Write-Output "Exported $($i-1) slides to $OutDir"
} finally {
  $pp.Quit()
  Remove-Item $tmp -Force -ErrorAction SilentlyContinue
}
