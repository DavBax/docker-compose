# docker-compose

Source of truth for the homelab's Docker Compose stacks, running on `pifive` (Raspberry Pi 5). Fully GitOps: this repo is authoritative, and Arcane's git sync redeploys any stack whose compose file changes on `main`.

For deep-dive runbooks, per-container audit status, and history, see the Confluence Docker Containers hub. This file only covers what runs in CI/CD and why.

## Flow

```
Renovate (scheduled)
   → opens PR against main with a dependency bump
   → validate-compose (v3) runs, posts a results comment on the PR
   → human reviews and merges (checks are advisory — see note below)
   → Arcane git sync picks up the change on main
   → affected stack(s) redeployed on pifive
```

There is no staging branch in this flow. A `renovate-sandbox` branch was used earlier to trial the Renovate config in isolation; that trial is over and `main` is the only branch in active use now. `renovate-sandbox` may still exist in the repo/workflow triggers as a leftover and can be disregarded.

**No branch protection is configured on `main`.** Failing or pending checks do not block merges — they're informational only. Anyone merging a Renovate PR (or any PR) is relying on actually reading the check result, not on GitHub enforcing it.

## Workflows (`.github/workflows/`)

| File | Trigger | Purpose |
|---|---|---|
| `renovate.yml` | Cron, every 6h (`0 */6 * * *`) + manual dispatch | Runs Renovate (`renovatebot/github-action`) against this repo only, using `renovate.json`. Opens/updates dependency PRs. |
| `validate-compose-files-v3.yaml` | PR touching any `compose.y*ml` / `docker-compose.y*ml` | **Active validation workflow.** Runs yamllint, compose-spec JSON schema check, dclint, and a custom house-convention script (`.github/scripts/validate_compose.py`) against changed files only. Posts a single results comment on the PR and writes a step summary. |
| `validate-compose.yml` | PR touching compose files | **Disabled.** Earliest version of the validator; superseded by v3. Left in the repo for history, does not execute. |
| `validate-compose-files-v2.yaml` | PR touching compose files | **Disabled.** Intermediate version of the validator; superseded by v3. Left in the repo for history, does not execute. |
| `audit-compose-files-one-off.yaml` | Manual dispatch only | Repo-wide audit — runs the same four checks as v3 but against every compose file in the repo (via `find`, not PR diff), excluding `*-legacy/*` directories. For ad-hoc full sweeps, not tied to a PR. |

v1 and v2 are kept only as a record of how the validator evolved. They should eventually be deleted outright rather than left disabled, once nobody needs the diff history readily visible.

## Renovate config (`renovate.json`)

- Base: `config:recommended`, timezone `Europe/London`, dependency dashboard enabled.
- **Nothing automerges.** Every update type (patch, minor, major, digest, and GitHub Actions bumps) requires manual review and merge.
- Compose services in the same file are grouped into a single PR (`groupName: "{{parentDir}}"`), so one stack = one PR rather than one PR per service.
- Images still on `latest` are tracked as digest-only updates, labelled `latest-tag-tracking`, and still require review — this is a stopgap until those images are moved to real semver tags Renovate can classify properly.
- GitHub Actions version bumps in workflow files are handled separately from compose bumps and always flagged for review.

## Known gaps / not yet in place

- No branch protection — checks are visible but not enforced.
- No automated Pi catch-up after merge yet — redeploy is via Arcane's git sync polling, not a triggered call scoped to only the changed stack.
- v1/v2 validator workflows still present but disabled — pending cleanup.
