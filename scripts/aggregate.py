#!/usr/bin/env python3
"""Aggregate individual hook JSON files into hooklist.json and README table."""
import json
import glob
import os
import sys


def aggregate_hooks(hooks_dir: str) -> list[dict]:
    """Read all hook JSON files and return sorted list."""
    hooks = []
    pattern = os.path.join(hooks_dir, "**", "*.json")
    for filepath in glob.glob(pattern, recursive=True):
        with open(filepath) as f:
            hooks.append(json.load(f))
    hooks.sort(key=lambda h: (h["hook"]["chain"], h["hook"]["address"].lower()))
    return hooks


def generate_readme_table(hooks: list[dict]) -> str:
    """Generate a markdown table summarizing all hooks."""
    if not hooks:
        return "_No hooks registered yet._"

    lines = [
        "| Chain | Address | Name | Flags | Dynamic Fee | Returns Delta | Upgradeable |",
        "|-------|---------|------|-------|-------------|---------------|-------------|",
    ]
    for h in hooks:
        hook = h["hook"]
        flags = h["flags"]
        props = h["properties"]

        active_flags = [k for k, v in flags.items() if v]
        flag_str = ", ".join(active_flags) if active_flags else "none"

        returns_delta = any([
            flags.get("beforeSwapReturnsDelta"),
            flags.get("afterSwapReturnsDelta"),
            flags.get("afterAddLiquidityReturnsDelta"),
            flags.get("afterRemoveLiquidityReturnsDelta"),
        ])

        addr_short = f"`{hook['address'][:6]}...{hook['address'][-4:]}`"
        lines.append(
            f"| {hook['chain']} | {addr_short} | {hook['name']} | {flag_str} "
            f"| {'Yes' if props['dynamicFee'] else 'No'} "
            f"| {'Yes' if returns_delta else 'No'} "
            f"| {'Yes' if props['upgradeable'] else 'No'} |"
        )
    return "\n".join(lines)


def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hooks_dir = os.path.join(repo_root, "hooks")
    hooklist_path = os.path.join(repo_root, "hooklist.json")
    readme_path = os.path.join(repo_root, "README.md")

    hooks = aggregate_hooks(hooks_dir)

    # Write hooklist.json
    with open(hooklist_path, "w") as f:
        json.dump(hooks, f, indent=2)
        f.write("\n")

    # Write README.md
    table = generate_readme_table(hooks)
    readme_content = f"# hooklist\n\nA public registry of Uniswap v4 hook deployments.\n\n## Registered Hooks\n\n{table}\n"
    with open(readme_path, "w") as f:
        f.write(readme_content)

    print(f"Aggregated {len(hooks)} hooks into hooklist.json")


if __name__ == "__main__":
    main()
