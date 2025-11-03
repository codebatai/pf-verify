from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception:
    yaml = None  # keep deps optional


REQUIRED_FIELDS = [
    "id",
    "ts",
    "subject",
    "input_hash",
    "output_hash",
    "env",
    "merkle",
    "tsa",
    "transparency",
    "signatures",
]

PLACEHOLDER_URL_PREFIXES = (
    "https://example.invalid",
    "https://rekor.example.invalid",
    "tsa://rfc3161.example.invalid",
)
PLACEHOLDER_KMS_PREFIXES = ("kms+example://",)


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _load_yaml(path: Path) -> dict | None:
    if path and yaml:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def _check_required_fields(receipt: dict) -> list[str]:
    missing = []
    for key in REQUIRED_FIELDS:
        if key not in receipt:
            missing.append(key)
    return missing


def _enforce_placeholders(receipt: dict) -> list[str]:
    """Reject any obvious real endpoints/keys. Only allow placeholders."""
    problems: list[str] = []

    def is_placeholder_url(val: str) -> bool:
        return any(val.startswith(p) for p in PLACEHOLDER_URL_PREFIXES)

    def is_placeholder_kms(val: str) -> bool:
        return any(val.startswith(p) for p in PLACEHOLDER_KMS_PREFIXES)

    # urls
    trans = receipt.get("transparency", {})
    url = trans.get("rekor_url") or trans.get("mirror_urls", [None])[0]
    if isinstance(url, str) and not is_placeholder_url(url):
        problems.append(f"transparency URL must use placeholder domain: {url!r}")

    # timestamps (no network check here)

    # signer ids
    for i, sig in enumerate(receipt.get("signatures", [])):
        signer = sig.get("signer", "")
        if isinstance(signer, str) and not is_placeholder_kms(signer):
            problems.append(f"signatures[{i}].signer must use placeholder KMS: {signer!r}")

    return problems


def _print_markdown(passed: bool, errors: list[str], warn: list[str]) -> None:
    if passed:
        print("## ✅ OEP-288 Skeleton Verification Passed\n")
    else:
        print("## ❌ OEP-288 Skeleton Verification Failed\n")

    if errors:
        print("### Errors")
        for e in errors:
            print(f"- {e}")
        print()

    if warn:
        print("### Warnings")
        for w in warn:
            print(f"- {w}")
        print()


def _print_json(passed: bool, errors: list[str], warn: list[str]) -> None:
    print(
        json.dumps(
            {"passed": passed, "errors": errors, "warnings": warn},
            ensure_ascii=False,
            indent=2,
        )
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Public-safe skeleton verifier (no cryptography)."
    )
    p.add_argument("--receipt", required=True, help="Path to receipt.json")
    p.add_argument("--policy", required=False, help="Path to policy.yml (optional)")
    p.add_argument(
        "--format", choices=["markdown", "json"], default="markdown", help="Output format"
    )
    args = p.parse_args(argv)

    rpath = Path(args.receipt)
    if not rpath.exists():
        print(f"receipt not found: {rpath}", file=sys.stderr)
        return 1

    try:
        receipt = _load_json(rpath)
    except Exception as e:
        print(f"invalid JSON: {e}", file=sys.stderr)
        return 1

    # load policy (not enforced in skeleton, kept for future)
    if args.policy:
        if not Path(args.policy).exists():
            print(f"policy not found: {args.policy}", file=sys.stderr)
            return 1
        _ = _load_yaml(Path(args.policy))

    errors: list[str] = []
    warnings: list[str] = []

    # 1) required fields
    missing = _check_required_fields(receipt)
    if missing:
        errors.append(f"missing required fields: {', '.join(missing)}")

    # 2) placeholder safety
    problems = _enforce_placeholders(receipt)
    errors.extend(problems)

    passed = len(errors) == 0

    if args.format == "json":
        _print_json(passed, errors, warnings)
    else:
        _print_markdown(passed, errors, warnings)

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
