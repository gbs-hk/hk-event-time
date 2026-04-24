#!/usr/bin/env python3
"""Verify that an exported Next.js app references only existing assets."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ASSET_PATTERN = re.compile(r'(?:href|src)="(/_next/[^"]+)"')


def parse_args() -> argparse.Namespace:
    default_dir = Path(__file__).resolve().parents[1] / "app" / "frontend_out"
    parser = argparse.ArgumentParser(
        description="Check that index.html only references assets that exist on disk."
    )
    parser.add_argument(
        "export_dir",
        nargs="?",
        default=default_dir,
        type=Path,
        help=f"Export directory to validate (default: {default_dir})"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    export_dir = args.export_dir.resolve()
    index_file = export_dir / "index.html"

    if not index_file.exists():
        print(f"Missing export entrypoint: {index_file}")
        return 1

    html = index_file.read_text(encoding="utf-8")
    asset_paths = sorted(set(ASSET_PATTERN.findall(html)))

    if not asset_paths:
        print(f"No /_next asset references found in {index_file}")
        return 1

    missing_assets = [
        asset_path
        for asset_path in asset_paths
        if not (export_dir / asset_path.removeprefix("/")).exists()
    ]

    if missing_assets:
        print(f"Missing {len(missing_assets)} exported asset(s) referenced by {index_file}:")
        for asset_path in missing_assets:
            print(f" - {asset_path}")
        return 1

    print(f"Verified {len(asset_paths)} exported asset reference(s) in {index_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
