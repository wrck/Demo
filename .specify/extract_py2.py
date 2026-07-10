# -*- coding: utf-8 -*-
import zipfile, os, re, glob

base = os.getcwd()
outdir = os.path.join(os.environ.get("TEMP",""), "py_offext_out2")
os.makedirs(outdir, exist_ok=True)

def read_zip_entry(zf, name):
    try:
        with zf.open(name) as f:
            return f.read().decode("utf-8", errors="ignore")
    except KeyError:
        return None

def extract_t(xml, tag):
    """Extract <tag ...>text</tag> texts (tag local name, matches any namespace)."""
    pat = re.compile(r'<' + tag + r'(?:\s[^>]*)?>([^<]*)</' + tag + r'>')
    return [m.group(1) for m in pat.finditer(xml)]

def slide_number(name):
    m = re.search(r'(\d+)', name)
    return int(m.group(1)) if m else 0

def extract_pptx(path, oname):
    sb = ["FILE: %s" % os.path.basename(path)]
    zf = zipfile.ZipFile(path)
    names = zf.namelist()
    # slides
    slides = sorted([n for n in names if re.match(r'ppt/slides/slide\d+\.xml$', n)], key=slide_number)
    for s in slides:
        xml = read_zip_entry(zf, s) or ""
        toks = extract_t(xml, "a:t")
        sb.append("\n=== %s ===" % s)
        # keep non-empty, join runs in a paragraph by <a:p> boundaries
        # split by paragraph to preserve structure
        paras = re.split(r'<a:p[ >]', xml)
        for p in paras[1:]:
            runs = extract_t(p, "a:t")
            line = "".join(runs)
            if line.strip():
                sb.append(line)
        # table cells detection
        if "<a:tbl" in xml:
            sb.append("[has table]")
    # diagrams (SmartArt)
    diags = sorted([n for n in names if re.match(r'ppt/diagrams/data\d+\.xml$', n)])
    for d in diags:
        xml = read_zip_entry(zf, d) or ""
        toks = [t for t in extract_t(xml, "a:t") if t.strip()]
        if toks:
            sb.append("\n=== DIAGRAM %s ===" % d)
            for t in toks:
                sb.append(t)
    # notes
    notes = sorted([n for n in names if re.match(r'ppt/notesSlides/notesSlide\d+\.xml$', n)], key=slide_number)
    if notes:
        sb.append("\n=== NOTES ===")
        for n in notes:
            xml = read_zip_entry(zf, n) or ""
            paras = re.split(r'<a:p[ >]', xml)
            for p in paras[1:]:
                runs = extract_t(p, "a:t")
                line = "".join(runs)
                if line.strip():
                    sb.append(line)
    # chart titles/text
    charts = sorted([n for n in names if re.match(r'ppt/charts/chart\d+\.xml$', n)])
    for c in charts:
        xml = read_zip_entry(zf, c) or ""
        toks = [t for t in extract_t(xml, "a:t") if t.strip()]
        if toks:
            sb.append("\n=== CHART %s ===" % c)
            for t in toks:
                sb.append(t)
    zf.close()
    res = "\n".join(sb)
    with open(os.path.join(outdir, oname), "w", encoding="utf-8") as f:
        f.write(res)
    print("%s <= %s : %d chars" % (oname, os.path.basename(path), len(res)))

def extract_docx(path, oname):
    sb = ["FILE: %s" % os.path.basename(path)]
    zf = zipfile.ZipFile(path)
    names = zf.namelist()
    doc = read_zip_entry(zf, "word/document.xml") or ""
    # split by paragraph
    paras = re.split(r'<w:p[ >]', doc)
    for p in paras[1:]:
        # split by cell to mark tables
        cells = re.split(r'<w:tc[ >]', p)
        if len(cells) > 1:
            # table row
            line_parts = []
            for c in cells[1:]:
                runs = extract_t(c, "w:t")
                line_parts.append("".join(runs))
            line = " | ".join(line_parts)
        else:
            runs = extract_t(p, "w:t")
            line = "".join(runs)
        if line.strip():
            sb.append(line)
    # headers/footers
    for n in names:
        if re.match(r'word/(header|footer)\d+\.xml$', n):
            xml = read_zip_entry(zf, n) or ""
            runs = extract_t(xml, "w:t")
            line = "".join(runs)
            if line.strip():
                sb.append("[HF] " + line)
    zf.close()
    res = "\n".join(sb)
    with open(os.path.join(outdir, oname), "w", encoding="utf-8") as f:
        f.write(res)
    print("%s <= %s : %d chars" % (oname, os.path.basename(path), len(res)))

i = 0
for ext in [".pptx", ".docx"]:
    for f in sorted(glob.glob(os.path.join(base, "*"+ext))):
        i += 1
        oname = "py2_%02d.txt" % i
        try:
            if ext == ".pptx":
                extract_pptx(f, oname)
            else:
                extract_docx(f, oname)
        except Exception as e:
            print("%s ERROR: %s" % (os.path.basename(f), e))
print("OUTDIR=%s" % outdir)
