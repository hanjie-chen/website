"""Exercise cleanup against an isolated Docker CLI fixture, never the host daemon."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "cleanup_old_images.sh"
WEB = "ghcr.io/hanjie-chen/website-web-app"
SYNC = "ghcr.io/hanjie-chen/website-articles-sync"
DOZZLE = "amir20/dozzle"
NGINX = "owasp/modsecurity-crs"

DOCKER_FIXTURE = r'''#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys

path = Path(os.environ["DOCKER_FIXTURE_STATE"])
state = json.loads(path.read_text())
args = sys.argv[1:]
command = " ".join(args[:2])
state.setdefault("calls", []).append(args)
path.write_text(json.dumps(state))
if command == state.get("fail"):
    sys.exit(1)
if args == ["container", "ls", "--all", "--quiet"]:
    for container in state["containers"]:
        print(container["id"])
elif command == "container inspect":
    assert args[2:4] == ["--format", "{{.Image}} {{.Config.Image}}"]
    assert args[4:] == [c["id"] for c in state["containers"]]
    for container in state["containers"]:
        print(container["image"], container["ref"])
elif command == "image ls":
    assert args[2:] == ["--digests", "--no-trunc", "--format",
                        "{{.Repository}} {{.Tag}} {{.Digest}} {{.ID}}"]
    for row in state["images"]:
        print(*row)
elif command == "image rm":
    assert args[2] == "--no-prune" and len(args) == 4
    ref = args[3]
    state.setdefault("removed", []).append(ref)
    path.write_text(json.dumps(state))
    if ref in state.get("refuse", []):
        sys.exit(1)
    def reference(row):
        repo, tag, digest, _ = row
        return repo + "@" + digest if "@" in ref else repo + ":" + tag
    matched = [row for row in state["images"] if reference(row) == ref]
    if not matched:
        sys.exit(1)
    state["images"] = [row for row in state["images"] if reference(row) != ref]
    # Docker removes digest aliases when the last tag in a repository is removed.
    if "@" not in ref:
        repo, _, _, image_id = matched[0]
        if not any(r[0] == repo and r[3] == image_id and r[1] != "<none>"
                   for r in state["images"]):
            state["images"] = [r for r in state["images"]
                               if not (r[0] == repo and r[3] == image_id)]
    path.write_text(json.dumps(state))
else:
    raise AssertionError(args)
'''


def image(repo, image_id, tag="<none>", digest="<none>"):
    return [repo, tag, digest, "sha256:" + image_id]


def container(image_id, ref, *, running=True):
    return {"id": "container-" + image_id, "image": "sha256:" + image_id,
            "ref": ref, "running": running}


class CleanupTests(unittest.TestCase):
    def run_cleanup(self, containers, images, **options):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = root / "docker"
            executable.write_text(DOCKER_FIXTURE)
            executable.chmod(0o755)
            state_file = root / "state.json"
            state_file.write_text(json.dumps({"containers": containers,
                                              "images": images, **options}))
            env = {**os.environ, "PATH": f"{root}:{os.environ['PATH']}",
                   "DOCKER_FIXTURE_STATE": str(state_file),
                   "KEEP_PREVIOUS_RELEASES": "99"}
            result = subprocess.run(["bash", str(SCRIPT), "current"], env=env,
                                    capture_output=True, text=True, check=False)
            return result, json.loads(state_file.read_text())

    def test_removes_history_in_all_four_repositories(self):
        containers = [container("web", WEB + ":current"),
                      container("sync", SYNC + ":current"),
                      container("dozzle", DOZZLE + ":v2@sha256:d2"),
                      container("nginx", NGINX + "@sha256:n2")]
        images = [image(WEB, "web", "current"), image(WEB, "web", "latest"),
                  image(SYNC, "sync", "current"),
                  image(DOZZLE, "dozzle", digest="sha256:d2"),
                  image(NGINX, "nginx", digest="sha256:n2"),
                  image(WEB, "old-web", "previous"),
                  image(SYNC, "old-sync", "previous"),
                  image(DOZZLE, "old-dozzle", digest="sha256:d1"),
                  image(DOZZLE, "unused-latest", "latest"),
                  image(NGINX, "old-nginx", "nginx-alpine", "sha256:n1"),
                  image(NGINX, "old-nginx", "nginx-alpine", "sha256:n1"),
                  image(NGINX, "old-nginx", digest="sha256:n1"),
                  image(WEB, "multi-tag", "old-a"),
                  image(WEB, "multi-tag", "old-b"),
                  image("unrelated/repository", "other", "latest"),
                  image("<none>", "anonymous")]
        result, state = self.run_cleanup(containers, images)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertCountEqual(state["removed"], [
            WEB + ":previous", SYNC + ":previous", DOZZLE + "@sha256:d1",
            DOZZLE + ":latest", NGINX + ":nginx-alpine",
            WEB + ":old-a", WEB + ":old-b"])
        self.assertEqual({r[3] for r in state["images"]},
                         {"sha256:" + key for key in
                          ("web", "sync", "dozzle", "nginx", "other", "anonymous")})

    def test_moved_latest_tag_does_not_override_container_identity(self):
        result, state = self.run_cleanup(
            [container("actual", WEB + ":latest")],
            [image(WEB, "actual", "previous"), image(WEB, "unused", "latest")])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(state["removed"], [WEB + ":latest"])

    def test_immutable_digest_protects_index_identity_and_aliases(self):
        for ref in (DOZZLE + ":v2@sha256:d2", DOZZLE + "@sha256:d2"):
            with self.subTest(ref=ref):
                result, state = self.run_cleanup(
                    [container("platform-image", ref)],
                    [image(DOZZLE, "index", "latest"),
                     image(DOZZLE, "index", digest="sha256:d2"),
                     image(DOZZLE, "old", digest="sha256:d1")])
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(state["removed"], [DOZZLE + "@sha256:d1"])

    def test_stopped_containers_and_cross_repository_aliases_are_protected(self):
        result, state = self.run_cleanup(
            [container("shared", "other/repo:tag", running=False)],
            [image(WEB, "shared", "old"), image(WEB, "unused", "previous")])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(state["removed"], [WEB + ":previous"])

    def test_discovery_failures_abort_before_removal(self):
        for failure in ("container ls", "container inspect", "image ls"):
            with self.subTest(failure=failure):
                result, state = self.run_cleanup(
                    [container("active", WEB + ":current")],
                    [image(WEB, "unused", "previous")], fail=failure)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(state.get("removed", []), [])

    def test_no_containers_refuses_cleanup(self):
        result, state = self.run_cleanup([], [image(WEB, "unused", "previous")])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(state.get("removed", []), [])

    def test_empty_image_inventory_is_successful(self):
        result, state = self.run_cleanup([container("active", WEB + ":current")], [])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(state.get("removed", []), [])

    def test_removal_failure_is_reported_and_other_repositories_are_cleaned(self):
        result, state = self.run_cleanup(
            [container("active", WEB + ":current")],
            [image(WEB, "old", "previous"),
             image(DOZZLE, "old-dozzle", digest="sha256:d1")],
            refuse=[WEB + ":previous"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Warning: failed to remove", result.stderr)
        self.assertCountEqual(state["removed"], [WEB + ":previous", DOZZLE + "@sha256:d1"])


if __name__ == "__main__":
    unittest.main()
