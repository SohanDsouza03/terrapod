# Contributing to Terrapod

Thanks for your interest in contributing. This guide covers the
conventions and the local workflow. For the security policy and how to
report vulnerabilities, see [SECURITY.md](SECURITY.md).

## Getting started

Terrapod runs entirely in containers — you don't need a local Python or
Node.js toolchain to build, test, or lint. You do need a local
Kubernetes cluster and [Tilt](https://tilt.dev/) for the full dev
environment. See [docs/getting-started.md](docs/getting-started.md) for
the one-time setup.

```zsh
make dev          # Start the local dev environment (Tilt, port 10352)
make dev-down     # Stop it
make test         # Run the Python test suite in Docker
make lint         # Run ruff + mypy in Docker
make help         # List every available target
```

The Go modules (`go-terrapod`, `provider`, `migrate`) each have their
own `go.mod` and are tested directly with `go test ./...` from inside
that directory — this is what CI does.

## Repository layout

| Path | What it is |
|---|---|
| `services/terrapod/` | FastAPI API server + runner listener (Python) |
| `web/` | Next.js frontend (TypeScript) |
| `go-terrapod/` | Public Go SDK for the Terrapod API |
| `provider/` | `terraform-provider-terrapod` (uses the SDK) |
| `migrate/` | `terrapod-migrate` TFE/Atlantis migration tool (uses the SDK) |
| `helm/` | Helm chart (the only supported deployment path) |
| `docs/` | MkDocs (Material) documentation site |

## Branches and commits

- Create a feature branch off `main`; never push directly to `main`.
- Use [Conventional Commits](https://www.conventionalcommits.org/):
  `feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`, `ci:`.
  Scopes are welcome (e.g. `fix(go-terrapod): ...`). Release notes are
  generated from these prefixes, so getting them right matters.
- Keep each commit a single logical change.

## Before opening a pull request

1. Run the relevant tests and linters and make sure they pass:
   - Python: `make test` and `make lint`
   - A Go module: `go vet ./...`, `go build ./...`, and
     `go test ./...` from within `go-terrapod/`, `provider/`, or
     `migrate/`.
   - Frontend: `npm run lint` and `npm run type-check` in `web/`.
2. Add or update tests for any behaviour change.
3. Update the docs in `docs/` when you change user-facing behaviour.
4. Fill in the pull request template with a clear description.

CI runs the full matrix (lint, test, security scans, image builds, and
E2E) on every PR; all checks must pass before merge.

## Discussing larger changes

For architecture questions or substantial changes, open an issue first
so the approach can be discussed before you invest in an implementation.
