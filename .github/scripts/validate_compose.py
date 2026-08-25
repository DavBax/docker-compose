#!/usr/bin/env python3
"""
Validates docker compose files changed in a PR:
  1. Structural validity via `docker compose config` (dummy secret files
     are created first, since real secrets live outside git in ./secrets/
     and are gitignored - see 01_New_Container_Process convention).
  2. House convention: any service with traefik labels AND more than one
     network must set traefik.docker.network explicitly (see PR #1).

Exits non-zero (failing the check) on any problem found, with a summary
printed for each file. Deleted files in the PR are skipped.
"""
import os
import subprocess
import sys

import yaml

FAILED = False


def fail(msg):
    global FAILED
    FAILED = True
    print(f"::error::{msg}")


def ensure_dummy_secrets(compose_path, data):
    """Create empty placeholder files for any top-level `secrets:` entries
    that reference a relative file path, so `docker compose config` doesn't
    choke on secrets that are deliberately excluded from git."""
    secrets = data.get("secrets") or {}
    compose_dir = os.path.dirname(compose_path) or "."
    for name, spec in secrets.items():
        file_ref = spec.get("file") if isinstance(spec, dict) else None
        if not file_ref:
            continue
        if file_ref.startswith("/"):
            continue
        full_path = os.path.normpath(os.path.join(compose_dir, file_ref))
        if not os.path.exists(full_path):
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write("dummy-value-for-ci-validation\n")
            print(f"  created dummy secret file: {full_path}")


def check_structural_validity(compose_path):
    result = subprocess.run(
        ["docker", "compose", "-f", compose_path, "config", "-q"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        fail(f"{compose_path}: docker compose config failed:\n{result.stderr.strip()}")
    else:
        print("  structural validation passed")


def check_traefik_network_label(compose_path, data):
    services = data.get("services") or {}
    for name, svc in services.items():
        if not isinstance(svc, dict):
            continue
        labels = svc.get("labels") or []

        if isinstance(labels, dict):
            has_traefik_enable = str(labels.get("traefik.enable", "")).lower() == "true"
            has_network_label = "traefik.docker.network" in labels
        else:
            has_traefik_enable = any(
                str(l).strip().strip('"').strip("'") == "traefik.enable=true" for l in labels
            )
            has_network_label = any(
                str(l).strip().strip('"').strip("'").startswith("traefik.docker.network=")
                for l in labels
            )

        networks = svc.get("networks") or []
        network_count = len(networks) if isinstance(networks, (list, dict)) else 0

        if has_traefik_enable and network_count > 1 and not has_network_label:
            fail(
                f"{compose_path}: service '{name}' has traefik.enable=true and "
                f"{network_count} networks but no traefik.docker.network label "
                f"(house convention - see PR #1)"
            )


def main(changed_files):
    if not changed_files:
        print("No changed compose files to validate.")
        return

    for path in changed_files:
        if not os.path.exists(path):
            print(f"Skipping {path} (deleted in this PR)")
            continue

        print(f"Validating {path}")
        with open(path) as f:
            try:
                data = yaml.safe_load(f) or {}
            except yaml.YAMLError as e:
                fail(f"{path}: YAML parse error: {e}")
                continue

        ensure_dummy_secrets(path, data)
        check_structural_validity(path)
        check_traefik_network_label(path, data)

    if FAILED:
        print("\nOne or more compose files failed validation.")
        sys.exit(1)
    print("\nAll changed compose files passed validation.")


if __name__ == "__main__":
    main(sys.argv[1:])
