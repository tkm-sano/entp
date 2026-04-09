#!/usr/bin/env bash

set -euo pipefail

MEDIA_PATHS=(
  "assets/images/models"
  "assets/videos/models"
)

staged_outside_media=()
media_changes=()
changed_model_ids=()

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Git repository not found."
  exit 1
fi

current_branch="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$current_branch" == "HEAD" ]]; then
  echo "Detached HEAD is not supported. Check out a branch first."
  exit 1
fi

while IFS= read -r line; do
  [[ -n "$line" ]] && staged_outside_media+=("$line")
done < <(git diff --cached --name-only -- . ':(exclude)assets/images/models' ':(exclude)assets/videos/models')

if (( ${#staged_outside_media[@]} > 0 )); then
  echo "There are already staged changes outside model media. Commit or unstage them first."
  printf ' - %s\n' "${staged_outside_media[@]}"
  exit 1
fi

while IFS= read -r line; do
  [[ -n "$line" ]] && media_changes+=("$line")
done < <(git status --short -- "${MEDIA_PATHS[@]}")

if (( ${#media_changes[@]} == 0 )); then
  echo "No model media changes found in assets/images/models or assets/videos/models."
  exit 0
fi

git add -A -- "${MEDIA_PATHS[@]}"

if git diff --cached --quiet -- "${MEDIA_PATHS[@]}"; then
  echo "No staged model media changes to commit."
  exit 0
fi

while IFS= read -r line; do
  [[ -n "$line" ]] && changed_model_ids+=("$line")
done < <(
  git diff --cached --name-only -- "${MEDIA_PATHS[@]}" \
    | sed -E 's#^assets/(images|videos)/models/([^/]+)/.*#\2#' \
    | sort -u
)

if (( ${#changed_model_ids[@]} == 1 )); then
  default_message="Add model media for ${changed_model_ids[0]}"
else
  default_message="Update model media"
fi

commit_message="${*:-$default_message}"

echo "Committing model media changes on branch: $current_branch"
printf ' - %s\n' "${changed_model_ids[@]}"

git commit -m "$commit_message"
git push origin "$current_branch"

echo "Pushed model media changes successfully."
