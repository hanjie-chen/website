# Container Security Remediation

`container_remediation.py` is the repository helper used by the daily
Container Security workflow to find newer Docker Hub images and replace one
exact pinned `tag@digest` reference in `compose.yml`.

`container_ci_gate.py` is the required CI gate helper. It reads the tracked
repositories from `container-images.json`, compares their exact pinned image
references between base and head Compose files, and prints only changed head
references. Every tracked reference must use an allowed stable tag and a full
immutable SHA-256 digest; missing, duplicate, malformed, or silently removed
tracked images fail closed. Changes to `container-images.json` or
`trivyignore.yaml` force a full tracked-image scan. CI scans the selected
references with the same fixable HIGH/CRITICAL policy while the daily Container
Security workflow retains responsibility for full-inventory scans.

The helper does not decide whether an update is safe. The workflow first scans
the currently pinned images, calls this helper to discover newer stable tags,
then scans each candidate with the same Trivy policy used by CI. A candidate is
written to `compose.yml` only after that scan reports no fixable HIGH or
CRITICAL vulnerabilities.

Image-specific tag formats live in
[`container-images.json`](container-images.json).
Each regular expression must expose a named `version` group. The supported
ordering strategies are semantic versions with exactly three numeric
components and monotonically increasing numeric versions. This currently
covers Dozzle semantic tags and the date-based NGINX/ModSecurity tags without
hard-coding a vulnerability ID or fixed release.

The discovery client intentionally supports Docker Hub only. Adding another
registry requires an explicit discovery implementation so that the digest
written to Compose remains the immutable manifest-list digest returned by that
registry.

## Temporary Vulnerability Exceptions

[`trivyignore.yaml`](trivyignore.yaml) is the shared exception policy used by
CI and the daily Container Security workflow. Keep the empty
`vulnerabilities: []` list when no exception is active. Every temporary entry
must include a reason and an expiry date so an expired acceptance blocks the
scan again.

## Commands

```bash
python3 scripts/security/container_remediation.py discover \
  --config scripts/security/container-images.json \
  --image 'amir20/dozzle:v10.6.14@sha256:...'

python3 scripts/security/container_remediation.py replace \
  --file compose.yml \
  --current 'amir20/dozzle:v10.6.14@sha256:...' \
  --candidate 'amir20/dozzle:v10.7.1@sha256:...'

python3 scripts/security/container_ci_gate.py changed \
  --config scripts/security/container-images.json \
  --base /tmp/base-compose.yml \
  --head compose.yml

python3 -m unittest discover -s scripts/security/tests -p 'test_*.py' -v
```

`replace` requires the complete current reference to occur exactly once and
refuses to switch repositories.

The scheduled workflow creates remediation branches and pull requests with its
job-scoped `GITHUB_TOKEN` and explicit `contents`, `pull-requests`, `issues`, and
`actions` write permissions. The repository setting that allows GitHub Actions
to create pull requests must remain enabled. The workflow intentionally does
not query the repository Actions-permissions administration endpoint first:
that endpoint requires repository Administration permission, which the
workflow token cannot receive. Branch push or pull-request errors are reported
directly by the corresponding `git` or `gh` command.
