# Container Security

Policy and Python helpers for pinned third-party container images. CI and the
daily security workflow perform the actual Trivy scans; triggers, PR automation,
permissions and production checks are described in the
[workflow guide](../../.github/workflows/README.md#container-security).

## Files and Responsibilities

| File | Responsibility |
| --- | --- |
| [container-images.json](container-images.json) | Tracked repositories, allowed tag patterns and version ordering |
| [container_ci_gate.py](container_ci_gate.py) | Validate pinned references and select images for CI scanning |
| [container_remediation.py](container_remediation.py) | Discover newer Docker Hub tags or replace an exact image reference |
| [trivyignore.yaml](trivyignore.yaml) | Shared, scoped vulnerability exceptions |
| [tests/](tests/) | Policy, image-selection and replacement checks |

Image references live in [compose.yml](../../compose.yml). The current scope is
Nginx/ModSecurity and Dozzle, not the application's own images.

## Scan and Update Policy

Actionable findings are HIGH/CRITICAL vulnerabilities with a fix available, after
applying the shared exceptions. Passing this policy does not establish runtime
compatibility; candidate images also go through CI runtime checks before release.

### CI Selection

Each tracked repository must appear exactly once with an allowed tag and a full
`sha256` digest. Missing, duplicate or invalid references fail the gate. The helper
reads literal `image:` lines; it does not resolve Compose variables or overlays.

With a base revision, the helper selects changed head references, including a
changed digest on the same tag. Without a base it selects all tracked images.
Comparing changed image policies also selects all images; removing a tracked
repository from the policy is rejected. CI passes `--base-config` to compare
policies and `--force-all` when `trivyignore.yaml` changes. The helper does not
inspect Git or detect exception-file changes itself.

### Candidate Discovery and Replacement

`discover` queries Docker Hub, filters tags through the configured policy and
returns newer candidates in descending version order. It uses the tag-level
digest returned by Docker Hub. Policies require a named `version` regex group;
ordering supports three-part numeric semantic versions or numeric timestamps.
Other registries require a separate discovery implementation.

`discover` does not scan vulnerabilities. The daily workflow scans candidates
and calls `replace` only after a candidate passes the shared policy. `replace`
requires exactly one occurrence of the current reference and the same repository
for both references. It edits the file directly and does not independently
require a newer version, a pinned candidate, or a passing scan. Use full
`repository:tag@sha256:...` references selected and checked by the workflow.

## Temporary Vulnerability Exceptions

Keep each exception's affected target/package, reason, supporting sources and
expiry in [trivyignore.yaml](trivyignore.yaml). Review or remove entries before
expiry; expired entries stop suppressing findings. Use `vulnerabilities: []`
when no exceptions remain. Avoid duplicating individual CVE status in this guide.

Both CI and candidate/daily scans use this file. Scope exceptions narrowly and
review policy changes together with the resulting scan; a policy edit triggers
CI scanning of all tracked images.

## Reports

The daily workflow retains `container-vulnerability-reports` for 30 days.
`actionable.json` contains package-level findings used for remediation;
`grouped-by-cve.json` groups them for presentation. The issue summarizes CVEs,
packages and images, with truncated display tables; use the artifact for complete
reports. Report generation and formatting are implemented in
[container-security.yml](../../.github/workflows/container-security.yml).

## Local Checks

Run from the repository root with Python 3; the helpers use the standard library.
This command validates current pinned references and lists all tracked images
without contacting a registry or modifying files:

```bash
python3 scripts/security/container_ci_gate.py changed \
  --config scripts/security/container-images.json --head compose.yml
python3 -m unittest discover -s scripts/security/tests -p 'test_*.py' -v
```

For comparison, add `--base <base-compose-path>` and
`--base-config <base-policy-path>`. Use `--help` on the `changed`, `discover` and
`replace` subcommands for arguments. Discovery requires Docker Hub network
access; unit tests use local fixtures and do not execute Trivy scans.
