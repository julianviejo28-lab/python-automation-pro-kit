#!/usr/bin/env python3
"""Read-only CSV profile: row counts, empty cells, duplicate rows and width issues."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from pathlib import Path


def detect_delimiter(sample: str) -> str:
    """Choose the common delimiter that produces the most consistent rows."""
    best_delimiter = ","
    best_score = (0, 0, 0)
    for delimiter in (",", ";", "\t", "|"):
        try:
            widths = [len(row) for row in csv.reader(io.StringIO(sample), delimiter=delimiter) if row]
        except csv.Error:
            continue
        counts: dict[int, int] = {}
        for width in widths:
            if width > 1:
                counts[width] = counts.get(width, 0) + 1
        if not counts:
            continue
        modal_width, matching_rows = max(counts.items(), key=lambda item: (item[1], item[0]))
        score = (matching_rows, modal_width, -len(widths))
        if score > best_score:
            best_score = score
            best_delimiter = delimiter
    return best_delimiter


def inspect_csv(path: Path) -> dict:
    """Inspect a UTF-8 CSV without changing the input file."""
    path = Path(path)
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        sample = stream.read(4096)
        stream.seek(0)
        reader = csv.reader(stream, delimiter=detect_delimiter(sample))
        try:
            headers = next(reader)
        except StopIteration:
            headers = []

        missing = [0] * len(headers)
        seen: set[bytes] = set()
        row_count = duplicate_rows = malformed_rows = 0
        for row in reader:
            row_count += 1
            if len(row) != len(headers):
                malformed_rows += 1
            for index in range(min(len(row), len(headers))):
                if not row[index].strip():
                    missing[index] += 1
            fingerprint = hashlib.sha256(
                json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            ).digest()
            if fingerprint in seen:
                duplicate_rows += 1
            else:
                seen.add(fingerprint)

    return {
        "file": path.name,
        "rows": row_count,
        "column_count": len(headers),
        "columns": headers,
        "duplicate_rows": duplicate_rows,
        "malformed_rows": malformed_rows,
        "missing_cells": [
            {"column": name, "index": index + 1, "count": missing[index]}
            for index, name in enumerate(headers)
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only summary of a CSV file.")
    parser.add_argument("file", type=Path, help="CSV file to inspect")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    args = parser.parse_args(argv)
    try:
        report = inspect_csv(args.file)
    except (OSError, UnicodeError, csv.Error) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print(f"File: {report['file']}")
    print(f"Rows: {report['rows']}  |  Columns: {report['column_count']}")
    print(f"Exact duplicate rows: {report['duplicate_rows']}")
    print(f"Rows with a different field count: {report['malformed_rows']}")
    print("Empty cells by column:")
    if report["missing_cells"]:
        for item in report["missing_cells"]:
            print(f"  {item['column'] or '(unnamed)'}: {item['count']}")
    else:
        print("  (no header row)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
