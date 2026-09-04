"""Publish a sanitized copy of an audit record.

`artifacts/` is gitignored because a completed run carries broker order identifiers. The audit
trail is the most useful thing this project produces, though, so this turns one run into a file
that is safe to commit and share: every identifier is replaced with a placeholder, and every
number a reader would want to check is kept.
"""

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

DEFAULT_SOURCE = Path("artifacts/latest-run.json")
DEFAULT_TARGET = Path("docs/sample-run.json")
#: The dashboard imports this at build time, so publishing keeps the site and the repo in step.
WEB_TARGET = Path("web/app/data/run.json")

REDACTED = "[redacted]"

#: Key names whose values identify an account, an order, or a credential.
SENSITIVE_KEYS = frozenset(
    {
        "account_id",
        "account_number",
        "api_key",
        "client_order_id",
        "id",
        "order_id",
        "secret_key",
        "token",
    }
)


def sanitize(value: Any) -> Any:
    """Recursively replace identifying values, preserving structure and every metric."""
    if isinstance(value, dict):
        return {
            key: REDACTED if key.lower() in SENSITIVE_KEYS else sanitize(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    return value


def publish(
    source: Path = DEFAULT_SOURCE,
    target: Path = DEFAULT_TARGET,
    *,
    extra_targets: Sequence[Path] = (),
) -> dict[str, Any]:
    if not source.exists():
        raise FileNotFoundError(f"no audit record at {source}; run alphabeater-run first")
    record = sanitize(json.loads(source.read_text(encoding="utf-8")))
    payload = json.dumps(record, indent=2) + "\n"
    for path in (target, *extra_targets):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--no-web", action="store_true", help="skip writing the dashboard copy")
    args = parser.parse_args()
    extra = () if args.no_web else (WEB_TARGET,)
    record = publish(args.source, args.target, extra_targets=extra)
    risk = record.get("risk") or {}
    checks = risk.get("checks") or []
    passed = sum(1 for check in checks if check.get("passed"))
    print(f"wrote {args.target}")
    if not args.no_web:
        print(f"wrote {WEB_TARGET}")
    print(f"  policy        : {record.get('execution_policy')}")
    print(f"  risk approved : {risk.get('approved')}")
    print(f"  checks passed : {passed}/{len(checks)}")
    print(f"  order         : {'submitted' if record.get('order') else 'none'}")


if __name__ == "__main__":  # pragma: no cover
    main()
