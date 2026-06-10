# Phase 1 — Step 2: Root `Makefile`

## What Was Done
The root `Makefile` already existed with all targets pre-defined.
No file was created — this step confirms the Makefile is correct and usable.

### Targets defined

| Group | Targets |
|---|---|
| Setup | `init`, `sync` |
| Code quality | `lint`, `format`, `type-check` |
| Tests | `test`, `test-unit`, `test-int`, `test-cov`, `test-spark`, `test-tcin`, `test-core`, `test-openai`, `test-thinktank` |
| Run locally | `run-spark`, `run-tcin` |
| Build | `build`, `build-libs`, `build-spark`, `build-tcin` |
| Clean | `clean` |

## How to Validate

### 1 — File exists
```
type Makefile
```
Expected: file prints with all targets visible.

### 2 — Help target works
```
make help
```
Expected: prints the full help menu grouped by `[Setup]`, `[Code quality]`, `[Tests]`, `[Run locally]`, `[Build]`, `[Clean]`.

### 3 — Make is on PATH
```
make --version
```
Expected: prints `GNU Make 3.x` or higher.
