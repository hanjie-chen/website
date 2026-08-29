import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIRECTORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIRECTORY))

from container_remediation import (  # noqa: E402
    ImageReference,
    RemediationError,
    load_policy,
    parse_image_reference,
    replace_image_reference,
    select_candidates,
)
from container_ci_gate import (  # noqa: E402
    GateError,
    image_repository,
    policies_require_full_scan,
    read_tracked_images,
    select_changed_images,
)


class ContainerRemediationTests(unittest.TestCase):
    def test_parse_pinned_reference(self):
        reference = parse_image_reference("amir20/dozzle:v10.6.14@sha256:" + "a" * 64)

        self.assertEqual(reference.repository, "amir20/dozzle")
        self.assertEqual(reference.tag, "v10.6.14")
        self.assertEqual(reference.digest, "sha256:" + "a" * 64)
        self.assertEqual(reference.docker_hub_repository, "amir20/dozzle")

    def test_rejects_non_docker_hub_registry(self):
        reference = parse_image_reference("ghcr.io/example/service:v1.0.0")

        with self.assertRaises(RemediationError):
            _ = reference.docker_hub_repository

    def test_selects_only_newer_stable_tags_in_version_order(self):
        image = ImageReference("amir20/dozzle", "v10.6.14", "sha256:" + "1" * 64)
        policy = {
            "tag_regex": r"^v(?P<version>[0-9]+\.[0-9]+\.[0-9]+)$",
            "version_scheme": "semver",
        }
        records = [
            {"name": "v10.6.15", "digest": "sha256:" + "2" * 64},
            {"name": "v10.7.1", "digest": "sha256:" + "3" * 64},
            {"name": "v10.7.0-rc1", "digest": "sha256:" + "4" * 64},
            {"name": "v10.6.13", "digest": "sha256:" + "5" * 64},
            {"name": "latest", "digest": "sha256:" + "6" * 64},
        ]

        candidates = select_candidates(image, policy, records, max_candidates=10)

        self.assertEqual(
            [candidate["tag"] for candidate in candidates], ["v10.7.1", "v10.6.15"]
        )
        self.assertEqual(
            candidates[0]["image"],
            "amir20/dozzle:v10.7.1@sha256:" + "3" * 64,
        )

    def test_numeric_version_policy(self):
        image = ImageReference(
            "owasp/modsecurity-crs",
            "4-nginx-alpine-202607160307",
            None,
        )
        policy = {
            "tag_regex": r"^4-nginx-alpine-(?P<version>[0-9]{12})$",
            "version_scheme": "numeric",
        }
        records = [
            {
                "name": "4-nginx-alpine-202608050608",
                "digest": "sha256:" + "7" * 64,
            },
            {
                "name": "4-apache-202608050608",
                "digest": "sha256:" + "8" * 64,
            },
        ]

        candidates = select_candidates(image, policy, records, max_candidates=10)

        self.assertEqual(
            [candidate["tag"] for candidate in candidates],
            ["4-nginx-alpine-202608050608"],
        )

    def test_replace_requires_exactly_one_matching_reference(self):
        current = "amir20/dozzle:v10.6.14@sha256:" + "1" * 64
        candidate = "amir20/dozzle:v10.7.1@sha256:" + "2" * 64
        with tempfile.TemporaryDirectory() as directory:
            compose_file = Path(directory) / "compose.yml"
            compose_file.write_text(
                f"services:\n  dozzle:\n    image: {current}\n", encoding="utf-8"
            )

            replace_image_reference(compose_file, current, candidate)

            self.assertIn(candidate, compose_file.read_text(encoding="utf-8"))
            with self.assertRaises(RemediationError):
                replace_image_reference(compose_file, current, candidate)

    def test_load_policy_requires_named_version_group(self):
        with tempfile.TemporaryDirectory() as directory:
            config_file = Path(directory) / "config.json"
            config_file.write_text(
                json.dumps(
                    {
                        "images": {
                            "amir20/dozzle": {
                                "tag_regex": "^v[0-9]+$",
                                "version_scheme": "semver",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(RemediationError):
                load_policy(config_file, "amir20/dozzle")


class ContainerCiGateTests(unittest.TestCase):
    policies = {
        "amir20/dozzle": {
            "tag_regex": r"^v(?P<version>[0-9]+\.[0-9]+\.[0-9]+)$",
            "version_scheme": "semver",
        },
        "owasp/modsecurity-crs": {
            "tag_regex": r"^4-nginx-alpine-(?P<version>[0-9]{12})$",
            "version_scheme": "numeric",
        },
    }
    repositories = list(policies)

    @staticmethod
    def digest(character):
        return "sha256:" + character * 64

    def test_extracts_repository_from_tag_and_digest(self):
        reference = (
            "owasp/modsecurity-crs:4-nginx-alpine-202608131208@sha256:" + "a" * 64
        )

        self.assertEqual(image_repository(reference), "owasp/modsecurity-crs")

    def test_reads_tracked_images_and_ignores_first_party_images(self):
        dozzle = f"amir20/dozzle:v10.7.2@{self.digest('1')}"
        modsecurity = (
            "owasp/modsecurity-crs:4-nginx-alpine-202608131208@" + self.digest("2")
        )
        with tempfile.TemporaryDirectory() as directory:
            compose_file = Path(directory) / "compose.yml"
            compose_file.write_text(
                f"""services:
  web:
    image: ghcr.io/example/web:latest
  dozzle:
    image: {dozzle}
  nginx:
    image: \"{modsecurity}\"
""",
                encoding="utf-8",
            )

            images = read_tracked_images(compose_file, self.policies)

        self.assertEqual(
            images,
            {
                "amir20/dozzle": dozzle,
                "owasp/modsecurity-crs": modsecurity,
            },
        )

    def test_selects_only_changed_head_images(self):
        base = {
            "amir20/dozzle": "amir20/dozzle:v10.7.2@sha256:111",
            "owasp/modsecurity-crs": "owasp/modsecurity-crs:old@sha256:222",
        }
        head = {
            "amir20/dozzle": "amir20/dozzle:v10.7.4@sha256:333",
            "owasp/modsecurity-crs": "owasp/modsecurity-crs:old@sha256:222",
        }

        changed = select_changed_images(base, head, self.repositories)

        self.assertEqual(changed, ["amir20/dozzle:v10.7.4@sha256:333"])

    def test_same_tag_digest_change_is_selected(self):
        base = {
            "amir20/dozzle": "amir20/dozzle:v10.7.4@sha256:111",
            "owasp/modsecurity-crs": "owasp/modsecurity-crs:stable@sha256:222",
        }
        head = {
            "amir20/dozzle": "amir20/dozzle:v10.7.4@sha256:333",
            "owasp/modsecurity-crs": "owasp/modsecurity-crs:stable@sha256:222",
        }

        changed = select_changed_images(base, head, self.repositories)

        self.assertEqual(changed, ["amir20/dozzle:v10.7.4@sha256:333"])

    def test_without_base_selects_every_tracked_image(self):
        head = {
            "amir20/dozzle": "amir20/dozzle:v10.7.4@sha256:333",
            "owasp/modsecurity-crs": "owasp/modsecurity-crs:new@sha256:444",
        }

        changed = select_changed_images(None, head, self.repositories)

        self.assertEqual(
            changed, [head[repository] for repository in self.repositories]
        )

    def test_missing_tracked_image_fails_closed(self):
        dozzle = f"amir20/dozzle:v10.7.2@{self.digest('1')}"
        with tempfile.TemporaryDirectory() as directory:
            compose_file = Path(directory) / "compose.yml"
            compose_file.write_text(
                f"services:\n  dozzle:\n    image: {dozzle}\n",
                encoding="utf-8",
            )

            with self.assertRaises(GateError):
                read_tracked_images(compose_file, self.policies)

    def test_duplicate_tracked_image_fails_closed(self):
        dozzle = f"amir20/dozzle:v10.7.2@{self.digest('1')}"
        modsecurity = (
            "owasp/modsecurity-crs:4-nginx-alpine-202608131208@" + self.digest("2")
        )
        with tempfile.TemporaryDirectory() as directory:
            compose_file = Path(directory) / "compose.yml"
            compose_file.write_text(
                f"""services:
  dozzle:
    image: {dozzle}
  dozzle-copy:
    image: {dozzle}
  nginx:
    image: {modsecurity}
""",
                encoding="utf-8",
            )

            with self.assertRaises(GateError):
                read_tracked_images(compose_file, self.policies)

    def test_unpinned_tracked_image_fails_closed(self):
        modsecurity = (
            "owasp/modsecurity-crs:4-nginx-alpine-202608131208@" + self.digest("2")
        )
        with tempfile.TemporaryDirectory() as directory:
            compose_file = Path(directory) / "compose.yml"
            compose_file.write_text(
                f"""services:
  dozzle:
    image: amir20/dozzle:v10.7.2
  nginx:
    image: {modsecurity}
""",
                encoding="utf-8",
            )

            with self.assertRaises(GateError):
                read_tracked_images(compose_file, self.policies)

    def test_unapproved_tag_fails_closed(self):
        dozzle = f"amir20/dozzle:latest@{self.digest('1')}"
        modsecurity = (
            "owasp/modsecurity-crs:4-nginx-alpine-202608131208@" + self.digest("2")
        )
        with tempfile.TemporaryDirectory() as directory:
            compose_file = Path(directory) / "compose.yml"
            compose_file.write_text(
                f"""services:
  dozzle:
    image: {dozzle}
  nginx:
    image: {modsecurity}
""",
                encoding="utf-8",
            )

            with self.assertRaises(GateError):
                read_tracked_images(compose_file, self.policies)

    def test_invalid_digest_fails_closed(self):
        dozzle = "amir20/dozzle:v10.7.2@sha256:123"
        modsecurity = (
            "owasp/modsecurity-crs:4-nginx-alpine-202608131208@" + self.digest("2")
        )
        with tempfile.TemporaryDirectory() as directory:
            compose_file = Path(directory) / "compose.yml"
            compose_file.write_text(
                f"""services:
  dozzle:
    image: {dozzle}
  nginx:
    image: {modsecurity}
""",
                encoding="utf-8",
            )

            with self.assertRaises(GateError):
                read_tracked_images(compose_file, self.policies)

    def test_policy_change_requires_full_scan(self):
        base = self.policies
        head = {
            **self.policies,
            "amir20/dozzle": {
                **self.policies["amir20/dozzle"],
                "version_scheme": "numeric",
            },
        }

        self.assertTrue(policies_require_full_scan(base, head))
        self.assertFalse(policies_require_full_scan(base, base))

    def test_policy_repository_removal_fails_closed(self):
        head = {"amir20/dozzle": self.policies["amir20/dozzle"]}

        with self.assertRaises(GateError):
            policies_require_full_scan(self.policies, head)


if __name__ == "__main__":
    unittest.main()
