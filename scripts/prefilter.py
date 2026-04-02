#!/usr/bin/env python3
"""Prefilter hook submissions: parse issue body, validate fields, check duplicates.

Usage: python3 scripts/prefilter.py <issue_body_json> [--hooks-dir <path>] [--output <path>]

<issue_body_json> is a file containing the issue body text.

Outputs sanitized submission fields as JSON to stdout (and optionally to --output file).
Exits non-zero with error message on validation failure.
"""
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join(REPO_ROOT, "chains.json")) as _f:
    CHAINS = set(json.load(_f).keys())

ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
AUDIT_URL_RE = re.compile(r"^(https://.*)?$")


def parse_issue_body(body: str) -> dict:
    """Parse structured fields from a GitHub issue form body."""
    sections = {}
    current_key = None
    current_lines = []

    for line in body.split("\n"):
        if line.startswith("### "):
            if current_key:
                sections[current_key] = "\n".join(current_lines).strip()
            current_key = line[4:].strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_key:
        sections[current_key] = "\n".join(current_lines).strip()

    def get(key, default=""):
        val = sections.get(key, default).strip()
        if val == "_No response_":
            return ""
        return val

    return {
        "chain": get("Chain"),
        "address": get("Hook Address").lower(),
        "name": get("Hook Name"),
        "description": get("Description"),
        "deployer": get("Deployer Address"),
        "auditUrl": get("Audit URL"),
    }


def validate_submission(submission: dict, hooks_dir: str | None = None) -> list[str]:
    """Validate submission fields. Returns list of error strings (empty = valid)."""
    errors = []

    if not ADDRESS_RE.match(submission["address"]):
        errors.append(f"Invalid address format: {submission['address']}")

    if submission["chain"] not in CHAINS:
        errors.append(f"Unsupported chain: {submission['chain']}. Must be one of: {', '.join(sorted(CHAINS))}")

    if submission["deployer"] and not ADDRESS_RE.match(submission["deployer"]):
        errors.append(f"Invalid deployer address: {submission['deployer']}. Must be a 0x address or empty.")

    if submission["auditUrl"] and not AUDIT_URL_RE.match(submission["auditUrl"]):
        errors.append(f"Invalid audit URL: {submission['auditUrl']}. Must be an https:// URL or empty.")

    if hooks_dir is None:
        hooks_dir = os.path.join(REPO_ROOT, "hooks")
    hook_path = os.path.join(hooks_dir, submission["chain"], f"{submission['address']}.json")
    if os.path.exists(hook_path):
        errors.append(f"Hook already registered: {submission['chain']}/{submission['address']}")

    return errors


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <issue_body_file> [--hooks-dir <path>] [--output <path>]", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1]) as f:
        body = f.read()

    hooks_dir = None
    if "--hooks-dir" in sys.argv:
        hooks_dir = sys.argv[sys.argv.index("--hooks-dir") + 1]

    submission = parse_issue_body(body)
    errors = validate_submission(submission, hooks_dir=hooks_dir)

    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    output = json.dumps(submission, indent=2)
    print(output)

    if "--output" in sys.argv:
        outpath = sys.argv[sys.argv.index("--output") + 1]
        with open(outpath, "w") as f:
            f.write(output)
            f.write("\n")


if __name__ == "__main__":
    main()
