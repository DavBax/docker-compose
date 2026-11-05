# docker-compose

Source of truth for the homelab's Docker Compose stacks, running on `pifive` (Raspberry Pi 5). Fully GitOps: this repo is authoritative, and Arcane's git sync redeploys any stack whose compose file changes on `main`.

For deep-dive runbooks, per-container audit status, and history, see the Confluence Docker Containers hub. This file only covers what runs in CI/CD and why.

## Flow

```
Renovate (scheduled)
   → opens or updates dependency PRs against main
   → Secret Scan runs on every PR; compose validation runs when compose files change
   → Docker Compose patch PRs are configured for GitHub automerge; other updates need human review
   → Arcane git sync picks up the change on main
   → affected stack(s) redeployed on pifive
```

There is no staging branch in this flow. A `renovate-sandbox` branch was used earlier to trial the Renovate config in isolation. The compose validation workflows still include it in their PR branch filters, so remove that filter if the branch is no longer in use.

Branch protection is enabled on `main`. The required status checks and whether they gate Renovate automerge are configured in GitHub, not in this repository.

## Workflows (`.github/workflows/`)

| File | Trigger | Purpose |
|---|---|---|
| `renovate.yml` | Cron, every 3h (`0 */3 * * *`) + manual dispatch | Runs Renovate (`renovatebot/github-action`) against this repo only, using `renovate.json`. Opens/updates dependency PRs. |
| `validate-compose-files-v3.yaml` | PR to `main` or `renovate-sandbox` touching a compose file | **Current validator.** Runs yamllint, compose-spec JSON schema check, dclint, and a custom house-convention script (`.github/scripts/validate_compose.py`) against changed files. The report job posts a results comment and step summary when it runs. |
| `secret-scan.yaml` | Push to `main`, every PR, or manual dispatch | Runs Gitleaks secret scanning. |
| `validate-compose.yml` | Disabled in GitHub Actions; file declares a PR trigger | Legacy v1 validator, retained for history. |
| `validate-compose-files-v2.yaml` | Disabled in GitHub Actions; file declares a PR trigger | Legacy v2 validator, retained for history. |
| `audit-compose-files-one-off.yaml` | Manual dispatch only | Repo-wide audit — runs the same four checks as v3 but against every compose file in the repo (via `find`, not PR diff), excluding `*-legacy/*` directories. For ad-hoc full sweeps, not tied to a PR. |

v1 and v2 are disabled in GitHub Actions and should eventually be deleted or have their triggers removed once nobody needs the diff history readily visible.

## Renovate config (`renovate.json`)

- Base: `config:recommended`, timezone `Europe/London`, dependency dashboard enabled.
- Docker Compose patch updates are configured for PR automerge (`automerge: true`, `platformAutomerge: true`). Whether required checks gate the merge depends on GitHub's branch protection/ruleset settings.
- Minor, major, and digest updates, plus GitHub Actions updates, have automerge disabled and require manual review.
- Compose services in the same file are grouped into a single PR (`groupName: "{{parentDir}}"`), so one stack = one PR rather than one PR per service.
- Images still on `latest` are tracked as digest-only updates, labelled `latest-tag-tracking`, and require review — this is a stopgap until those images are moved to real semver tags Renovate can classify properly.
- GitHub Actions version bumps in workflow files are handled separately from compose bumps and always require review.

## Known gaps / not yet in place

- Branch protection is enabled on `main`; confirm required-check settings in GitHub before relying on them to gate Renovate automerge.
- No automated Pi catch-up after merge yet — redeploy is via Arcane's git sync polling, not a triggered call scoped to only the changed stack.
- v1/v2 validator workflows are disabled in GitHub Actions but still have PR triggers in their files; clean them up when convenient.
