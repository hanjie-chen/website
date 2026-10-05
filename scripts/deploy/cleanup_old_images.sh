#!/usr/bin/env bash
set -euo pipefail

# Run only after deployment validation succeeds. Keep container-referenced images;
# no historical release or latest-tag cache is retained.
CURRENT_DEPLOY_SHA="${1:-}"
if [[ -z "${CURRENT_DEPLOY_SHA}" ]]; then
  echo "Usage: $0 <deploy_sha>" >&2
  exit 2
fi

IMAGE_REPOS=(
  "ghcr.io/hanjie-chen/website-web-app"
  "ghcr.io/hanjie-chen/website-articles-sync"
  "amir20/dozzle"
  "owasp/modsecurity-crs"
)
declare -A managed_repos=() protected_images=() protected_digests=()
for repo in "${IMAGE_REPOS[@]}"; do
  managed_repos["${repo}"]=1
done

# Include stopped containers, and fail before any removal if inspection fails.
# Command substitutions preserve Docker failures that process substitutions hide.
container_ids="$(docker container ls --all --quiet)"
if [[ -z "${container_ids}" ]]; then
  echo "[cleanup] No containers found; refusing cleanup without an active deployment." >&2
  exit 1
fi
mapfile -t containers <<< "${container_ids}"
container_images="$(docker container inspect --format '{{.Image}} {{.Config.Image}}' "${containers[@]}")"
while read -r image_id image_ref; do
  protected_images["${image_id}"]=1
  if [[ "${image_ref}" == *@* ]]; then
    # A pinned tag@digest is immutable; a plain tag may have moved since creation.
    repo="${image_ref%@*}"
    if [[ "${repo##*/}" == *:* ]]; then
      repo="${repo%:*}"
    fi
    protected_digests["${repo}@${image_ref##*@}"]=1
  fi
done <<< "${container_images}"

cleanup_status=0
for phase in tags digests; do
  # Rescan after tag removals: deleting the last tag can also delete its digests.
  images="$(docker image ls --digests --no-trunc --format '{{.Repository}} {{.Tag}} {{.Digest}} {{.ID}}')"

  # Containerd may list an index ID instead of the container's image ID. Match
  # immutable digest references too, protecting every alias of that listed image.
  while read -r repo tag digest image_id; do
    [[ -n "${repo}" ]] || continue
    if [[ -n "${protected_digests["${repo}@${digest}"]:-}" ]]; then
      protected_images["${image_id}"]=1
    fi
  done <<< "${images}"

  declare -A processed_refs=()
  while read -r repo tag digest image_id; do
    [[ -n "${repo}" ]] || continue
    [[ -n "${managed_repos["${repo}"]:-}" ]] || continue
    if [[ -n "${protected_images["${image_id}"]:-}" ]]; then
      continue
    fi

    if [[ "${phase}" == tags && "${tag}" != '<none>' ]]; then
      image_ref="${repo}:${tag}"
    elif [[ "${phase}" == digests && "${tag}" == '<none>' && "${digest}" != '<none>' ]]; then
      image_ref="${repo}@${digest}"
    else
      continue
    fi
    [[ -z "${processed_refs["${image_ref}"]:-}" ]] || continue
    processed_refs["${image_ref}"]=1

    echo "[cleanup] Removing ${image_ref}"
    # Never force removal or prune anonymous parents outside the managed repos.
    if ! docker image rm --no-prune "${image_ref}"; then
      echo "[cleanup] Warning: failed to remove ${image_ref}" >&2
      cleanup_status=1
    fi
  done <<< "${images}"
done

echo "[cleanup] Finished for deployment ${CURRENT_DEPLOY_SHA}; container-referenced images retained."
exit "${cleanup_status}"
