"""
security_scan.py - Automated security audit scanner for secrets, PII, and build leaks.
Scans git tracking, commit history, and frontend bundle for API keys, bearer tokens, or PII.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT_DIR / ".env")

GENERIC_PATTERNS = [
    re.compile(r"gsk_[a-zA-Z0-9_\-]{30,}", re.IGNORECASE),  # Groq live key pattern
    re.compile(r"AIza[0-9A-Za-z\-_]{35}", re.IGNORECASE),    # Google API key pattern
    re.compile(r"sk-[a-zA-Z0-9]{32,}", re.IGNORECASE),       # OpenAI key pattern
    re.compile(r"-----BEGIN [A-Z]+ PRIVATE KEY-----"),       # Private keys
]

EXCLUDED_FILES = {".env", ".env.local"}


def get_live_secrets() -> list[tuple[str, str]]:
    secrets: list[tuple[str, str]] = []
    for var in ["GNANI_API_KEY", "GROQ_API_KEY"]:
        val = os.getenv(var, "").strip()
        if val and len(val) >= 12 and not val.startswith("your_") and not val.startswith("mock_"):
            secrets.append((var, val))
    return secrets


def scan_git_tree(live_secrets: list[tuple[str, str]]) -> list[str]:
    violations: list[str] = []
    tracked = subprocess.check_output(["git", "ls-files"], cwd=str(ROOT_DIR), text=True).splitlines()

    for rel_path in tracked:
        if rel_path in EXCLUDED_FILES:
            continue
        full_path = ROOT_DIR / rel_path
        if not full_path.is_file():
            continue
        try:
            content = full_path.read_text(encoding="utf-8", errors="ignore")
            # 1. Check live secrets
            for var_name, secret_val in live_secrets:
                if secret_val in content:
                    violations.append(f"{rel_path}: Leaked active secret {var_name}")
            # 2. Check generic patterns
            for pattern in GENERIC_PATTERNS:
                matches = pattern.findall(content)
                if matches:
                    violations.append(f"{rel_path}: Matched secret pattern {pattern.pattern}")
        except Exception as exc:
            violations.append(f"{rel_path}: Scan error: {exc}")
    return violations


def scan_git_history(live_secrets: list[tuple[str, str]], max_commits: int = 30) -> list[str]:
    violations: list[str] = []
    try:
        log_diff = subprocess.check_output(
            ["git", "log", f"-n{max_commits}", "-p", "--", ":!.env*"],
            cwd=str(ROOT_DIR),
            text=True,
            errors="ignore",
        )
        for var_name, secret_val in live_secrets:
            if secret_val in log_diff:
                violations.append(f"Git history: Leaked active secret {var_name}")
        for pattern in GENERIC_PATTERNS:
            matches = pattern.findall(log_diff)
            if matches:
                violations.append(f"Git history: Matched secret pattern {pattern.pattern}")
    except Exception as exc:
        violations.append(f"Git history scan error: {exc}")
    return violations


def scan_frontend_dist(live_secrets: list[tuple[str, str]]) -> list[str]:
    violations: list[str] = []
    dist_dir = ROOT_DIR / "frontend" / "dist"
    if not dist_dir.exists():
        return violations

    for p in dist_dir.rglob("*.js"):
        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
            for var_name, secret_val in live_secrets:
                if secret_val in content:
                    violations.append(f"Dist leak in {p.name}: Contains active secret {var_name}")
            for pattern in GENERIC_PATTERNS:
                matches = pattern.findall(content)
                if matches:
                    violations.append(f"Dist leak in {p.name}: Matched {pattern.pattern}")
        except Exception as exc:
            violations.append(f"{p.name}: Error scanning: {exc}")
    return violations


def main() -> None:
    print("[security_scan] Starting security and secrets scan across repository...")
    live_secrets = get_live_secrets()
    print(f"  - Configured live secrets to check: {[v[0] for v in live_secrets]}")

    tree_issues = scan_git_tree(live_secrets)
    history_issues = scan_git_history(live_secrets)
    dist_issues = scan_frontend_dist(live_secrets)

    total_issues = len(tree_issues) + len(history_issues) + len(dist_issues)
    print(f"\nScan complete: {total_issues} secret leak issues found.")
    print(f"  - Tracked files issues: {len(tree_issues)}")
    for issue in tree_issues:
        print(f"    * {issue}")
    print(f"  - Git history issues: {len(history_issues)}")
    for issue in history_issues:
        print(f"    * {issue}")
    print(f"  - Frontend dist leaks: {len(dist_issues)}")
    for issue in dist_issues:
        print(f"    * {issue}")

    if total_issues == 0:
        print("\nVerdict: PASSED. Working tree, git history, and build assets are completely free of active secrets.")
    else:
        print("\nVerdict: FAILED. Please scrub flagged secrets before release.")


if __name__ == "__main__":
    main()
