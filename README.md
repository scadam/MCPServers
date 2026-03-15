# MCP Servers Hub

This repository packages multiple Model Context Protocol (MCP) servers behind a single
Python project and deploys them to one Azure Container App with path-based routing.
Each server is mounted on its own path:

| Server      | Path               | Description                                          |
|-------------|--------------------|------------------------------------------------------|
| TaskServer  | `/taskserver/mcp`  | Unified task/approval aggregation across all systems |
| Workday     | `/workday/mcp`     | Worker profiles, leave, compensation, learning       |
| ServiceNow  | `/servicenow/mcp`  | Incidents, approvals, service catalog                |
| Salesforce  | `/salesforce/mcp`  | CRM, compliance cases, pipeline management           |
| Jira        | `/jira/mcp`        | Issues, projects, boards                             |

A shared `/healthz` endpoint returns `200 OK` for all liveness probes.

---

## Table of Contents

- [Servers & Tools](#servers--tools)
- [Prepare a Development Machine](#1-prepare-a-clean-development-machine)
- [Run and Test Locally](#2-run-and-test-locally)
- [Deploy to Azure Container Apps](#3-deploy-to-azure-container-apps)
- [Deploy to Azure Functions (alternative)](#4-deploy-to-azure-functions-alternative)
- [Project Structure](#5-project-structure)
- [Adding a New Server](#6-adding-a-new-server)

---

## Servers & Tools

### TaskServer (6 tools)

Unified orchestrator that aggregates tasks, approvals, and learning assignments from
Workday, ServiceNow, Salesforce, and Jira into a single view with nonce-gated
approval decisions.

| Tool | Type | Description |
|------|------|-------------|
| `list_items` | read | Aggregate tasks/approvals/learning across all connected systems |
| `prepare_approval_review` | read | Fetch approval detail and issue a single-use nonce for review |
| `execute_approval_decision` | write | Approve or reject with nonce validation |
| `get_item_detail` | read | Full details, comments, and transitions for a task or case |
| `add_item_comment` | write | Add a comment inline (Salesforce/Jira) |
| `execute_item_transition` | write | Update status inline |

### Workday (12 tools)

HR and employee management — worker profiles, leave requests, pay slips, learning,
and business title changes. Supports anonymous mode for local testing.

| Tool | Type | Description |
|------|------|-------------|
| `get_worker` | read | Current worker profile |
| `get_leave_balances` | read | Leave balances, eligible absence types, and booked time off |
| `get_direct_reports` | read | List direct reports |
| `get_inbox_tasks` | read | Inbox tasks (approvals and non-approvals) |
| `get_learning_assignments` | read | Required learning assignments |
| `get_pay_slips` | read | Recent pay slips |
| `get_time_off_entries` | read | Time off entries |
| `prepare_request_leave` | read | Prepare leave request form |
| `book_leave` | write | Submit a leave request |
| `prepare_change_business_title` | read | Prepare business title change form |
| `change_business_title` | write | Submit a title change |
| `search_learning_content` | read | Search the learning catalog by skills or topics |

### ServiceNow (25 tools)

IT service management — incident lifecycle, task and approval management, and full
service catalog ordering with shopping cart support.

**Incident Management**

| Tool | Type | Description |
|------|------|-------------|
| `list_incidents` | read | Search by number, text, category, state, priority, assignee |
| `show_create_incident_form` | read | Prefill create-incident form |
| `create_incident` | write | Create an incident |
| `show_update_incident_form` | read | Load current values for update form |
| `get_incident` | read | Full incident with journal (comments and work notes) |
| `update_incident` | write | Update fields, add comments or work notes |

**Task & Approval Management**

| Tool | Type | Description |
|------|------|-------------|
| `list_tasks` | read | Active tasks from the task table |
| `list_approvals` | read | Pending approvals |
| `get_approval` | read | Full approval detail with source document |
| `approve_reject` | write | Approve or reject an approval |

**Service Catalog**

| Tool | Type | Description |
|------|------|-------------|
| `list_catalog_items` | read | Search catalog items by name/description with filters |
| `list_catalog_categories` | read | Browse catalog categories |
| `get_catalog_item` | read | Full item with dynamic order form variables |
| `order_catalog_item` | write | Submit a one-off order |
| `add_to_cart` | write | Add item to shopping cart |
| `get_cart` | read | View cart contents and prices |
| `checkout_cart` | write | Submit cart order |
| `delete_cart` | write | Clear the cart |
| `remove_cart_item` | write | Remove a single line from the cart |
| `list_my_requests` | read | User's service requests and status |
| `search_reference_values` | read | Look up reference field values (e.g. cmdb_ci, sys_user) |

### Salesforce (20 tools)

CRM and compliance case management — accounts, contacts, opportunities, pipeline
dashboards, 14 compliance case types, and approval workflows.

**Task Management**

| Tool | Type | Description |
|------|------|-------------|
| `list_tasks` | read | Filter by status, priority, owner |
| `get_task` | read | Full task detail |
| `update_task` | write | Update status, priority, description, subject |

**Approvals**

| Tool | Type | Description |
|------|------|-------------|
| `list_approvals` | read | Pending approval work items |
| `approve_reject` | write | Approve or reject |

**Compliance Cases**

| Tool | Type | Description |
|------|------|-------------|
| `list_cases` | read | Filter by status, priority, compliance type, search text |
| `get_case` | read | Full case with comments |
| `show_compliance_case_form` | read | Create form prefill |
| `create_case` | write | Create a compliance case (14 types supported) |
| `update_case` | write | Update fields and add comments |

**CRM**

| Tool | Type | Description |
|------|------|-------------|
| `list_accounts` | read | Filter by search, industry, owner |
| `list_contacts` | read | Scoped to account or free-text search |
| `list_opportunities` | read | Pipeline view with stage, owner, account filters |
| `get_account_360` | read | Contacts, opportunities, events, tasks, and cases for an account |
| `get_pipeline_dashboard` | read | Stage rollups and opportunity list for funnel analysis |
| `show_create_opportunity_form` | read | Prefill opportunity form |
| `create_opportunity` | write | Create an opportunity |
| `create_opportunity_task` | write | Link a task to an opportunity |
| `show_create_event_form` | read | Event form prefill |
| `create_event` | write | Create an event (meeting) |

### Jira (12 tools)

Issue tracking and project management — JQL search, issue CRUD, transitions,
comments (auto-converted to Atlassian Document Format), and project creation.

| Tool | Type | Description |
|------|------|-------------|
| `list_issues` | read | JQL query or filter by project, status, assignee |
| `get_issue` | read | Full issue with comments and available transitions |
| `show_create_issue_form` | read | Create issue form |
| `create_issue` | write | Create in project (task, bug, story, epic) |
| `add_comment` | write | Add a comment |
| `transition_issue` | write | Move to a new status |
| `update_issue` | write | Update fields and add a comment |
| `show_create_project_form` | read | Project form |
| `create_project` | write | Create a software or business project |

---

## 1. Prepare a Clean Development Machine

- **Python 3.11** and pip (required by `pyproject.toml`). Verify with `python --version`.
- **Git** for cloning the repository.
- **Docker Desktop** for local container builds and deployment. Azure Container Registry
  (ACR) remote builds can be used when Docker is unavailable.
- **Azure CLI** with the Container Apps extension:
  ```powershell
  winget install -e --id Microsoft.AzureCLI
  az extension add --name containerapp
  ```

Once prerequisites are installed:

1. Clone the project and enter the workspace:
   ```powershell
   git clone <repo-url>
   Set-Location MCPServers\mcp_servers
   ```
2. Create and activate a virtual environment, then install dependencies:
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -e .[dev]
   ```
3. Provision local secrets by copying the example environment files:
   ```powershell
   Copy-Item env\workday.example.env  env\workday.local.env
   Copy-Item env\servicenow.example.env env\servicenow.local.env
   Copy-Item env\salesforce.example.env env\salesforce.local.env
   Copy-Item env\jira.example.env env\jira.local.env
   ```
   Update each file with tenant-specific values (none are committed to source control).

   **Workday:**

   | Variable | Purpose |
   |----------|---------|
   | `WORKDAY_CLIENT_ID` | Workday OAuth client ID |
   | `WORKDAY_CLIENT_SECRET` | Workday OAuth client secret |
   | `WORKDAY_REFRESH_TOKEN` | Workday OAuth refresh token |
   | `WORKDAY_CLIENT_CREDENTIALS` | Optional combined credential blob |
   | `WORKDAY_TOKEN_URL` | Workday OAuth token endpoint |
   | `WORKDAY_WORKERS_API_URL` | Workday workers API base URL |
   | `WORKDAY_ANONYMOUS_EMPLOYEE_ID` | *(Optional)* Skip Entra auth; use this employee ID for all requests |

   **Microsoft Entra / Graph (shared):**

   | Variable | Purpose |
   |----------|---------|
   | `AAD_APP_CLIENT_ID` | Microsoft Entra application ID |
   | `AAD_APP_TENANT_ID` | Microsoft Entra tenant ID |
   | `GRAPH_CLIENT_ID` | Microsoft Graph client ID |
   | `GRAPH_CLIENT_SECRET` | Microsoft Graph client secret |
   | `GRAPH_TENANT_ID` | Microsoft Graph tenant ID |

   **ServiceNow:**

   | Variable | Purpose |
   |----------|---------|
   | `SERVICENOW_INSTANCE_URL` | ServiceNow instance (e.g. `https://dev12345.service-now.com`) |
   | `SERVICENOW_CLIENT_ID` | ServiceNow OAuth client ID |
   | `SERVICENOW_CLIENT_SECRET` | ServiceNow OAuth client secret |

   **Salesforce:**

   | Variable | Purpose |
   |----------|---------|
   | `SALESFORCE_DOMAIN` | Salesforce org domain |
   | `SALESFORCE_CLIENT_ID` | Salesforce OAuth client ID |
   | `SALESFORCE_CLIENT_SECRET` | Salesforce OAuth client secret |

   **Jira:**

   | Variable | Purpose |
   |----------|---------|
   | `JIRA_BASE_URL` | Jira instance URL (e.g. `https://org.atlassian.net`) |
   | `JIRA_EMAIL` | Jira account email |
   | `JIRA_API_TOKEN` | Jira API token |
   | `JIRA_PROJECT_KEY` | *(Optional)* Default project key |

---

## 2. Run and Test Locally

### 2.1 Start all servers

The quickest way is to use the run script, which loads your env file and starts every
server on a single port:

```powershell
scripts\run-mcp.ps1                          # defaults: all servers, port 8080
scripts\run-mcp.ps1 -Server workday -Port 9000   # single server on a custom port
```

On Linux / macOS:

```bash
scripts/run-mcp.sh                            # defaults: all servers, port 8080
scripts/run-mcp.sh ../env/workday.local.env workday 9000   # single server
```

When running all servers the following endpoints are available:

| Endpoint | URL |
|----------|-----|
| TaskServer MCP | `http://localhost:8080/taskserver/mcp` |
| Workday MCP | `http://localhost:8080/workday/mcp` |
| ServiceNow MCP | `http://localhost:8080/servicenow/mcp` |
| Salesforce MCP | `http://localhost:8080/salesforce/mcp` |
| Jira MCP | `http://localhost:8080/jira/mcp` |
| Health check | `http://localhost:8080/healthz` |

### 2.2 Start the server directly (without a script)

```powershell
python -m mcp_servers.cli all --transport http --host 0.0.0.0 --port 8080
```

Replace `all` with `taskserver`, `workday`, `servicenow`, `salesforce`, or `jira` to
start a single server.

### 2.3 Test with MCP Inspector

1. Launch the Inspector and create a new Streamable HTTP connection.
2. Set the URL to `http://localhost:8080/workday/mcp`.
3. Provide an `Authorization: Bearer <Entra access token>` header (not required when
   `WORKDAY_ANONYMOUS_EMPLOYEE_ID` is set).
4. Invoke tools such as `get_worker` or `get_leave_balances` to confirm responses.

### 2.4 Anonymous mode

Set `WORKDAY_ANONYMOUS_EMPLOYEE_ID` in your env file to bypass Entra token validation
and Microsoft Graph employee-ID lookup. All requests will use the configured employee ID
directly. This is useful for local testing or single-user deployments where Entra auth
is not required.

---

## 3. Deploy to Azure Container Apps

### 3.1 One-time Azure setup

Sign in and create the required resources:

```powershell
az login
az account set --subscription <subscription-id>

$resourceGroup = "rg-m365copilot-mcp"
$location      = "eastus"
$registry      = "m365copilotmcpacr"

az group create --name $resourceGroup --location $location
az acr create   --name $registry --resource-group $resourceGroup --sku Standard
```

### 3.2 Provision infrastructure with Bicep

Deploy the Container Apps Environment and Container App using the provided Bicep template:

```powershell
az deployment group create `
  --name m365copilot-mcp `
  --resource-group $resourceGroup `
  --template-file infra/azure/containerapp.bicep `
  --parameters @infra/azure/parameters.m365copilot.json
```

Preview changes first with `az deployment group what-if` using the same arguments.

### 3.3 Configure secrets

Set secrets on the Container App before the first deployment (values from your vault):

```powershell
az containerapp secret set `
  --resource-group $resourceGroup `
  --name <container-app-name> `
  --secrets `
    workday-client-id=<value> `
    workday-client-secret=<value> `
    workday-refresh-token=<value> `
    workday-client-credentials=<value> `
    aad-app-client-id=<value> `
    aad-app-tenant-id=<value> `
    graph-client-id=<value> `
    graph-client-secret=<value> `
    graph-tenant-id=<value> `
    servicenow-client-id=<value> `
    servicenow-client-secret=<value>
```

### 3.4 Deploy with the deploy script

The `scripts\deploy-mcp.ps1` script handles building, pushing, and updating in one
command:

```powershell
scripts\deploy-mcp.ps1 `
  -ResourceGroup rg-m365copilot-mcp `
  -ContainerApp  m365copilot-mcp-app `
  -Registry      m365copilotmcpacr.azurecr.io
```

The script:

1. Logs in to ACR and builds the Docker image locally.
2. Pushes the image with an auto-generated timestamp tag.
3. Reads environment variable definitions from `infra/azure/envars.json`.
4. Updates the Container App with the new image and env vars.
5. Prints all live endpoints on completion.

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `-ResourceGroup` | Yes | — | Azure resource group |
| `-ContainerApp` | Yes | — | Container App name |
| `-Registry` | Yes | — | ACR login server (e.g. `myacr.azurecr.io`) |
| `-ImageName` | No | `mcp-servers` | Docker image name (without tag) |
| `-Tag` | No | Timestamp | Image tag |
| `-SkipBuild` | No | `$false` | Skip build/push; only update config |

### 3.5 Verify the deployment

```powershell
# List revisions
az containerapp revision list `
  --resource-group $resourceGroup `
  --name <container-app-name> `
  --output table

# Stream logs
az containerapp logs show `
  --resource-group $resourceGroup `
  --name <container-app-name> `
  --follow

# Quick health check
Invoke-WebRequest https://<fqdn>/healthz
```

### 3.6 Connect Copilot Studio

1. Add an MCP connection in Copilot Studio using the Container App FQDN, e.g.
   `https://<fqdn>/workday/mcp` (or `/servicenow/mcp`, `/salesforce/mcp`, `/jira/mcp`).
2. Supply `Authorization: Bearer <token>` pointing to the retrieved OAuth access token.
3. Bind `mcp-session-id` to any non-empty string.
4. Trigger tool calls while monitoring `az containerapp logs show` for validation.

---

## 4. Deploy to Azure Functions (alternative)

An Azure Functions wrapper is available in `azure_function/` for deployments where a
Function App is already provisioned. See the files in that directory for setup. The
Container App approach in Section 3 is the recommended deployment model.

---

## 5. Project Structure

```
mcp_servers/
├── Dockerfile              # Multi-stage Docker build
├── pyproject.toml           # Dependencies and project metadata
├── azure_function/          # Azure Functions wrapper (alternative deployment)
├── env/                     # Example environment files per server
├── infra/azure/             # Bicep templates and deployment parameters
├── scripts/                 # Run and deploy scripts
├── src/mcp_servers/
│   ├── cli.py               # CLI entry point & multi-server ASGI builder
│   ├── settings.py          # Pydantic-settings configuration
│   ├── auth/                # Shared Entra & token helpers
│   ├── http/                # HTTP client & retry logic
│   ├── ui/widget/           # Skybridge HTML widgets
│   ├── taskserver/          # TaskServer – unified task/approval aggregation
│   ├── workday/             # Workday – worker profiles, leave, compensation
│   ├── servicenow/          # ServiceNow – incidents, approvals, catalog
│   ├── salesforce/          # Salesforce – CRM, compliance, pipeline
│   └── jira/                # Jira – issues, projects, boards
└── tests/                   # Test suites per server
```

---

## 6. Adding a New Server

1. Create a new package under `src/mcp_servers/<system>/` with at least `server.py` and
   `__init__.py`.
2. In `server.py`, define a `build_<system>_server()` function that returns a `FastMCP`
   instance with registered tools.
3. Register the builder in the `SERVER_BUILDERS` dict in `cli.py`.
4. The server will automatically be mounted at `/<system>/mcp` when running in `all` mode.
5. Reuse shared modules in `auth/` and `http/` for consistent token handling and retries.
