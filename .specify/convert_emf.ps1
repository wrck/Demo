# Convert all EMF files in a folder to PNG using .NET System.Drawing
param(
    [string]$InputDir = "C:\Users\user\AppData\Local\Temp\offimg_out",
    [string]$OutputDir = "C:\Users\user\AppData\Local\Temp\offimg_out\png"
)
Add-Type -AssemblyName System.Drawing
if (-not (Test-Path $OutputDir)) { New-Item -ItemType Directory -Path $OutputDir | Out-Null }
$emfFiles = Get-ChildItem -Path $InputDir -Filter "*.emf" -File
Write-Host "Found $($emfFiles.Count) EMF files"
foreach ($f in $emfFiles) {
    $outName = [System.IO.Path]::GetFileNameWithoutExtension($f.Name) + ".png"
    $outPath = Join-Path $OutputDir $outName
    try {
        $emf = New-Object System.Drawing.Imaging.Metafile($f.FullName)
        # Scale up for readability (2x)
        $scale = 2
        $w = [int]($emf.Width * $scale)
        $h = [int]($emf.Height * $scale)
        if ($w -gt 8000) { $w = 8000 }
        if ($h -gt 8000) { $h = 8000 }
        $bmp = New-Object System.Drawing.Bitmap($w, $h)
        $bmp.SetResolution(300, 300)
        $g = [System.Drawing.Graphics]::FromImage($bmp)
        $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
        $g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
        $g.Clear([System.Drawing.Color]::White)
        $g.DrawImage($emf, 0, 0, $w, $h)
        $bmp.Save($outPath, [System.Drawing.Imaging.ImageFormat]::Png)
        $g.Dispose(); $bmp.Dispose(); $emf.Dispose()
        Write-Host "OK $($f.Name) -> $outName ($w x $h)"
    } catch {
        Write-Host "FAIL $($f.Name): $($_.Exception.Message)"
    }
}
Write-Host "DONE"
