#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract images from Office files and parse vsdx flow connections.
Pure standard library, no external dependencies.
"""
import zipfile
import os
import re
import sys
import xml.etree.ElementTree as ET
import io

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Source directory (passed via argv to avoid hardcoding non-ASCII paths in script)
SRC_DIR = sys.argv[1] if len(sys.argv) > 1 else r'd:\开发资料\PMS资料\优化\2026\阶段性汇报文件'
OUT_DIR = sys.argv[2] if len(sys.argv) > 2 else r'C:\Users\user\AppData\Local\Temp\offimg_out'

IMG_EXTS = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.emf', '.wmf', '.svg', '.tiff', '.tif')
VNS = 'http://schemas.microsoft.com/office/visio/2012/main'
RNS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'

# Global image counter for unique naming
img_counter = [0]
conn_log = []  # (file, page, connections)
shape_log = []  # (file, page, shapes)
slide_img_log = []  # (file, slide, images)


def safe_basename(name):
    """Make a safe ASCII filename."""
    base = os.path.basename(name)
    # Replace non-ascii
    return re.sub(r'[^A-Za-z0-9._\-]', '_', base)


def extract_images(z, file_prefix, out_subdir):
    """Extract all images from a zip to output dir, return list of (orig_path, out_path, size)."""
    extracted = []
    for name in z.namelist():
        lower = name.lower()
        if any(lower.endswith(ext) for ext in IMG_EXTS):
            ext = os.path.splitext(name)[1]
            img_counter[0] += 1
            out_name = f"{file_prefix}_{img_counter[0]:03d}{ext}"
            out_path = os.path.join(out_subdir, out_name)
            try:
                with z.open(name) as src, open(out_path, 'wb') as dst:
                    data = src.read()
                    dst.write(data)
                extracted.append((name, out_path, len(data)))
            except Exception as e:
                print(f"  [WARN] failed extract {name}: {e}")
    return extracted


def parse_vsdx_pages(z, fname):
    """Parse vsdx page XMLs for shapes and connections."""
    page_files = [n for n in z.namelist()
                  if re.match(r'visio/pages/page\d+\.xml$', n, re.I)]
    for pf in page_files:
        try:
            data = z.read(pf)
            root = ET.fromstring(data)
            shapes = {}
            # Collect all shapes including nested
            for shape in root.iter(f'{{{VNS}}}Shape'):
                sid = shape.get('ID')
                if sid is None:
                    continue
                name = shape.get('Name', '') or ''
                nameU = shape.get('NameU', '') or ''
                text_parts = []
                for t in shape.iter(f'{{{VNS}}}Text'):
                    text_parts.append(''.join(t.itertext()))
                text = '\n'.join(s for s in text_parts if s).strip()
                # Type: is it a dynamic connector?
                type_attr = shape.get('Type', '') or ''
                master = shape.get('Master', '') or ''
                shapes[sid] = {
                    'id': sid,
                    'name': name,
                    'nameU': nameU,
                    'text': text,
                    'type': type_attr,
                    'master': master,
                }
            # Collect connections
            connects = []
            for conn in root.iter(f'{{{VNS}}}Connect'):
                connects.append({
                    'from_sheet': conn.get('FromSheet') or '',
                    'to_sheet': conn.get('ToSheet') or '',
                    'from_cell': conn.get('FromCell') or '',
                    'to_cell': conn.get('ToCell') or '',
                    'from_part': conn.get('FromPart') or '',
                    'to_part': conn.get('ToPart') or '',
                })
            conn_log.append((fname, pf, connects))
            shape_log.append((fname, pf, shapes))
        except Exception as e:
            print(f"  [WARN] parse {pf} in {fname}: {e}")


def parse_pptx_slide_images(z, fname):
    """Parse pptx slides to map which images appear on which slide."""
    slide_files = sorted([n for n in z.namelist()
                          if re.match(r'ppt/slides/slide\d+\.xml$', n, re.I)],
                         key=lambda x: int(re.search(r'(\d+)', x).group(1)))
    for sf in slide_files:
        try:
            data = z.read(sf)
            root = ET.fromstring(data)
            # Find pic elements referencing images
            pics = []
            ns_a = 'http://schemas.openxmlformats.org/drawingml/2006/main'
            ns_r = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
            for blip in root.iter(f'{{{ns_a}}}blip'):
                embed = blip.get(f'{{{ns_r}}}embed') or ''
                if embed:
                    pics.append(embed)
            slide_img_log.append((fname, sf, pics))
        except Exception as e:
            print(f"  [WARN] parse {sf} in {fname}: {e}")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    # Collect office files
    office_files = []
    for fn in os.listdir(SRC_DIR):
        lower = fn.lower()
        if lower.endswith(('.pptx', '.docx', '.xlsx', '.vsdx')):
            office_files.append(fn)
    office_files.sort()
    print(f"Found {len(office_files)} office files")
    # File prefix mapping (ascii)
    prefix_map = {}
    for i, fn in enumerate(office_files, 1):
        prefix_map[fn] = f"f{i:02d}"
    print("\n=== File prefix map ===")
    for fn, p in prefix_map.items():
        print(f"  {p} = {fn}")
    # Process each file
    img_manifest = []  # (prefix, orig_path, out_path, size)
    for fn in office_files:
        prefix = prefix_map[fn]
        fpath = os.path.join(SRC_DIR, fn)
        lower = fn.lower()
        print(f"\n>>> Processing {prefix} = {fn}")
        try:
            with zipfile.ZipFile(fpath, 'r') as z:
                # Extract images
                imgs = extract_images(z, prefix, OUT_DIR)
                for orig, out, sz in imgs:
                    img_manifest.append((prefix, orig, out, sz))
                # Parse vsdx connections
                if lower.endswith('.vsdx'):
                    parse_vsdx_pages(z, prefix)
                # Parse pptx slide->image mapping
                if lower.endswith('.pptx'):
                    parse_pptx_slide_images(z, prefix)
        except Exception as e:
            print(f"  [ERROR] {e}")
    # Write image manifest
    manifest_path = os.path.join(OUT_DIR, 'images_manifest.txt')
    with open(manifest_path, 'w', encoding='utf-8') as f:
        f.write("=== Image Manifest ===\n")
        f.write("prefix | orig_path | out_path | size(bytes)\n")
        for prefix, orig, out, sz in img_manifest:
            f.write(f"{prefix} | {orig} | {out} | {sz}\n")
        f.write(f"\nTotal images: {len(img_manifest)}\n")
    print(f"\nImage manifest written: {manifest_path}")
    # Write vsdx connections
    conn_path = os.path.join(OUT_DIR, 'vsdx_connections.txt')
    with open(conn_path, 'w', encoding='utf-8') as f:
        f.write("=== Visio Connections & Shapes ===\n")
        for fname, page, connects in conn_log:
            shapes = {}
            for ff, pp, ss in shape_log:
                if ff == fname and pp == page:
                    shapes = ss
                    break
            f.write(f"\n--- File: {fname}  Page: {page} ---\n")
            # Resolve file name
            real_file = "?"
            for k, v in prefix_map.items():
                if v == fname:
                    real_file = k
            f.write(f"(real file: {real_file})\n")
            f.write(f"Shapes ({len(shapes)}):\n")
            for sid, info in shapes.items():
                disp = info['text'] or info['name'] or info['nameU'] or '(no text)'
                type_info = info['type']
                if type_info == 'Group':
                    type_info = 'Group'
                f.write(f"  [{sid}] {disp[:120]}")
                if info['type']:
                    f.write(f"  <Type={info['type']}>")
                if info['master']:
                    f.write(f"  <Master={info['master']}>")
                f.write("\n")
            f.write(f"Connects ({len(connects)}):\n")
            for c in connects:
                from_id = c['from_sheet']
                to_id = c['to_sheet']
                from_text = shapes.get(from_id, {}).get('text', '') or shapes.get(from_id, {}).get('name', '') or from_id
                to_text = shapes.get(to_id, {}).get('text', '') or shapes.get(to_id, {}).get('name', '') or to_id
                f.write(f"  [{from_text[:60]}] --({c['from_cell']}->{c['to_cell']})--> [{to_text[:60]}]\n")
    print(f"Connections written: {conn_path}")
    # Write pptx slide->image mapping
    slide_path = os.path.join(OUT_DIR, 'pptx_slide_images.txt')
    with open(slide_path, 'w', encoding='utf-8') as f:
        f.write("=== PPTX Slide -> Image refs ===\n")
        for fname, slide, pics in slide_img_log:
            real_file = "?"
            for k, v in prefix_map.items():
                if v == fname:
                    real_file = k
            f.write(f"\n--- {fname} ({real_file}) {slide} ---\n")
            for p in pics:
                f.write(f"  blip ref: {p}\n")
    print(f"Slide image mapping written: {slide_path}")
    print("\n=== DONE ===")


if __name__ == '__main__':
    main()
