#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract text from EMF (Enhanced Metafile) vector images by parsing
text-drawing records. Pure standard library, no external dependencies.

EMF records of interest:
  EMR_EXTTEXTOUTW = 84  (UTF-16LE text, most common for Chinese)
  EMR_EXTTEXTOUTA = 83  (ANSI text)
  EMR_SMALLTEXTOUT = 51
  EMR_POLYTEXTOUTA = 95
  EMR_POLYTEXTOUTW = 96
"""
import struct
import sys
import os
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# EMF record types
EMR_HEADER = 1
EMR_EXTTEXTOUTA = 83
EMR_EXTTEXTOUTW = 84
EMR_POLYTEXTOUTA = 95
EMR_POLYTEXTOUTW = 96
EMR_SMALLTEXTOUT = 51
EMR_CREATEBRUSHINDIRECT = 39
EMR_SELECTOBJECT = 37
EMR_SETTEXTCOLOR = 24
EMR_SETTEXTALIGN = 26


def extract_emf_texts(data):
    """Parse EMF binary and return list of (x, y, text) tuples."""
    results = []
    if len(data) < 88:
        return results
    # EMF header: Type(4) Size(4) Bounds(16) Frame(16) Signature(4) Version(4) Bytes(4) Records(4) ...
    # Just iterate records after reading header record size.
    off = 0
    # First record is header
    if len(data) < 8:
        return results
    rec_type, rec_size = struct.unpack_from('<II', data, 0)
    if rec_type != EMR_HEADER:
        # Not a valid EMF
        return results
    off = rec_size
    while off + 8 <= len(data):
        rec_type, rec_size = struct.unpack_from('<II', data, off)
        if rec_size < 8 or off + rec_size > len(data):
            break
        rec_start = off
        rec_data = data[off:off + rec_size]
        if rec_type == EMR_EXTTEXTOUTW or rec_type == EMR_EXTTEXTOUTA:
            # EMR_EXTTEXTOUT record:
            # Type(4) Size(4) Bounds(16) iGraphicsMode(4) exScale(4) eyScale(4)
            # then EMRTEXT: ptlReference(8) nChars(4) offString(4) fOptions(4) rcl(16) offDx(4)
            try:
                base = 8 + 16  # after Type+Size+Bounds
                if rec_type == EMR_EXTTEXTOUTW:
                    # iGraphicsMode, exScale, eyScale
                    base += 12
                else:
                    base += 12
                # EMRTEXT
                ptl_ref_x, ptl_ref_y = struct.unpack_from('<ii', rec_data, base)
                n_chars = struct.unpack_from('<I', rec_data, base + 8)[0]
                off_string = struct.unpack_from('<I', rec_data, base + 12)[0]
                # String is at rec_start + off_string (offset is from start of record)
                abs_str_off = off_string  # relative to record start
                if n_chars > 0 and abs_str_off + n_chars * 2 <= rec_size:
                    if rec_type == EMR_EXTTEXTOUTW:
                        text = data[rec_start + abs_str_off: rec_start + abs_str_off + n_chars * 2].decode('utf-16-le', errors='replace')
                    else:
                        text = data[rec_start + abs_str_off: rec_start + abs_str_off + n_chars].decode('latin-1', errors='replace')
                    text = text.strip()
                    if text:
                        results.append((ptl_ref_x, ptl_ref_y, text))
            except Exception:
                pass
        elif rec_type == EMR_SMALLTEXTOUT:
            # EMR_SMALLTEXTOUT has a different layout, try best effort
            try:
                # Type(4) Size(4) then: ptlReference(8) nChars(4) offString(4) fOptions(4)
                # ... actually SMALLTEXTOUT puts string right after
                base = 8
                ptl_ref_x, ptl_ref_y = struct.unpack_from('<ii', rec_data, base)
                n_chars = struct.unpack_from('<I', rec_data, base + 8)[0]
                off_string = struct.unpack_from('<I', rec_data, base + 12)[0]
                abs_str_off = off_string
                if n_chars > 0 and abs_str_off + n_chars * 2 <= rec_size:
                    text = data[rec_start + abs_str_off: rec_start + abs_str_off + n_chars * 2].decode('utf-16-le', errors='replace')
                    text = text.strip()
                    if text:
                        results.append((ptl_ref_x, ptl_ref_y, text))
            except Exception:
                pass
        elif rec_type == EMR_POLYTEXTOUTW or rec_type == EMR_POLYTEXTOUTA:
            # Contains multiple EMRTEXT structures; complex, best-effort scan
            # skip for now
            pass
        off += rec_size
    return results


def main():
    in_dir = sys.argv[1] if len(sys.argv) > 1 else r'C:\Users\user\AppData\Local\Temp\offimg_out'
    out_dir = sys.argv[2] if len(sys.argv) > 2 else r'C:\Users\user\AppData\Local\Temp\offimg_out\emf_text'
    os.makedirs(out_dir, exist_ok=True)
    # Process all emf files
    emf_files = sorted([f for f in os.listdir(in_dir) if f.lower().endswith('.emf')])
    print(f"Found {len(emf_files)} EMF files")
    combined = []
    for fn in emf_files:
        fpath = os.path.join(in_dir, fn)
        try:
            with open(fpath, 'rb') as f:
                data = f.read()
            texts = extract_emf_texts(data)
            # Group by approximate y then x (to read in layout order)
            # Sort by y (rows), then x
            texts_sorted = sorted(texts, key=lambda t: (t[1] // 200, t[0]))
            out_name = os.path.splitext(fn)[0] + '.txt'
            out_path = os.path.join(out_dir, out_name)
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(f"=== EMF text: {fn} (size={len(data)}) ===\n")
                f.write(f"Total text records: {len(texts)}\n\n")
                # Output grouped by approximate rows
                if texts_sorted:
                    cur_y = texts_sorted[0][1] // 200
                    row_texts = []
                    for x, y, t in texts_sorted:
                        if y // 200 != cur_y:
                            if row_texts:
                                f.write(' | '.join(row_texts) + '\n')
                            cur_y = y // 200
                            row_texts = [t]
                        else:
                            row_texts.append(t)
                    if row_texts:
                        f.write(' | '.join(row_texts) + '\n')
            combined.append((fn, texts))
            print(f"  {fn}: {len(texts)} text records")
        except Exception as e:
            print(f"  [ERROR] {fn}: {e}")
    # Write combined
    combined_path = os.path.join(out_dir, '_all_emf_text.txt')
    with open(combined_path, 'w', encoding='utf-8') as f:
        f.write("=== All EMF Text Combined ===\n\n")
        for fn, texts in combined:
            f.write(f"\n========== {fn} ==========\n")
            texts_sorted = sorted(texts, key=lambda t: (t[1] // 200, t[0]))
            if texts_sorted:
                cur_y = texts_sorted[0][1] // 200
                row_texts = []
                for x, y, t in texts_sorted:
                    if y // 200 != cur_y:
                        if row_texts:
                            f.write(' | '.join(row_texts) + '\n')
                        cur_y = y // 200
                        row_texts = [t]
                    else:
                        row_texts.append(t)
                if row_texts:
                    f.write(' | '.join(row_texts) + '\n')
    print(f"\nCombined written: {combined_path}")
    print("DONE")


if __name__ == '__main__':
    main()
