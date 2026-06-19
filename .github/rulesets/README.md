# Branch protection for `main`

[`main-protection.json`](main-protection.json) is a GitHub **repository ruleset**
(ruleset-as-code) that protects the `main` branch. It is not applied
automatically — an admin has to import it once. It encodes:

- **No direct pushes / no deletion / no force-push** to `main` — all changes go
  through a pull request.
- **Required status checks:** the `python` and `cpp` jobs from
  [`../workflows/ci.yml`](../workflows/ci.yml) must pass, and the branch must be
  up to date with `main` before merging (`strict` policy).
- **Required conversation resolution** — review threads must be resolved.
- **Linear history** — matches the squash-merge workflow.
- **Required approvals: 0** — set this way so a solo author isn't permanently
  blocked (GitHub forbids approving your own PR). Bump
  `required_approving_review_count` to `1` once there's a second maintainer.

## Apply it (pick one)

### A. GitHub UI (no tooling needed)
`Settings → Rules → Rulesets → New ruleset → Import a ruleset`, then select this
file and click **Create**.

### B. `gh` CLI (needs admin token)
```bash
gh api --method POST \
  -H "Accept: application/vnd.github+json" \
  /repos/ethanluh/Behrend_UAS_2025-2026/rulesets \
  --input .github/rulesets/main-protection.json
```

To update an existing ruleset later, find its id with
`gh api /repos/ethanluh/Behrend_UAS_2025-2026/rulesets` and `PUT` to
`/repos/.../rulesets/{id}` with the edited file.

> The exact check names (`python`, `cpp`) must match the job names in
> `ci.yml`. If you rename a CI job, update the `required_status_checks` contexts
> here too.
