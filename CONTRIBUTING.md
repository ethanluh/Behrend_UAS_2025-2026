# Contributing

Thanks for contributing to the Behrend UAS pipeline. Read [`CLAUDE.md`](CLAUDE.md)
for the repo's core conventions and [`README.md`](README.md) for the project
overview before you start.

## Branch naming

`main` is protected (PR-only, required status checks — see
[`.github/rulesets/`](.github/rulesets/)). All work happens on a feature branch.

Name branches as a **type**, a slash, and a short, hyphenated description:

```
<type>/<short-description>
```

Examples:

```
feature/new-sign-in
fix/safety-gate-stale-detection
bug/onnx-export-shape-mismatch
docs/hardware-runbook-update
```

Use one of these types:

| Type | Use for |
|------|---------|
| `feature` | A new capability or enhancement |
| `fix` | A bug fix |
| `bug` | A bug investigation/reproduction (or fix, interchangeable with `fix`) |
| `docs` | Documentation-only changes |
| `refactor` | Code restructuring with no behavior change |
| `test` | Adding or updating tests |
| `chore` | Tooling, CI, dependencies, or housekeeping |

Keep the description lowercase and hyphen-separated; aim for three or four words
that say what the branch does.

## Workflow

1. Branch off the latest `main` using the naming convention above.
2. Make your change, following the conventions in [`CLAUDE.md`](CLAUDE.md) — keep
   pure logic dependency-free, keep heavy imports lazy, and add a unit test for
   any new pure helper.
3. Run the test suites locally before opening a PR:

   ```bash
   pip install -r requirements-dev.txt
   pytest -q

   cmake -S embedded -B embedded/build
   cmake --build embedded/build --target geometry_tests
   ctest --test-dir embedded/build --output-on-failure
   ```

4. Open a PR into `main`. CI
   ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) must stay green, and
   review conversations must be resolved before merge.
