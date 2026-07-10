Add-Type -AssemblyName System.IO.Compression.FileSystem
$out = Join-Path $env:TEMP "offext_out"
Remove-Item $out -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $out | Out-Null

function GetZipEntries($src) {
    return [System.IO.Compression.ZipFile]::OpenRead($src)
}

function ReadEntry($entry) {
    $sr = New-Object System.IO.StreamReader($entry.Open())
    $x = $sr.ReadToEnd()
    $sr.Close()
    return $x
}

function StripTags($xml) {
    $xml = $xml -replace '<w:p[ >', "`n<w:p>"
    $xml = $xml -replace '<a:p[ >', "`n<a:p>"
    $xml = $xml -replace '<cp[^>]*/>', "`n"
    return ($xml -replace '<[^>]+>', '')
}

$files = Get-ChildItem -Path "." -File | Where-Object { ".pptx",".docx",".xlsx",".vsdx" -contains $_.Extension } | Sort-Object Name
$i = 0
foreach ($f in $files) {
    $i++
    $mode = $f.Extension.TrimStart(".")
    $outName = "{0:D2}.txt" -f $i
    $sb = New-Object System.Text.StringBuilder
    [void]$sb.Append("FILE: " + $f.Name + "`r`n")
    [void]$sb.Append("MODE: " + $mode + "`r`n`r`n")
    try {
        $z = GetZipEntries $f.FullName
        switch ($mode) {
            "docx" {
                $entry = $z.Entries | Where-Object { $_.FullName -eq "word/document.xml" } | Select-Object -First 1
                if ($entry) { [void]$sb.Append((StripTags (ReadEntry $entry))) }
            }
            "pptx" {
                $slides = $z.Entries | Where-Object { $_.FullName -match '^ppt/slides/slide\d+\.xml$' } | Sort-Object { [int](($_.Name -replace '[^0-9]','')) }
                foreach ($e in $slides) {
                    [void]$sb.Append("`r`n=== " + $e.Name + " ===`r`n")
                    [void]$sb.Append((StripTags (ReadEntry $e)))
                }
                $notes = $z.Entries | Where-Object { $_.FullName -match '^ppt/notesSlides/notesSlide\d+\.xml$' }
                if ($notes) {
                    [void]$sb.Append("`r`n=== NOTES ===`r`n")
                    foreach ($e in $notes) { [void]$sb.Append((StripTags (ReadEntry $e))) }
                }
            }
            "xlsx" {
                $ssEntry = $z.Entries | Where-Object { $_.FullName -eq "xl/sharedStrings.xml" } | Select-Object -First 1
                $shared = @()
                if ($ssEntry) {
                    $ssXml = ReadEntry $ssEntry
                    $ms = [regex]::Matches($ssXml, '<si>(.*?)</si>', 'Singleline')
                    foreach ($m in $ms) {
                        $t = ($m.Groups[1].Value -replace '<[^>]+>', '')
                        $shared += $t
                    }
                }
                [void]$sb.Append("=== SharedStrings count=" + $shared.Count + " ===`r`n")
                for ($k=0; $k -lt $shared.Count; $k++) { [void]$sb.Append("[$k] " + $shared[$k] + "`r`n") }
                $sheets = $z.Entries | Where-Object { $_.FullName -match '^xl/worksheets/sheet\d+\.xml$' } | Sort-Object { [int](($_.Name -replace '[^0-9]','')) }
                foreach ($e in $sheets) {
                    $shXml = ReadEntry $e
                    [void]$sb.Append("`r`n=== " + $e.Name + " ===`r`n")
                    $rows = [regex]::Matches($shXml, '<row[^>]*r="(\d+)"[^>]*>(.*?)</row>', 'Singleline')
                    foreach ($r in $rows) {
                        $rowNum = $r.Groups[1].Value
                        $rowContent = $r.Groups[2].Value
                        $cells = [regex]::Matches($rowContent, '<c r="([A-Z]+\d+)"(?:[^>]*t="([^"]+)")?[^>]*>(?:<v>([^<]*)</v>)?')
                        $vals = @()
                        foreach ($c in $cells) {
                            $ref = $c.Groups[1].Value
                            $t = $c.Groups[2].Value
                            $v = $c.Groups[3].Value
                            if ($t -eq "s" -and $v -ne "") { $val = $shared[[int]$v] } else { $val = $v }
                            $vals += ($ref + "=" + $val)
                        }
                        if ($vals.Count -gt 0) { [void]$sb.Append("R" + $rowNum + ": " + ($vals -join " | ") + "`r`n") }
                    }
                }
            }
            "vsdx" {
                $pages = $z.Entries | Where-Object { $_.FullName -match '^visio/pages/.*\.xml$' } | Sort-Object Name
                foreach ($e in $pages) {
                    $xml = ReadEntry $e
                    [void]$sb.Append("`r`n=== " + $e.Name + " ===`r`n")
                    $tms = [regex]::Matches($xml, '<Text>(.*?)</Text>', 'Singleline')
                    foreach ($tm in $tms) {
                        $t = ($tm.Groups[1].Value -replace '<cp[^>]*/>', "`n") -replace '<[^>]+>', ''
                        [void]$sb.Append($t + "`r`n---`r`n")
                    }
                }
            }
        }
        $z.Dispose()
    } catch {
        [void]$sb.Append("ERROR: " + $_.Exception.Message + "`r`n")
    }
    $result = $sb.ToString()
    $resultPath = Join-Path $out $outName
    [System.IO.File]::WriteAllText($resultPath, $result, [System.Text.Encoding]::UTF8)
    Write-Output ($outName + " <= " + $f.Name + " : " + $result.Length + " chars")
}
Write-Output ("OUTDIR=" + $out)
