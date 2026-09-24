"""CLI entrypoint for standalone PDF report generation (REQ-9.7).

Usage:
    python -m app.reports <run_id> <out_path>
    python -m app.reports.pdf <run_id> <out_path>
"""

import shutil
import sys
from pathlib import Path

from app.reports.pdf import generate_pdf


def main() -> int:
    """CLI wrapper invoking generate_pdf() without embedding business logic."""
    if len(sys.argv) < 3:
        print("Usage: python -m app.reports <run_id> <out_path>", file=sys.stderr)
        return 1

    run_id = sys.argv[1]
    out_path = Path(sys.argv[2])

    try:
        temp_dir = out_path.parent
        temp_dir.mkdir(parents=True, exist_ok=True)

        generated_path = generate_pdf(run_id, output_dir=temp_dir)
        if generated_path != out_path:
            shutil.copyfile(generated_path, out_path)

        print(f"Successfully generated PDF report: {out_path}")
        return 0
    except Exception as err:
        print(f"Error generating PDF report for {run_id}: {err}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
