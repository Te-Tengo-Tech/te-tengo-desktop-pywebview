#!/usr/bin/env python3
"""Summarise an OSV-Scanner JSON report as Markdown and gate on high or critical findings.

Usage: osv_summary.py <osv-results.json> [--fail-on-high]

The Markdown table goes to stdout (CI appends it to $GITHUB_STEP_SUMMARY). With --fail-on-high
the script exits with 1 when any vulnerability group has a CVSS score of 7.0 or higher.
A missing or unreadable report is always an error, so a broken scanner never looks green.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HIGH = 7.0


def severity(group: dict) -> float | None:
    try:
        return float(group.get("max_severity") or "")
    except ValueError:
        return None


def label(score: float | None) -> str:
    if score is None:
        return "unknown"
    if score >= 9.0:
        return f"critical ({score})"
    if score >= HIGH:
        return f"high ({score})"
    if score >= 4.0:
        return f"medium ({score})"
    return f"low ({score})"


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: osv_summary.py <osv-results.json> [--fail-on-high]", file=sys.stderr)
        return 2
    report = Path(argv[0])
    fail_on_high = "--fail-on-high" in argv[1:]
    try:
        data = json.loads(report.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        print(f"::error::OSV-Scanner report not readable ({error})", file=sys.stderr)
        return 1

    rows: list[tuple[float, str]] = []
    sources: list[str] = []
    for result in data.get("results") or []:
        source = (result.get("source") or {}).get("path", "?")
        sources.append(source)
        for entry in result.get("packages") or []:
            pkg = entry.get("package") or {}
            for group in entry.get("groups") or []:
                score = severity(group)
                ids = ", ".join(group.get("aliases") or group.get("ids") or [])
                rows.append(
                    (
                        score if score is not None else -1.0,
                        f"| `{pkg.get('name')}` | {pkg.get('version')} "
                        f"| {pkg.get('ecosystem')} | {ids} | {label(score)} |",
                    )
                )

    high = sum(1 for score, _ in rows if score >= HIGH)
    print("## OSV-Scanner")
    print()
    if not rows:
        print("No known vulnerabilities in the scanned lockfiles.")
    else:
        print(f"**{len(rows)}** vulnerability groups, **{high}** high or critical.")
        print()
        print("| Package | Version | Ecosystem | Advisories | Severity |")
        print("|---|---|---|---|---|")
        for _, row in sorted(rows, reverse=True):
            print(row)
    if sources:
        print()
        print("Scanned: " + ", ".join(f"`{Path(s).name}`" for s in sources))

    if fail_on_high and high:
        print(f"::error::{high} high or critical vulnerability groups found", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
