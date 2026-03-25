#!/usr/bin/env bash
set -euo pipefail

# Cleanup runs on the production VM after a successful deploy.
# Goal: keep the current release, keep latest, optionally keep a small rollback
# buffer, and delete older first-party images so disk usage does not grow forever.
CURRENT_DEPLOY_SHA="${1:-}"
# Keep one previous SHA by default so we still have a fast rollback target on-host.
# Set KEEP_PREVIOUS_RELEASES=0 if you prefer maximum disk savings over rollback cache.
KEEP_PREVIOUS_RELEASES="${KEEP_PREVIOUS_RELEASES:-1}"

if [[ -z "${CURRENT_DEPLOY_SHA}" ]]; then
  echo "Usage: $0 <deploy_sha>" >&2
  exit 2
fi

if ! [[ "${KEEP_PREVIOUS_RELEASES}" =~ ^[0-9]+$ ]]; then
  echo "KEEP_PREVIOUS_RELEASES must be a non-negative integer" >&2
  exit 2
fi

IMAGE_REPOS=(
  "ghcr.io/hanjie-chen/website-web-app"
  "ghcr.io/hanjie-chen/website-articles-sync"
)

for repo in "${IMAGE_REPOS[@]}"; do
  echo "[cleanup] Inspecting ${repo}..."

  # docker image ls returns newest-first for a repository. We use that order to
  # preserve the current deploy plus a small number of recent historical tags.
  mapfile -t ordered_tags < <(
    docker image ls "${repo}" --format '{{.Tag}}' \
      | awk '!seen[$0]++'
  )

  if [[ "${#ordered_tags[@]}" -eq 0 ]]; then
    echo "[cleanup] No local tags found for ${repo}, skipping."
    continue
  fi

  # latest and the active deploy tag should never be removed by this script.
  keep_tags=("latest" "${CURRENT_DEPLOY_SHA}")
  previous_kept=0

  # Keep a limited number of older SHA tags as rollback cache, then delete the rest.
  for tag in "${ordered_tags[@]}"; do
    if [[ "${tag}" == "<none>" || "${tag}" == "latest" || "${tag}" == "${CURRENT_DEPLOY_SHA}" ]]; then
      continue
    fi

    if (( previous_kept < KEEP_PREVIOUS_RELEASES )); then
      keep_tags+=("${tag}")
      ((previous_kept += 1))
      continue
    fi

    echo "[cleanup] Removing ${repo}:${tag}"
    docker image rm "${repo}:${tag}" >/dev/null || {
      echo "[cleanup] Warning: failed to remove ${repo}:${tag}" >&2
    }
  done

  echo "[cleanup] Keeping tags for ${repo}: ${keep_tags[*]}"
done
