# Threat Model

## System and security goals

The system exposes a single MCP gateway that aggregates Calculator, Currency, and WooCommerce tools. It also includes a dashboard, dashboard API, WordPress/WooCommerce, and database workloads.

Security goals:

- Only authenticated clients can invoke protected gateway operations.
- One dashboard/API user must not access another user's keys, audit records, or other tenant-owned data.
- Upstream credentials and database passwords must not be committed to source control or exposed in logs.
- A compromised or unavailable upstream MCP server must not automatically gain access to unrelated services or make the whole system hang indefinitely.
- Public access should be limited to the intended storefront and dashboard; upstream MCP services and databases should remain internal.

## Assets

- Gateway API keys and dashboard session/signing secrets.
- WooCommerce/WordPress administrator credentials and store data.
- PostgreSQL and MariaDB credentials and persistent data.
- API keys or credentials used by upstream integrations.
- Product, order, audit, and user records.
- Gateway availability and tool-call integrity.

## Trust boundaries

1. **External client → MCP Gateway:** treat all requests and tool arguments as untrusted. Validate authentication and inputs.
2. **Browser → Dashboard API:** validate login/session state and enforce authorization server-side; do not rely on UI hiding controls.
3. **Gateway → upstream MCP servers:** upstream responses and tool metadata are untrusted. Restrict network reachability and validate outputs before using them.
4. **WooCommerce MCP → WordPress/WooCommerce:** protect store credentials and apply least privilege.
5. **Application → databases:** database services should not be publicly exposed; use secrets and persistent storage with appropriate access controls.
6. **Deployment configuration → cluster:** Helm values and manifests are code and should be reviewed; production secrets must be injected separately.

## Threats and mitigations

| Threat | Potential impact | Required or recommended mitigation | Verification |
| --- | --- | --- | --- |
| Stolen or guessed API key | Unauthorized tool invocation | Validate bearer tokens server-side, use high-entropy keys, support rotation/revocation, avoid logging tokens. | Test valid, invalid, revoked, and missing tokens. |
| Cross-user/tenant data access | Exposure or modification of another user's keys, logs, or data | Enforce ownership checks in every API/database operation; scope tool access to the authenticated user where applicable. | Create two test users and prove User A cannot access User B's resources. |
| Malicious/compromised MCP server | Tool poisoning, malicious outputs, unauthorized network access | Treat tool descriptions/results as untrusted; restrict upstream permissions and egress; allowlist upstream endpoints; apply timeouts and output validation. | Simulate malformed output, unavailable service, and slow responses. |
| Tool-name collision or confusing tool metadata | Wrong tool called or unexpected behavior | Namespace tools by server, reject ambiguous names, and make routing deterministic. | Register two test tools with the same name and verify deterministic safe behavior. |
| Slow or dead upstream | Hung requests or cascading failures | Set connection/read timeouts, bound retries, return clear errors, and isolate failures per upstream. | Stop one upstream and confirm other tools remain usable. |
| Secret committed to Git | Account/store/database compromise | Commit only placeholders in `.env.example`; ignore `.env`, local DB files, and generated credentials; enable secret scanning and push protection; rotate exposed credentials. | Review tracked files and repository secret-scanning alerts before submission. |
| Public database or upstream service | Direct data theft or unauthorized operations | Keep databases and upstream MCP Services as ClusterIP; use NetworkPolicies where supported; expose only necessary ingress routes. | Inspect Service types, Ingress routes, and NetworkPolicy resources. |
| Uninitialized or weakly secured WordPress | Store compromise or demo failure | Complete installation, change defaults, keep admin credentials secret, update components, and use HTTPS for public deployments. | Confirm the deployed store is initialized and the admin credentials are not defaults. |
| Data loss after pod replacement | Loss of store or gateway state | Use persistent volumes and documented backups; test restore procedures. | Delete/recreate a non-production pod and verify expected data remains; test a backup restore. |

## Kubernetes exposure

The chart's application and database Services are intended to be internal ClusterIP Services. The optional Ingress currently routes the shop and dashboard by hostname. The current Ingress template is HTTP-only and does not configure TLS. ClusterIP is not a substitute for NetworkPolicy: add and test NetworkPolicies when the cluster requires explicit pod-to-pod restrictions.

Review actual rendered manifests and live resources rather than assuming a security property from this document:

```bash
kubectl get services -o wide
kubectl get ingress
kubectl get networkpolicy
kubectl get secrets
```

Do not print Secret values while collecting evidence.

## Secret handling

- Keep real `.env` files, local database files, credentials, and tokens out of Git.
- Use Kubernetes Secret references or an external secret manager in the target cluster.
- Commit only non-sensitive example configuration with placeholder values.
- If a real secret was pushed, revoke/rotate it; deleting it from the latest commit does not remove it from Git history.
- Never include credentials in screenshots, logs, demo recordings, or the README.

## Known verification gaps

Before claiming the system is production-ready, verify gateway authentication end-to-end, two-user isolation, WordPress initialization, upstream timeout/error handling, and the exact exposure rules in the deployed cluster. This document records the threat model and test plan; it is not evidence that each mitigation has already been implemented.
