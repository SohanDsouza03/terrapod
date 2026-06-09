# Health Dashboard

Every workspace exposes a set of **health conditions** — derived signals
that surface operational problems (a broken VCS connection, detected
drift, a misconfigured agent pool) without making an operator open each
workspace to find them. The workspace list page aggregates these into
summary cards so a fleet-wide problem is visible at a glance.

Health conditions are computed on read from the workspace's current
state; there is no separate health table to keep in sync.

---

## Conditions

Each condition has a stable `code`, a `severity` (`error` or `warning`),
and a human-readable `detail`. The current set:

| Code | Severity | Raised when |
|---|---|---|
| `state_diverged` | error | The stored state version no longer matches what the runner last wrote (a divergence detected during state upload). |
| `vcs_error` | error | The workspace's VCS connection failed its last poll — expired token, unreachable repo, unparseable URL. `detail` carries the upstream error. |
| `no_agent_pool` | warning | The workspace is in `agent` execution mode but has no agent pool assigned, so runs cannot be dispatched. |
| `drifted` | warning | Drift detection is enabled and the latest drift run found out-of-band changes. |
| `drift_errored` | warning | Drift detection is enabled and the latest drift run failed. |

Drift-derived conditions (`drifted`, `drift_errored`) are **hidden when
drift detection is disabled** for the workspace — a stale drift status
from a previously-enabled period must not show as a live problem.

A workspace with no problems returns an empty condition list.

---

## API

Health conditions are embedded in the workspace JSON:API resource under
the `health-conditions` attribute, alongside the VCS polling fields used
to render the dashboard:

```jsonc
{
  "data": {
    "type": "workspaces",
    "attributes": {
      "name": "api-prod",
      "health-conditions": [
        { "code": "vcs_error", "severity": "error", "detail": "401 token expired" }
      ],
      "vcs-last-polled-at": "2026-06-09T10:00:00Z",
      "vcs-last-error": "401 token expired",
      "vcs-last-error-at": "2026-06-09T10:00:00Z"
    }
  }
}
```

Because conditions are computed from existing workspace fields, listing
workspaces returns their health in the same response — no extra request
per workspace.

---

## See Also

- [Drift Detection](drift-detection.md) — how `drifted` / `drift_errored` are produced
- [VCS Integration](vcs-integration.md) — polling and the `vcs_error` condition
- [Monitoring](monitoring.md) — Prometheus metrics for platform-level health
- [API Reference](api-reference.md) — the full workspace resource shape
