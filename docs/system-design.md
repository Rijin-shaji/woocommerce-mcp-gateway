# System Design and Trade-offs

## Scope

This repository implements an MCP gateway that aggregates tools from three upstream MCP servers: Calculator, Currency, and WooCommerce. It also includes a React/Vite dashboard, a FastAPI dashboard API, and a Helm chart for a Kubernetes deployment.

The design separates tool providers from the client-facing gateway so an MCP client can discover and invoke tools through one endpoint rather than connecting to every server independently.

## Component responsibilities

| Component | Responsibility | Kubernetes exposure |
| --- | --- | --- |
| MCP Gateway | Connects to upstream MCP servers, discovers their tools, and exposes the gateway MCP endpoint. | ClusterIP Service; use port-forward or add an explicitly secured ingress if remote MCP access is required. |
| Calculator MCP | Arithmetic and percentage tools. | ClusterIP Service; internal service-to-service traffic. |
| Currency MCP | Currency conversion tool. | ClusterIP Service; internal service-to-service traffic. |
| WooCommerce MCP | Product and order tools backed by WooCommerce. | ClusterIP Service; internal service-to-service traffic. |
| Dashboard frontend | Browser UI for the project. | Served through the dashboard Ingress host when Ingress is enabled. |
| Dashboard API | Dashboard authentication and management API. | ClusterIP Service behind the frontend/deployment setup. |
| WordPress + WooCommerce | Storefront, catalog, cart, checkout, and order management. | Routed through the shop Ingress host when enabled. |
| MariaDB | WordPress/WooCommerce database. | ClusterIP Service with persistent storage. |
| PostgreSQL | Gateway/dashboard data storage. | ClusterIP Service with persistent storage. |

The Helm chart also contains configuration for MongoDB and Redis. Verify which application paths use them before describing them as required runtime dependencies.

## Request flow

1. An MCP client connects to the gateway endpoint and presents a valid gateway API key.
2. The gateway validates the token against its configured API-key store.
3. The gateway routes a requested tool to the matching upstream MCP server.
4. The upstream server performs the operation and returns a result.
5. The gateway returns the result to the client.

For a WooCommerce operation, the tool server communicates with the WordPress/WooCommerce deployment. Product and order operations should be tested against the same Kubernetes WordPress instance that is being demonstrated; a separate Docker Compose instance has separate data.

## Kubernetes and deployment

The Helm chart is under `infrastructure/helm/woocommerce-mcp`. It defines application Deployments and Services, WordPress and database workloads, persistent volume claims, and an optional Ingress. Most application services use ClusterIP, so they are not directly exposed as public LoadBalancer services.

The default `values.yaml` is a local-oriented baseline: it uses local image tags and disables Ingress by default. Use the separate local values file for a Kind demo. The production values file is a template and must be customized with real registry image names/tags, hostnames, storage settings, and cluster-specific configuration before deployment.

### Local deployment

From the repository root, after building/loading the images into Kind and creating the required Kubernetes Secret:

```powershell
helm lint ./infrastructure/helm/woocommerce-mcp -f ./infrastructure/helm/woocommerce-mcp/values-local.yaml
helm template woocommerce-mcp ./infrastructure/helm/woocommerce-mcp -f ./infrastructure/helm/woocommerce-mcp/values-local.yaml
helm upgrade --install woocommerce-mcp ./infrastructure/helm/woocommerce-mcp -f ./infrastructure/helm/woocommerce-mcp/values-local.yaml
```

Check the rendered manifests and live cluster before assuming that a deployment is healthy:

```powershell
kubectl get pods,services,pvc,ingress
kubectl get events --sort-by=.metadata.creationTimestamp
```

### Production-like deployment

Use the same chart with `values-production.yaml`, but only after replacing all example registry and domain values and confirming the target cluster's storage class and ingress controller:

```bash
helm lint ./infrastructure/helm/woocommerce-mcp -f ./infrastructure/helm/woocommerce-mcp/values-production.yaml
helm template woocommerce-mcp ./infrastructure/helm/woocommerce-mcp -f ./infrastructure/helm/woocommerce-mcp/values-production.yaml
helm upgrade --install woocommerce-mcp ./infrastructure/helm/woocommerce-mcp -f ./infrastructure/helm/woocommerce-mcp/values-production.yaml
```

The current Ingress template configures host-based HTTP routing only; it does not currently configure TLS. Add and test TLS configuration (for example, a cert-manager-managed TLS Secret) before using this chart for a public production deployment. Also add and validate NetworkPolicies if the target cluster needs network-level restrictions beyond ClusterIP service exposure.

## Trade-offs and limitations

- **One gateway endpoint:** simplifies client configuration and tool discovery, but makes the gateway a shared dependency and a security boundary.
- **Separate MCP servers:** keeps tool implementations isolated by responsibility, but introduces service discovery, timeout, and partial-failure handling requirements.
- **Helm values per environment:** avoids duplicating templates between local and VPS deployments, but values files alone cannot replace missing production capabilities such as TLS or NetworkPolicies.
- **Persistent volumes:** preserve state across pod replacement, but backup, restore, capacity, and storage-class behavior must be validated for the target environment.
- **API-key authentication:** protects the gateway only when token verification and per-user authorization are correctly implemented and tested. Authentication alone does not prove tenant isolation.

## Verification status

Treat the following as acceptance checks, not as claims that have automatically passed:

- A valid API key completes a client → gateway → upstream tool call.
- An invalid key is rejected.
- Two different users cannot read or modify each other's protected data.
- A missing or slow upstream produces a bounded, understandable failure.
- WordPress/WooCommerce is initialized and product/order operations work in the Kubernetes deployment.
- Helm rendering succeeds with both environment values files.
- The production deployment has TLS, appropriate network restrictions, resource settings, persistence, and a documented rollback procedure.
