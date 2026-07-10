Add-Type -AssemblyName System.IO.Compression.FileSystem
$out = Join-Path $env:TEMP "offext_out"

function ReadEntry($entry) {
    $sr = New-Object System.IO.StreamReader($entry.Open())
    $x = $sr.ReadToEnd()
    $sr.Close()
    return $x
}

function ExtractT($xml, $tag) {
    $sb = New-Object System.Text.StringBuilder
    $pat = '<' + $tag + '[^>]*>([^<]*)</' + $tag + '>'
    $ms = [regex]::Matches($xml, $pat)
    foreach ($m in $ms) { [void]$sb.Append($m.Groups[1].Value + "`r`n") }
    return $sb.ToString()
}

$files = Get-ChildItem -Path "." -File | Where-Object { ".pptx",".docx" -contains $_.Extension } | Sort-Object Name
$i = 0
foreach ($f in $files) {
    $i++
    $mode = $f.Extension.TrimStart(".")
    $outName = "fix_{0:D2}.txt" -f $i
    $sb = New-Object System.Text.StringBuilder
    [void]$sb.Append("FILE: " + $f.Name + "`r`n`r`n")
    try {
        $z = [System.IO.Compression.ZipFile]::OpenRead($f.FullName)
        if ($mode -eq "docx") {
            $entry = $z.Entries | Where-Object { $_.FullName -eq "word/document.xml" } | Select-Object -First 1
            if ($entry) { [void]$sb.Append((ExtractT (ReadEntry $entry) "w:t")) }
            $hdrs = $z.Entries | Where-Object { $_.FullName -match '^word/header' }
            foreach ($h in $hdrs) { [void]$sb.Append((ExtractT (ReadEntry $h) "w:t")) }
        } else {
            $slides = $z.Entries | Where-Object { $_.FullName -match '^ppt/slides/slide\d+\.xml$' } | Sort-Object { [int](($_.Name -replace '[^0-9]','')) }
            foreach ($e in $slides) {
                $xml = ReadEntry $e
                [void]$sb.Append("`r`n=== " + $e.Name + " ===`r`n")
                [void]$sb.Append((ExtractT $xml "a:t"))
            }
            $notes = $z.Entries | Where-Object { $_.FullName -match '^ppt/notesSlides/notesSlide\d+\.xml$' }
            if ($notes) {
                [void]$sb.Append("`r`n=== NOTES ===`r`n")
                foreach ($e in $notes) { [void]$sb.Append((ExtractT (ReadEntry $e) "a:t")) }
            }
            $diagrams = $z.Entries | Where-Object { $_.FullName -match '^ppt/diagrams/' } | Sort-Object Name
            foreach ($e in $diagrams) {
                [void]$sb.Append("`r`n=== DIAGRAM " + $e.Name + " ===`r`n")
                [void]$sb.Append((ExtractT (ReadEntry $e) "a:t"))
            }
        }
        $z.Dispose()
    } catch { [void]$sb.Append("ERROR: " + $_.Exception.Message + "`r`n") }
    $result = $sb.ToString()
    $resultPath = Join-Path $out $outName
    [System.IO.File]::WriteAllText($resultPath, $result, [System.Text.Encoding]::UTF8)
    Write-Output ($outName + " <= " + $f.Name + " : " + $result.Length + " chars")
}
