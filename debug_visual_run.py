import argparse
import os
from pathlib import Path
from run import run


def _latest_job_folder(base: Path) -> Path:
    jobs = [p for p in base.iterdir() if p.is_dir()]
    if not jobs:
        raise FileNotFoundError(f"No job folders found in {base}")
    jobs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return jobs[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run routing with the visual debugger enabled.")
    parser.add_argument("--job-id", help="Existing job ID from storage/jobs", default=None)
    parser.add_argument("--jobs-root", help="Jobs root folder", default="./storage/jobs")
    args = parser.parse_args()

    jobs_root = Path(args.jobs_root)

    if args.job_id:
        job_folder = jobs_root / args.job_id
        if not job_folder.exists():
            raise FileNotFoundError(f"Job folder not found: {job_folder}")
        job_id = args.job_id
    else:
        job_folder = _latest_job_folder(jobs_root)
        job_id = job_folder.name

    os.environ["MAKEDEVICE_DEBUG_VISUAL"] = "1"
    run(job_id, job_folder)


if __name__ == "__main__":
    main()
