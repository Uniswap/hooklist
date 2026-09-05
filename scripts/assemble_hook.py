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

import validate

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


def assemble(submission: dict, source_meta: dict, flags: dict, claude_output: dict,
             repo_root: str = REPO_ROOT) -> dict:
    """Assemble the final hook JSON from all inputs."""
    with open(os.path.join(repo_root, "chains.json")) as f:
        chains = json.load(f)

    chain = submission["chain"]
    chain_id = chains[chain]["chainId"]

    release_ref = (claude_output.get("release") or "").strip()
    if release_ref:
        release = validate.load_release(repo_root, release_ref)
        if release is None:
            # Raised immediately and explicitly, before the properties
            # cross-check below, so that check can never be silently
            # skipped by a dangling/typo'd release ref.
            raise ValueError(f"release not found: {release_ref}")
        mismatches = [
            field for field in
            ("dynamicFee", "upgradeable", "requiresCustomSwapData", "vanillaSwap", "swapAccess")
            if claude_output.get(field) != release["properties"].get(field)
        ]
        if mismatches:
            raise ValueError(
                f"properties mismatch with release {release_ref}: {', '.join(mismatches)}"
            )
        thin_hook: dict = {
            "address": submission["address"],
            "chain": chain,
            "chainId": chain_id,
            "release": release_ref,
        }
        deployer = submission.get("deployer", "").strip()
        if deployer and ADDRESS_RE.match(deployer):
            thin_hook["deployer"] = deployer
        instance_desc = claude_output.get("description", "").strip()
        if instance_desc:
            thin_hook["description"] = instance_desc[:500]
        hook = {"hook": thin_hook}
        errors = validate.check_hook_data(hook, repo_root, label="assembled")
        if errors:
            raise ValueError("; ".join(errors))
        return hook

    # Name: Claude is canonical (it evaluates the submitter's suggestion against the source
    # per classify-hook.md §6). Submitter text never lands directly in the registry.
    # contractName is a defense-in-depth fallback if Claude returns empty.
    name = claude_output.get("name", "").strip()
    if not name:
        name = source_meta.get("contractName", "").strip()
    if not name:
        name = "UnnamedHook"
    name = sanitize_name(name)

    # Description: Claude is canonical (see classify-hook.md §7).
    description = claude_output.get("description", "").strip()
    if len(description) > 500:
        description = description[:497] + "..."

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

    # check_hook_data does not enforce flags/properties coherence for
    # pointer-less full files (validate.py treats those as non-fatal
    # warnings for pre-existing legacy data — see legacy_semantic_warnings).
    # Freshly assembled output has no such legacy excuse, so enforce it
    # directly here as a hard failure.
    coherence_errors = validate.coherence_issues(hook["hook"]["address"], hook["properties"])
    if coherence_errors:
        raise ValueError("; ".join(coherence_errors))

    errors = validate.check_hook_data(hook, repo_root, label="assembled")
    if errors:
        raise ValueError("; ".join(errors))

    return hook


def generate_pr_body(flags: dict, claude_output: dict, description: str, issue_number: int,
                      release_ref: str | None = None, release_properties: dict | None = None) -> str:
    """Generate the PR body markdown.

    When `release_ref` is set (the assembled file is a thin release instance),
    the body opens with a pointer callout and the Properties table renders the
    release's canonical properties rather than Claude's per-instance output.
    """
    flag_rows = "\n".join(f"| {k} | {str(v).lower()} |" for k, v in flags.items())
    properties = release_properties if release_ref else {
        "dynamicFee": claude_output["dynamicFee"],
        "upgradeable": claude_output["upgradeable"],
        "requiresCustomSwapData": claude_output["requiresCustomSwapData"],
        "vanillaSwap": claude_output["vanillaSwap"],
        "swapAccess": claude_output["swapAccess"],
    }
    prop_rows = "\n".join(
        f"| {k} | {str(v).lower() if isinstance(v, bool) else v} |"
        for k, v in properties.items()
    )

    warnings = claude_output.get("warnings") or []
    if warnings:
        warning_section = "\n".join(f"- {w}" for w in warnings)
    else:
        warning_section = "None"

    header = f"Instance of release `{release_ref}`\n\n" if release_ref else ""

    return f"""{header}## Summary
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
{warning_section}

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

    hook = assemble(submission, source_meta, flags, claude_output)

    hook_json = json.dumps(hook, indent=2) + "\n"
    print(hook_json)

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(hook_json)

    release_ref = hook["hook"].get("release")
    release = validate.load_release(REPO_ROOT, release_ref) if release_ref else None
    description = hook["hook"].get("description", "")
    name = hook["hook"].get("name") or (sanitize_name(release["name"]) if release else "UnnamedHook")

    if pr_body_path:
        body = generate_pr_body(
            flags, claude_output, description, issue_number,
            release_ref=release_ref,
            release_properties=release["properties"] if release else None,
        )
        with open(pr_body_path, "w") as f:
            f.write(body)

    # Output the sanitized name for the workflow to use in shell commands
    print(f"SAFE_NAME={name}", file=sys.stderr)


if __name__ == "__main__":
    main()
