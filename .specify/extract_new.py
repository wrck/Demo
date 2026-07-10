# -*- coding: utf-8 -*-
"""提取新增的 项目交付页面数据、逻辑、功能.xlsx 和 项目交付页面数据DemoV2.html"""
import zipfile, os, re, sys
from html.parser import HTMLParser

BASE = r"d:\开发资料\PMS资料\优化\2026\阶段性汇报文件"
OUT = r"C:\Users\user\AppData\Local\Temp\pms_new_files"
os.makedirs(OUT, exist_ok=True)

XLSX = os.path.join(BASE, "项目交付页面数据、逻辑、功能.xlsx")
HTML = os.path.join(BASE, "项目交付页面数据DemoV2.html")

# ============ 1. 提取 xlsx ============
def extract_xlsx(path, out_file):
    """提取 xlsx 所有 sheet 的 sharedStrings 与 cell 文本"""
    with zipfile.ZipFile(path, 'r') as z:
        names = z.namelist()

        # 提取 sharedStrings
        shared = []
        if 'xl/sharedStrings.xml' in names:
            xml = z.read('xl/sharedStrings.xml').decode('utf-8', errors='ignore')
            # 提取 <t> 节点（含命名空间）
            for m in re.finditer(r'<t[^>]*>([^<]*)</t>', xml):
                shared.append(m.group(1))

        # 提取 workbook.xml 获取 sheet 名称
        sheets = []
        if 'xl/workbook.xml' in names:
            xml = z.read('xl/workbook.xml').decode('utf-8', errors='ignore')
            for m in re.finditer(r'<sheet [^>]*name="([^"]*)"[^>]*sheetId="(\d+)"', xml):
                sheets.append((m.group(1), m.group(2)))

        # 提取每个 sheet 的单元格
        sheet_files = sorted([n for n in names if n.startswith('xl/worksheets/sheet') and n.endswith('.xml')])

        with open(out_file, 'w', encoding='utf-8') as f:
            f.write(f"FILE: {os.path.basename(path)}\n")
            f.write(f"MODE: xlsx\n")
            f.write(f"Sheets: {len(sheets)} | SharedStrings: {len(shared)}\n\n")

            # 输出 sharedStrings
            f.write("=== SharedStrings ===\n")
            for i, s in enumerate(shared):
                f.write(f"[{i}] {s}\n")
            f.write("\n")

            # 输出每个 sheet
            for idx, sf in enumerate(sheet_files):
                sheet_name = sheets[idx][0] if idx < len(sheets) else f"sheet{idx+1}"
                f.write(f"\n=== Sheet {idx+1}: {sheet_name} ({sf}) ===\n")
                xml = z.read(sf).decode('utf-8', errors='ignore')
                # 提取行
                for row_m in re.finditer(r'<row [^>]*r="(\d+)"[^>]*>(.*?)</row>', xml, re.DOTALL):
                    row_num = row_m.group(1)
                    row_xml = row_m.group(2)
                    cells = []
                    for cell_m in re.finditer(r'<c [^>]*r="([A-Z]+\d+)"[^>]*(?:t="([^"]*)")?[^>]*>(?:<v>([^<]*)</v>)?</c>', row_xml):
                        ref, t, v = cell_m.group(1), cell_m.group(2), cell_m.group(3)
                        if t == 's' and v is not None:
                            try:
                                cells.append(f"{ref}={shared[int(v)]}")
                            except:
                                cells.append(f"{ref}=?")
                        elif v is not None:
                            cells.append(f"{ref}={v}")
                    if cells:
                        f.write(f"Row {row_num}: {' | '.join(cells)}\n")

xlsx_out = os.path.join(OUT, "new_xlsx.txt")
extract_xlsx(XLSX, xlsx_out)
print(f"XLSX extracted: {xlsx_out}")

# ============ 2. 提取 HTML ============
class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.texts = []
        self.skip = False
        self.tag_stack = []

    def handle_starttag(self, tag, attrs):
        self.tag_stack.append(tag)
        if tag in ('script', 'style'):
            self.skip = True

    def handle_endtag(self, tag):
        if self.tag_stack and self.tag_stack[-1] == tag:
            self.tag_stack.pop()
        if tag in ('script', 'style'):
            self.skip = False
        # 块级元素换行
        if tag in ('div', 'p', 'tr', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'br', 'table', 'thead', 'tbody'):
            self.texts.append('\n')

    def handle_data(self, data):
        if not self.skip:
            text = data.strip()
            if text:
                self.texts.append(text)

def extract_html(path, out_file):
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        html = f.read()

    parser = TextExtractor()
    parser.feed(html)

    # 合并文本并清理多余空行
    text = ''.join(parser.texts)
    # 合并连续空行
    text = re.sub(r'\n{3,}', '\n\n', text)

    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(f"FILE: {os.path.basename(path)}\n")
        f.write(f"SIZE: {len(html)} chars\n")
        f.write(f"TEXT_SIZE: {len(text)} chars\n\n")
        f.write(text)

html_out = os.path.join(OUT, "new_html.txt")
extract_html(HTML, html_out)
print(f"HTML extracted: {html_out}")

print("\nDone.")
