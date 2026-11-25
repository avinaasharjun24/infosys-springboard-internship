"""Operator-controlled CLI for bounded test or full JDT ingestion.

Examples:
  python -m app.ingest_cli --test-limit 100
  python -m app.ingest_cli --full --batch-size 500
"""
import argparse
import json

from .knowledge import get_kb
from .config import settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Eclipse JDT defects into Qdrant")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--test-limit", type=int, metavar="N", help="Process a bounded verification batch")
    group.add_argument("--full", action="store_true", help="Process the complete configured CSV")
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--offset", type=int, default=0, help="CSV row offset to resume from")
    parser.add_argument("--path", default=settings.dataset_path)
    args = parser.parse_args()
    if args.batch_size < 50 or args.batch_size > 2000:
        parser.error("--batch-size must be between 50 and 2000")
    if args.offset < 0:
        parser.error("--offset must be >= 0")
    result = get_kb().ingest_csv(
        csv_path=args.path, limit=args.test_limit if not args.full else None,
        batch_size=args.batch_size, start_offset=args.offset,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
