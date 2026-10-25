# WooCommerce MCP Gateway on Kubernetes

An MCP gateway project that connects multiple Model Context Protocol (MCP) servers through one backend. The project includes a WooCommerce tool server, calculator and currency-conversion servers, a web dashboard, and Kubernetes deployment resources packaged with Helm.

## Overview

The gateway provides a single MCP endpoint for discovering and invoking tools exposed by registered upstream MCP servers. The dashboard and backend API provide a UI and supporting management functionality. Docker is used to package services, and Helm manifests deploy the application stack to Kubernetes.

## Architecture

```text
User / MCP Client
       |
       v
MCP Gateway (FastAPI + MCP SDK)
       |
       +-------------------+--------------------+
       |                   |                    |
       v                   v                    v
 Calculator MCP       Currency MCP        WooCommerce MCP
       |                   |                    |
 Arithmetic tools     Currency conversion   Store/product/order tools

Dashboard Frontend ---> Dashboard API ---> PostgreSQL
                                              
Kubernetes deployment also includes:
- WordPress + WooCommerce
- MariaDB with persistent storage
- Persistent WordPress content
- PostgreSQL storage for gateway/dashboard data
- Ingress routes for the shop and dashboard
```

## Features

- **Central MCP gateway** to connect clients with tools from multiple upstream MCP servers.
- **Calculator MCP server** with addition, subtraction, multiplication, division and percentage calculations.
- **Currency MCP server** for currency conversion.
- **WooCommerce MCP server** with tools for listing products, creating products, listing orders, retrieving an order and updating order status.
- **Dashboard** built with React and Vite, backed by a FastAPI dashboard API.
- **Data persistence** using PostgreSQL, MariaDB and persistent Kubernetes volumes.
- **Containerization and orchestration** using Docker, Kubernetes, Kind and Helm.
- **Ingress routing** for the shop and dashboard in the Kubernetes setup.

## Technology Stack

- Python, FastAPI, MCP SDK
- React, Vite, Nginx
- PostgreSQL, MariaDB, WordPress, WooCommerce
- Docker, Docker Compose
- Kubernetes, Kind, Helm, Kubernetes Ingress

## Repository Structure

```text
.
├── agent.py
├── backend/
│   ├── app/
│   │   ├── ai_service.py
│   │   ├── dashboard_api.py
│   │   ├── database.py
│   │   └── gateway.py
│   ├── Dockerfile
│   └── Dashboard.Dockerfile
├── frontend/
├── infrastructure/
│   └── helm/
│       └── woocommerce-mcp/
├── mcp-servers/
│   ├── calculator/
│   ├── currency/
│   └── woocommerce/
├── docker-compose.yml
├── requirements.txt
└── test_gateway.py
```

## Prerequisites

Install the following tools before running the full stack:

- Docker Desktop with Docker Compose
- Python 3.11 or a compatible version supported by the project dependencies
- Node.js and npm
- Kubernetes CLI (`kubectl`)
- Kind (for a local Kubernetes cluster)
- Helm

## Run with Docker Compose

1. Clone the repository:

   ```bash
   git clone https://github.com/Rijin-shaji/woocommerce-mcp-gateway.git
   cd woocommerce-mcp-gateway
   ```

2. Review `docker-compose.yml` and the service configuration. Set the required environment variables and credentials in a local environment file or your shell. **Do not commit real API keys, passwords, tokens, or production credentials.**

3. Build and start the services:

   ```bash
   docker compose up --build -d
   ```

4. Check service status and logs:

   ```bash
   docker compose ps
   docker compose logs -f
   ```

Use the ports and health checks defined in `docker-compose.yml` for the local endpoints. Complete the initial WordPress/WooCommerce setup if the installer is displayed.

To stop the stack:

```bash
docker compose down
```

Use `docker compose down -v` only if you intentionally want to delete the Compose volumes and their persisted data.

## Deploy to Kubernetes with Helm

The Helm chart is located at `infrastructure/helm/woocommerce-mcp`. It contains templates for the gateway, upstream MCP servers, dashboard, WordPress/WooCommerce, MariaDB, PostgreSQL and Ingress.

1. Start your local Kubernetes cluster (for example, with Kind) and ensure `kubectl` is using the intended cluster.
2. Review `infrastructure/helm/woocommerce-mcp/values.yaml` and all templates.
3. Create the Kubernetes Secret(s) required by the deployment using your own credentials. The chart references an existing secret named `woocommerce-mcp-secrets`; verify the required keys in the manifests and application configuration before deployment. Do not put real secrets into committed values files.
4. Install or upgrade the release:

   ```bash
   helm upgrade --install woocommerce-mcp ./infrastructure/helm/woocommerce-mcp
   ```

5. Verify the release and workloads:

   ```bash
   helm list
   kubectl get pods
   kubectl get services
   kubectl get pvc
   kubectl get ingress
   ```

If the chart is configured for the `shop.local` and `dashboard.local` hostnames, configure local hostname resolution and the Ingress controller as required by your cluster. Check the chart values and Ingress controller setup for the exact local access method.

## MCP Tools

The upstream servers expose tools in these groups:

| Server | Tool examples |
| --- | --- |
| Calculator | `add`, `subtract`, `multiply`, `divide`, `calculate_percentage` |
| Currency | `convert_currency` |
| WooCommerce | `list_products`, `create_product`, `list_orders`, `get_order`, `update_order_status` |

Tool availability depends on the corresponding upstream service being healthy and registered with the gateway.

## Authentication and Configuration

The gateway uses API-key authentication. Configure a valid key through the project's intended key-management/database flow and pass it as a bearer token from the MCP client. A Kubernetes Secret environment variable alone does not guarantee that the key exists as a valid API key in the gateway database.

Keep credentials out of source control. Use Kubernetes Secrets or local environment variables, and rotate any credential that has accidentally been committed or shared.

## Testing and Troubleshooting

- Check container status with `docker compose ps` or `kubectl get pods`.
- Inspect service logs with `docker compose logs <service>` or `kubectl logs <pod-name>`.
- If the gateway returns `401 Unauthorized`, verify the bearer token and confirm it is a valid API key in the gateway's configured database.
- If WordPress opens its installation screen, complete the initial WordPress setup for that deployment.
- If Ingress hostnames do not resolve locally, verify the Ingress controller, host resolution and port mapping.
- Review the test scripts in the individual `mcp-servers/*` folders and the gateway test files before relying on a workflow.

## Project Status

The repository contains the application source, Dockerfiles, Docker Compose configuration and Helm chart for the multi-service deployment. Validate authentication, WordPress initialization and a complete client-to-gateway-to-upstream tool call in your environment before describing the entire workflow as end-to-end verified.

## Author

**Rijin Shaji**

Repository: https://github.com/Rijin-shaji/woocommerce-mcp-gateway


## Assignment Deliverables and Design Notes

- [System design and trade-offs](docs/system-design.md)
- [Threat model and security test plan](docs/threat-model.md)

These documents describe the architecture, trust boundaries, expected safeguards, and verification checklist. A listed test or mitigation should be considered complete only after it has been run and its result recorded.

## Environment-specific Helm values

The chart supports shared templates with environment-specific values files, following Helm's standard `-f` override mechanism ([Helm values documentation](https://helm.sh/docs/intro/cheatsheet/)).

- `infrastructure/helm/woocommerce-mcp/values.yaml`: shared chart defaults.
- `infrastructure/helm/woocommerce-mcp/values-local.yaml`: Kind/local image tags and local Ingress hostnames.
- `infrastructure/helm/woocommerce-mcp/values-production.yaml`: **template only**. Replace the example image registry, version tags, domains, and storage settings for your actual VPS/k3s cluster. It is not a ready-to-run production configuration and does not itself add TLS or NetworkPolicies.

### Validate and render the chart

Run these commands from the repository root in PowerShell:

```powershell
helm lint ./infrastructure/helm/woocommerce-mcp -f ./infrastructure/helm/woocommerce-mcp/values-local.yaml
helm template woocommerce-mcp ./infrastructure/helm/woocommerce-mcp -f ./infrastructure/helm/woocommerce-mcp/values-local.yaml
```

After loading the local images into Kind and creating the Kubernetes Secret expected by the chart, deploy or upgrade:

```powershell
helm upgrade --install woocommerce-mcp ./infrastructure/helm/woocommerce-mcp -f ./infrastructure/helm/woocommerce-mcp/values-local.yaml
kubectl get pods,services,pvc,ingress
```

For a VPS/k3s deployment, first customize the production template and configure the cluster's ingress controller, storage class, TLS, secret delivery, backups, and network restrictions. Then lint/render with the production values file and review the rendered manifests before deploying. Do not commit actual credentials.

## Definition-of-done checklist

Use this as a test checklist before recording the assignment walkthrough:

- [ ] A valid API key completes a real MCP client → gateway → upstream tool call.
- [ ] Missing and invalid API keys are rejected.
- [ ] Two separate users are tested; one cannot read or modify the other's protected data.
- [ ] Calculator, currency, and WooCommerce tools are discovered and invoked through the gateway.
- [ ] Tool-name collisions, a stopped upstream, and a slow upstream have documented safe outcomes.
- [ ] The Kubernetes WordPress instance is initialized and its product/order flow is tested (the Compose store has separate data).
- [ ] Pods, Services, persistent volume claims, Ingress, probes, and resource requests/limits are shown in the walkthrough.
- [ ] Local and production-like Helm values are rendered and reviewed; production settings are customized rather than left as placeholders.
- [ ] The chat agent is demonstrated acting as the authenticated user, and its tool loop is explained.
- [ ] Helm upgrade and rollback commands are documented and tested in a non-production environment.
- [ ] The video and screenshots contain no credentials, API keys, or passwords.

## Security note

The chart currently uses host-based Ingress routing without TLS in its Ingress template. Do not expose the dashboard or store publicly until HTTPS/TLS and the target cluster's access controls have been configured and tested. Internal ClusterIP Services reduce direct exposure but are not a replacement for Kubernetes NetworkPolicies where explicit network restrictions are required.
