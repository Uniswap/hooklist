#!/usr/bin/env python3
"""Assemble a hook JSON file from prefilter, source, flags, and Claude outputs.

Usage: python3 scripts/assemble_hook.py \\
    --submission submission.json \\
    --source-meta source_meta.json \\
    --flags computed_flags.json \\
    --claude claude_output.json \\
    --issue-number 123 \\
    [--output hooks/<chain>/<address>.json] \\
    [--pr-body pr_body.md]
"""
import json
import os
import re
import sys

import jsonschema

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
# Allow alphanumeric, spaces, hyphens, periods, underscores, parentheses
SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9 \-._()]")


def sanitize_name(name: str) -> str:
    """Sanitize a hook name for shell safety."""
    name = SAFE_NAME_RE.sub("", name).strip()
    if not name:
        return "UnnamedHook"
    return name[:100]


def assemble(submission: dict, source_meta: dict, flags: dict, claude_output: dict, issue_number: int) -> dict:
    """Assemble the final hook JSON from all inputs."""
    with open(os.path.join(REPO_ROOT, "chains.json")) as f:
        chains = json.load(f)

    chain = submission["chain"]
    chain_id = chains[chain]["chainId"]

    # Name priority: submitter > claude > contractName
    name = submission.get("name", "").strip()
    if not name:
        name = claude_output.get("name", "").strip()
    if not name:
        name = source_meta.get("contractName", "").strip()
    if not name:
        name = "UnnamedHook"
    name = sanitize_name(name)

    # Description priority: submitter > claude
    description = submission.get("description", "").strip()
    if not description:
        description = claude_output.get("description", "").strip()

    # Deployer: must be valid address or empty
    deployer = submission.get("deployer", "").strip()
    if deployer and not ADDRESS_RE.match(deployer):
        deployer = ""

    # Audit URL: must be https or empty
    audit_url = submission.get("auditUrl", "").strip()
    if audit_url and not re.match(r"^https://", audit_url):
        audit_url = ""

    hook = {
        "hook": {
            "address": submission["address"],
            "chain": chain,
            "chainId": chain_id,
            "name": name,
            "description": description,
            "deployer": deployer,
            "verifiedSource": source_meta.get("verified", True),
            "auditUrl": audit_url,
        },
        "flags": flags,
        "properties": {
            "dynamicFee": claude_output["dynamicFee"],
            "upgradeable": claude_output["upgradeable"],
            "requiresCustomSwapData": claude_output["requiresCustomSwapData"],
            "vanillaSwap": claude_output["vanillaSwap"],
            "swapAccess": claude_output["swapAccess"],
        },
    }

    # Validate against schema
    with open(os.path.join(REPO_ROOT, "schema.json")) as f:
        schema = json.load(f)
    jsonschema.validate(hook, schema)

    return hook


def generate_pr_body(flags: dict, claude_output: dict, description: str, issue_number: int) -> str:
    """Generate the PR body markdown."""
    flag_rows = "\n".join(f"| {k} | {str(v).lower()} |" for k, v in flags.items())
    prop_rows = "\n".join(
        f"| {k} | {str(v).lower() if isinstance(v, bool) else v} |"
        for k, v in {
            "dynamicFee": claude_output["dynamicFee"],
            "upgradeable": claude_output["upgradeable"],
            "requiresCustomSwapData": claude_output["requiresCustomSwapData"],
            "vanillaSwap": claude_output["vanillaSwap"],
            "swapAccess": claude_output["swapAccess"],
        }.items()
    )

    return f"""## Summary
{description}

## Flags
| Flag | Value |
|------|-------|
{flag_rows}

## Properties
| Property | Value |
|----------|-------|
{prop_rows}

## Warnings
None

Closes #{issue_number}
"""


def main():
    args = sys.argv[1:]

    def get_arg(flag):
        if flag in args:
            return args[args.index(flag) + 1]
        return None

    submission_path = get_arg("--submission")
    source_meta_path = get_arg("--source-meta")
    flags_path = get_arg("--flags")
    claude_path = get_arg("--claude")
    issue_number = int(get_arg("--issue-number") or 0)
    output_path = get_arg("--output")
    pr_body_path = get_arg("--pr-body")

    if not all([submission_path, source_meta_path, flags_path, claude_path, issue_number]):
        print(f"Usage: {sys.argv[0]} --submission <file> --source-meta <file> --flags <file> --claude <file> --issue-number <num> [--output <file>] [--pr-body <file>]", file=sys.stderr)
        sys.exit(1)

    with open(submission_path) as f:
        submission = json.load(f)
    with open(source_meta_path) as f:
        source_meta = json.load(f)
    with open(flags_path) as f:
        flags = json.load(f)
    with open(claude_path) as f:
        claude_output = json.load(f)

    hook = assemble(submission, source_meta, flags, claude_output, issue_number)

    hook_json = json.dumps(hook, indent=2) + "\n"
    print(hook_json)

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(hook_json)

    if pr_body_path:
        body = generate_pr_body(flags, claude_output, hook["hook"]["description"], issue_number)
        with open(pr_body_path, "w") as f:
            f.write(body)

    # Output the sanitized name for the workflow to use in shell commands
    print(f"SAFE_NAME={hook['hook']['name']}", file=sys.stderr)


if __name__ == "__main__":
    main()
