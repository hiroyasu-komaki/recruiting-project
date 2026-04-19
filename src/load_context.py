#!/usr/bin/env python3
"""
Context loader for cv-screening skill.
- Reads all job-description .md files from job-descriptions/
- Reads all template .md files from templates/
- Outputs structured JSON to stdout and saves to json/context.json
"""
import json
import sys
from pathlib import Path


def read_file(path: Path) -> dict:
    try:
        return {"filename": path.name, "content": path.read_text(encoding="utf-8")}
    except Exception as e:
        return {"filename": path.name, "content": None, "error": str(e)}


def main():
    base = Path(__file__).parent.parent
    jd_dir = base / "job-descriptions"
    tmpl_dir = base / "templates"

    if not jd_dir.exists():
        print(json.dumps({"error": f"job-descriptions/ directory not found: {jd_dir}"}))
        sys.exit(1)

    job_descriptions = [
        read_file(f)
        for f in sorted(jd_dir.glob("*_job-description.md"))
    ]

    templates = [
        read_file(f)
        for f in sorted(tmpl_dir.glob("*.md"))
    ] if tmpl_dir.exists() else []

    result = {
        "job_descriptions": job_descriptions,
        "templates": templates,
    }
    output = json.dumps(result, ensure_ascii=False, indent=2)

    json_dir = base / "json"
    json_dir.mkdir(exist_ok=True)
    context_file = json_dir / "context.json"
    context_file.write_text(output, encoding="utf-8")

    errors = [jd["filename"] for jd in job_descriptions if "error" in jd] + \
             [t["filename"] for t in templates if "error" in t]

    summary = {
        "status": "success",
        "saved_path": str(context_file),
        "loaded_job_descriptions": len(job_descriptions),
        "loaded_templates": len(templates),
        "errors": errors
    }
    print(json.dumps(summary, ensure_ascii=False))

if __name__ == "__main__":
    main()
