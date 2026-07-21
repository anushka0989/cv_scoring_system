import os
import sys

from cv_parser import parse_cv
from save_candidate import save_candidate

CV_FOLDER = sys.argv[1] if len(sys.argv) > 1 else os.getenv("CV_FOLDER", "uploads/cvs")
SUPPORTED = {".pdf", ".docx"}


def run_bulk_import(folder):
    if not os.path.isdir(folder):
        print(f"❌  Folder not found: {folder}")
        sys.exit(1)

    files = [f for f in os.listdir(folder) if os.path.splitext(f)[-1].lower() in SUPPORTED]
    if not files:
        print(f"⚠️  No supported CV files found in: {folder}")
        return

    saved = skipped = errors = 0

    for filename in files:
        file_path = os.path.join(folder, filename)
        print(f"\n📄  Processing: {filename}")
        try:
            candidate = parse_cv(file_path)

            if candidate["warnings"]:
                for w in candidate["warnings"]:
                    print(f"   ⚠️  {w}")

            print(f"   NAME: {candidate.get('name', '')}")
            print(f"   LATEST DESIGNATION: {candidate.get('latest_designation', '')}")
            print(f"   EXPERIENCE: {candidate.get('experience_years', '')} yrs")

            if not candidate.get("name"):
                errors += 1
                continue

            if save_candidate(candidate, cv_path=file_path, source_filename=filename):
                saved += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"   ❌  Error: {e}")
            errors += 1

    print(f"\n{'=' * 40}\n✅  Saved: {saved}\n⚠️  Skipped (duplicate): {skipped}\n❌  Errors/unparsed: {errors}\n{'=' * 40}")


if __name__ == "__main__":
    run_bulk_import(CV_FOLDER)
