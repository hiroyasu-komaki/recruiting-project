#!/usr/bin/env python3
"""
CV pre-processor for cv-screening skill.
- Scans input/ for files, moves non-PDFs to error/
- Extracts text from all PDFs using pypdf
- Outputs structured JSON to stdout and saves to json/candidates.json
"""
import json
import random
import shutil
import sys
import re
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:
    print(json.dumps({"error": "pypdf not installed. Run: pip install pypdf"}))
    sys.exit(1)


def _unique_id(used: set) -> str:
    while True:
        candidate_id = f"{random.randint(10000, 99999)}"
        if candidate_id not in used:
            used.add(candidate_id)
            return candidate_id


def main():
    base = Path(__file__).parent.parent
    input_dir = base / "input"
    error_dir = base / "error"

    if not input_dir.exists():
        print(json.dumps({"error": f"input/ directory not found: {input_dir}"}))
        sys.exit(1)

    pdf_files = []
    non_pdf_files = []

    for f in sorted(input_dir.iterdir()):
        if not f.is_file():
            continue
        if f.suffix.lower() == ".pdf":
            pdf_files.append(f)
        else:
            non_pdf_files.append(f)

    # Move non-PDFs to error/
    moved = []
    if non_pdf_files:
        error_dir.mkdir(exist_ok=True)
        for f in non_pdf_files:
            dest = error_dir / f.name
            shutil.move(str(f), str(dest))
            moved.append({"filename": f.name, "format": f.suffix or "unknown"})

    # Extract text from PDFs
    candidates = []
    extraction_errors = []
    used_ids: set[str] = set()

    for pdf_path in pdf_files:
        try:
            reader = PdfReader(str(pdf_path))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)

            # 日本語文字間の不要な改行を削除（連鎖する改行に対応するためループで安定するまで繰り返す）
            # ひらがな全域・カタカナ全域(ーを含む U+30A0-U+30FF)・CJK統合漢字全域(U+4E00-U+9FFF)を対象とする
            JP = r'[\u3041-\u3096\u30a0-\u30ff\u4e00-\u9fff]'
            prev = None
            while prev != text:
                prev = text
                text = re.sub(JP + r'\n' + JP, lambda m: m.group(0).replace('\n', ''), text)
            # 日本語文字間の不要なスペースを削除（段落区切りの\n\nを壊さないよう空白のみ対象）
            text = re.sub(JP + r' +' + JP, lambda m: m.group(0).replace(' ', ''), text)

            candidate_id = _unique_id(used_ids)
            candidates.append({
                "id": candidate_id,
                "filename": pdf_path.name,
                "pages": len(reader.pages),
                "text": text,
            })
        except Exception as e:
            extraction_errors.append({"filename": pdf_path.name, "error": str(e)})

    result = {
        "candidates": candidates,
        "moved_to_error": moved,
        "extraction_errors": extraction_errors,
    }
    output = json.dumps(result, ensure_ascii=False, indent=2)

    json_dir = base / "json"
    json_dir.mkdir(exist_ok=True)
    candidates_file = json_dir / "candidates.json"
    candidates_file.write_text(output, encoding="utf-8")

    # 標準出力にはCV本文を出さず、処理結果のサマリーのみをJSONで返す
    summary = {
        "status": "success",
        "saved_path": str(candidates_file),
        "candidates_count": len(candidates),
        "moved_to_error_count": len(moved),
        "extraction_errors_count": len(extraction_errors)
    }
    print(json.dumps(summary, ensure_ascii=False))

if __name__ == "__main__":
    main()
