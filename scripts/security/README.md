# Container Security Remediation

`container_remediation.py` is the repository helper used by the daily
Container Security workflow to find newer Docker Hub images and replace one
exact pinned `tag@digest` reference in `compose.yml`.

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

## Commands

```bash
python3 scripts/security/container_remediation.py discover \
  --config scripts/security/container-images.json \
  --image 'amir20/dozzle:v10.6.14@sha256:...'

python3 scripts/security/container_remediation.py replace \
  --file compose.yml \
  --current 'amir20/dozzle:v10.6.14@sha256:...' \
  --candidate 'amir20/dozzle:v10.7.1@sha256:...'

python3 -m unittest discover -s scripts/security/tests -p 'test_*.py' -v
```

`replace` requires the complete current reference to occur exactly once and
refuses to switch repositories.
