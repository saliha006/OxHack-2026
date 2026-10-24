# Tooling - use what the project already has

Run only tools already configured in the repo (check config files, CI, package scripts). Suggesting a new
tool is a dependency decision → flag it, don't install it.

| Job | Python | JS/TS | Go | Other |
|---|---|---|---|---|
| Lint + unused imports/vars | `ruff check` | `eslint` | `go vet`, `staticcheck` | language linter |
| Types | `mypy`, `pyright` | `tsc --noEmit` | compiler | |
| Dead code | `vulture` | `knip`, `ts-prune` | `staticcheck` (U1000), `deadcode` | |
| Clones / near-duplicates | `pylint --enable=duplicate-code` | `jscpd` | `dupl` | `jscpd` (multi-language), PMD CPD |
| Complexity metrics | `ruff` (C901), `radon cc` | `eslint complexity` | `gocyclo` | SonarQube |
| Security smells | `ruff` (S rules), `bandit` | `eslint-plugin-security` | `gosec` | `semgrep` |

No tool configured? Fall back to targeted grep over the scope:
`print(`, `console.log`, `debugger`, `TODO`, `FIXME`, `except:`, `except Exception`, `catch (`, `# type: ignore`,
`@ts-ignore`, `any`, `eslint-disable`, `noqa`.
Each suppression comment needs a reason, or it goes.
