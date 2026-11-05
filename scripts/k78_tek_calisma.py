"""QuantBIST – K-78 "one run" guard, called by .github/workflows/factor-study.yml before the real step.

    python scripts/k78_tek_calisma.py snapshot
    python scripts/k78_tek_calisma.py measure

It counts the earlier runs of the workflow from the Actions record. A step that ran counts as an attempt;
a job stopped earlier (date refused, no confirmation text) does not. A success, or two attempts (K-78: one
repeat after a technical failure), stops the job. If the record cannot be read the job stops too.
Standard library only: it runs before the packages are installed.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request

WORKFLOW = "factor-study.yml"
STEPS = {"snapshot": "Fresh download from Yahoo", "measure": "Measure (K-78, once)"}
MAX_ATTEMPTS = 2
ATTEMPT = ("success", "failure", "cancelled", "timed_out")


def decide(jobs: list[dict], job: str) -> tuple[bool, str]:
    """(may run, why) from the job records of the earlier runs."""

    outcomes = [s.get("conclusion") for j in jobs if j.get("name") == job for s in j.get("steps", [])
                if s.get("name") == STEPS[job] and s.get("conclusion") in ATTEMPT]
    if "success" in outcomes:
        return False, f"{job} daha önce başarıyla çalıştı; ikinci kez çalışmaz"
    if len(outcomes) >= MAX_ATTEMPTS:
        return False, f"{job} için {len(outcomes)} deneme yapıldı; en fazla {MAX_ATTEMPTS}"
    return True, f"{job}: önceki deneme {len(outcomes)}"


def _get(url: str, token: str) -> dict:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}",
                                                   "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310 - fixed https host
        return json.load(response)


def earlier_jobs(repo: str, token: str, current: str, get=_get) -> list[dict]:
    base = f"https://api.github.com/repos/{repo}/actions"
    jobs, page = [], 1
    while True:
        runs = get(f"{base}/workflows/{WORKFLOW}/runs?per_page=100&page={page}", token)["workflow_runs"]
        for run in runs:
            if str(run["id"]) != str(current):
                jobs += get(f"{base}/runs/{run['id']}/jobs?per_page=100", token)["jobs"]
        if len(runs) < 100:
            return jobs
        page += 1


def main(argv: list[str] | None = None, get=_get) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1 or argv[0] not in STEPS:
        print(__doc__)
        return 2
    try:
        jobs = earlier_jobs(os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_TOKEN"],
                            os.environ["GITHUB_RUN_ID"], get)
    except Exception as error:  # noqa: BLE001 - fail closed: an unread record never allows a run
        print(f"K-78: önceki çalışmalar okunamadı ({type(error).__name__}); durdu.")
        return 1
    allowed, why = decide(jobs, argv[0])
    print("K-78: " + why)
    return 0 if allowed else 1


if __name__ == "__main__":
    raise SystemExit(main())
