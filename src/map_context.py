#!/usr/bin/env python3
"""
Maps job-description content from context.json to the job-description-template.json schema.
Reads:  json/context.json
Writes: json/context_mapping.json  (structured job_descriptions + templates copied as-is)
"""
import json
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Markdown parsing helpers
# ---------------------------------------------------------------------------

def _strip_bold(text: str) -> str:
    return re.sub(r'\*\*(.+?)\*\*', r'\1', text).strip()


def _extract_section(text: str, name: str) -> str:
    """Return the content of the section named `name` (any heading level).

    Stops at the next heading of equal or higher level (fewer #'s).
    """
    m = re.search(rf'^(#{{1,6}})\s+{re.escape(name)}\s*$', text, flags=re.MULTILINE)
    if not m:
        return ''
    level = len(m.group(1))
    after = text[m.end():]
    stop = re.search(rf'^#{{1,{level}}}\s', after, flags=re.MULTILINE)
    return after[:stop.start()].strip() if stop else after.strip()


def _extract_named_subsections(text: str) -> list[tuple[str, str]]:
    """Split text by its first-encountered heading level.

    Returns [(title, content), ...].
    """
    first = re.search(r'^(#{1,6})\s', text, flags=re.MULTILINE)
    if not first:
        return []
    level = len(first.group(1))
    hashes = '#' * level
    parts = re.split(rf'^{re.escape(hashes)}\s+(.+?)\s*$', text, flags=re.MULTILINE)
    result = []
    for i in range(1, len(parts), 2):
        result.append((parts[i].strip(), parts[i + 1] if i + 1 < len(parts) else ''))
    return result


def _parse_bullet_list(text: str) -> list[str]:
    return [
        line.strip()[2:].strip()
        for line in text.split('\n')
        if line.strip().startswith('- ')
    ]


def _parse_bold_kv(text: str) -> dict:
    """Parse '- **Key**: val1 / val2 / val3' lines into {key: [val1, val2, ...]}."""
    result = {}
    for line in text.split('\n'):
        m = re.match(r'-\s+\*\*(.+?)\*\*\s*[：:]\s*(.+)', line.strip())
        if m:
            key = m.group(1).strip()
            result[key] = [v.strip() for v in m.group(2).split('/') if v.strip()]
    return result


def _parse_table(text: str) -> list[dict]:
    """Parse a markdown table into a list of row dicts."""
    lines = [l.strip() for l in text.split('\n') if l.strip().startswith('|')]
    if len(lines) < 3:
        return []
    headers = [_strip_bold(h.strip()) for h in lines[0].split('|')[1:-1]]
    rows = []
    for line in lines[2:]:
        cells = [c.strip() for c in line.split('|')[1:-1]]
        if len(cells) != len(headers):
            continue
        row = {}
        for h, c in zip(headers, cells):
            c_clean = _strip_bold(c)
            if '<br>' in c_clean:
                row[h] = [p.strip().lstrip('•').strip() for p in c_clean.split('<br>') if p.strip()]
            else:
                row[h] = c_clean
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Section parsers
# ---------------------------------------------------------------------------

def _parse_shokushu(boshuu: str) -> dict:
    content = _extract_section(boshuu, '募集職種')
    subsections = _extract_named_subsections(content)
    if not subsections:
        return {'職種名': '', 'レベル': ''}
    title = subsections[0][0]
    m = re.match(r'^(.+)（(.+?)レベル）$', title.strip())
    if m:
        return {'職種名': m.group(1).strip(), 'レベル': m.group(2).strip() + 'レベル'}
    return {'職種名': title, 'レベル': ''}


def _parse_thematic(section_text: str) -> list[dict]:
    """Parse sub-sections each containing a bullet list → [{'テーマ': ..., '詳細': [...]}]."""
    return [
        {'テーマ': title, '詳細': _parse_bullet_list(content)}
        for title, content in _extract_named_subsections(section_text)
    ]


def _parse_requirements(section_text: str) -> dict:
    """Parse H3 sub-sections each with a bullet list → {サブセクション名: [...]}."""
    return {
        title: _parse_bullet_list(content)
        for title, content in _extract_named_subsections(section_text)
    }


def _parse_hyoka_jiku(gyomu: str) -> dict:
    content = _extract_section(gyomu, '業務レベルの評価軸')
    result = {}
    for title, body in _extract_named_subsections(content):
        if '影響範囲' in title:
            result['影響範囲'] = _parse_bold_kv(body)
        elif '難易度' in title:
            result['難易度'] = _parse_bold_kv(body)
    return result


def _parse_level_def(gyomu: str) -> list[dict]:
    content = _extract_section(gyomu, 'レベル定義')
    return _parse_table(content)


def _parse_scope(full_text: str) -> list[dict]:
    """業務スコープ定義 may live at any heading level; search full text."""
    scope_text = _extract_section(full_text, '業務スコープ定義')
    result = []
    for domain, content in _extract_named_subsections(scope_text):
        rows = _parse_table(content)
        categories = []
        for row in rows:
            detail = row.get('具体的な業務内容', [])
            if isinstance(detail, str):
                detail = [detail] if detail else []
            categories.append({
                '業務領域': row.get('業務領域', ''),
                '具体的な業務内容': detail,
            })
        result.append({'領域名': domain, 'カテゴリ': categories})
    return result


def _find_shoko(boshuu: str) -> str:
    """尚可 section name varies slightly across JDs."""
    for name in ['尚可（あれば望ましい要件）', '尚可']:
        s = _extract_section(boshuu, name)
        if s:
            return s
    return ''


# ---------------------------------------------------------------------------
# Top-level JD mapper
# ---------------------------------------------------------------------------

def map_jd(content: str) -> dict:
    boshuu = _extract_section(content, '募集要項')
    # 業務レベル要件定義 may be H1 (standard) or H2 inside 募集要項 (VMO-style)
    gyomu = _extract_section(content, '業務レベル要件定義')

    return {
        '募集要項': {
            '募集職種': _parse_shokushu(boshuu),
            '現状の課題': _parse_thematic(_extract_section(boshuu, '現状の課題')),
            '期待する役割・貢献': _parse_thematic(_extract_section(boshuu, '期待する役割・貢献')),
            '必須要件': _parse_requirements(_extract_section(boshuu, '必須要件')),
            '尚可': _parse_requirements(_find_shoko(boshuu)),
        },
        '業務レベル要件定義': {
            '業務レベルの評価軸': _parse_hyoka_jiku(gyomu),
            'レベル定義': _parse_level_def(gyomu),
            '業務スコープ定義': _parse_scope(content),
        },
        'appendix': _extract_section(content, 'APPENDIX'),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    base = Path(__file__).parent.parent
    context_path = base / 'json' / 'context.json'

    if not context_path.exists():
        print(json.dumps({'error': f'context.json not found: {context_path}'}))
        sys.exit(1)

    context = json.loads(context_path.read_text(encoding='utf-8'))

    mapped_jds = []
    for entry in context.get('job_descriptions', []):
        filename = entry.get('filename', '')
        if 'error' in entry or not entry.get('content'):
            mapped_jds.append({
                'filename': filename,
                'structured': None,
                'error': entry.get('error', 'content missing'),
            })
            continue
        try:
            mapped_jds.append({
                'filename': filename,
                'structured': map_jd(entry['content']),
            })
        except Exception as e:
            mapped_jds.append({'filename': filename, 'structured': None, 'error': str(e)})

    result = {
        'job_descriptions': mapped_jds,
        'templates': context.get('templates', []),
    }
    output = json.dumps(result, ensure_ascii=False, indent=2)

    out_path = base / 'json' / 'context_mapping.json'
    out_path.write_text(output, encoding='utf-8')

    success_count = sum(1 for jd in mapped_jds if jd.get('structured') is not None)
    errors = [jd['filename'] for jd in mapped_jds if jd.get('error')]

    summary = {
        "status": "success",
        "saved_path": str(out_path),
        "mapped_job_descriptions": success_count,
        "templates_carried_over": len(context.get('templates', [])),
        "errors": errors
    }
    print(json.dumps(summary, ensure_ascii=False))

if __name__ == '__main__':
    main()
