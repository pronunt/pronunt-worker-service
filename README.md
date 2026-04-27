# pronunt-worker-service

Consumes queue events, normalizes PR data, and forwards it downstream.

## Stack

* FastAPI
* Docker Hardened Images with multi-stage builds
* Kubernetes raw manifests in `k8s/`
* Helm chart in `helm/`
* GitHub Actions workflow in `.github/workflows/`

## Branching

This repository follows trunk-based development with `main` as the long-lived branch.

CI note: merged PRs should carry the `build` label when image publication is expected.
Release note: April 2026 release automation verification touch.
