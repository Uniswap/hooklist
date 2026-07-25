#!/usr/bin/env python3
"""Assemble a family JSON file from Claude output or as an unverified stub.

Usage:
  python3 scripts/assemble_family.py --family 0x<hash> --stub \
      [--contract-name NAME] --output families/0x<hash>.json
  python3 scripts/assemble_family.py --family 0x<hash> \
      --claude claude_output.json --output families/0x<hash>.json
"""
import argparse
import datetime
import json
import os


def build_stub(family_id: str, contract_name: str = "") -> dict:
    return {"family": {
        "id": family_id,
        "kind": "unknown",
        "name": contract_name or f"Unknown {family_id[:10]}",
        "description": "",
        "sourceStatus": "unverified",
        "repoUrl": "",
        "auditUrl": "",
    }}


def build_analyzed(family_id: str, claude: dict, analyzed_at: str) -> dict:
    return {
        "family": {
            "id": family_id,
            "kind": claude["kind"],
            "name": claude["name"],
            "description": claude["description"],
            "sourceStatus": "verified",
            "repoUrl": "",
            "auditUrl": "",
            "analyzedAt": analyzed_at,
        },
        "implementedPermissions": claude["implementedPermissions"],
        "properties": {
            "dynamicFee": claude["dynamicFee"],
            "requiresCustomSwapData": claude["requiresCustomSwapData"],
            "vanillaSwap": claude["vanillaSwap"],
            "swapAccess": claude["swapAccess"],
        },
        "warnings": claude["warnings"],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", required=True)
    ap.add_argument("--stub", action="store_true")
    ap.add_argument("--contract-name", default="")
    ap.add_argument("--claude")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    if args.stub:
        out = build_stub(args.family, args.contract_name)
    else:
        with open(args.claude) as f:
            claude = json.load(f)
        today = datetime.date.today().isoformat()
        out = build_analyzed(args.family, claude, today)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(out, f, indent=2)
        f.write("\n")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
