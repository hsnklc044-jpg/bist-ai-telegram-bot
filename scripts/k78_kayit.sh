#!/usr/bin/env bash
# K-78 attempt record, called by .github/workflows/factor-study.yml: scripts/k78_kayit.sh STEP OUTCOME
# Appends one line to k78/denemeler.csv on research-results and copies that attempt's output next to it.
set -eo pipefail
step=$1
outcome=$2
stamp=$(TZ=Europe/Istanbul date '+%Y-%m-%d %H:%M')
if git fetch --depth=1 origin research-results; then
  git worktree add -B research-results results FETCH_HEAD
else
  git worktree add --orphan -b research-results results
fi
mkdir -p results/k78
[ -s results/k78/denemeler.csv ] || echo "zaman,adim,calisma,commit,sonuc" > results/k78/denemeler.csv
echo "$stamp,$step,$GITHUB_RUN_ID,${GITHUB_SHA::7},$outcome" >> results/k78/denemeler.csv
for f in k78.txt freeze_daily.txt; do
  if [ -s "$f" ]; then cp "$f" "results/k78/${step}_${GITHUB_RUN_ID}_$f"; fi
done
cd results
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git add -A
git commit -q -m "K-78 $step attempt $GITHUB_RUN_ID (${GITHUB_SHA::7}): $outcome"
for i in 1 2 3; do  # another workflow may have pushed meanwhile
  git pull --rebase -q origin research-results && git push -q origin research-results && exit 0
  sleep $((i * 10))
done
exit 1
