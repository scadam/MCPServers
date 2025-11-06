# MCP Servers Hub

This workspace packages multiple Model Context Protocol (MCP) servers behind a single
Python project. The first server targets Workday and exposes tool-based APIs that can be
invoked from any compliant MCP client such as MCP Inspector or Microsoft Copilot Studio.

---

## 1. Prepare a Clean Development Machine

- **Python 3.11** and pip (required by `pyproject.toml`). Verify with `python --version`.
- **Git** for cloning the repository.
- **Node/npm (optional)** only if you plan to use the MCP Inspector desktop app; the
  published binaries are sufficient otherwise.
- **Docker Desktop (optional)** for local container builds. Azure Container Registry (ACR)
  remote builds can be used when Docker is unavailable.
- **Azure CLI** with the Container Apps extension:
  ```powershell
  winget install -e --id Microsoft.AzureCLI
  az extension add --name containerapp
  ```

Once prerequisites are installed:

1. Clone the project and enter the MCP workspace:
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
3. Provision local secrets by copying the example environment file:
   ```powershell
   Copy-Item env\workday.example.env .env.workday
   ```
   Update the new file with tenant-specific values. The server expects the following keys
   (none are committed to source control):
   - `WORKDAY_CLIENT_ID`, `WORKDAY_CLIENT_SECRET`, `WORKDAY_REFRESH_TOKEN`
   - `AAD_APP_CLIENT_ID`, `AAD_APP_TENANT_ID`
   - `GRAPH_CLIENT_ID`, `GRAPH_CLIENT_SECRET`, `GRAPH_TENANT_ID`
   - Optional overrides for `WORKDAY_TOKEN_URL`, `WORKDAY_WORKERS_API_URL`, etc.
4. If you plan to deploy, also copy `infra/azure/parameters.example.json` to
   `infra/azure/parameters.workday.json` and populate the parameter values for your
   subscription (registry name, resource group, container image, environment variables).

---

## 2. Run and Test the Workday MCP Server Locally

1. Ensure the virtual environment is active (`.venv\Scripts\Activate.ps1`).
2. Export environment variables for the session. The simplest path is to use the provided
   script, which loads `.env.workday` and starts the server in HTTP mode:
   ```powershell
   scripts\run-workday.ps1
   ```
   The script binds to `http://127.0.0.1:8080/mcp` with structured logging enabled.
3. Alternatively, start the server manually:
   ```powershell
   python -m mcp_servers.cli workday --transport http --host 0.0.0.0 --port 8080
   ```
4. Test with **MCP Inspector**:
   - Launch the Inspector and create a new HTTP connection.
   - Use the base URL `http://localhost:8080/mcp`.
   - Provide an `Authorization: Bearer <Entra access token>` header and a
     `mcp-session-id` header (any non-empty GUID works for local testing).
   - Invoke tools such as `get_worker` or `get_leave_balances` to confirm responses.
5. Watch server output for debug statements (e.g., `auth_token_resolved_from_header`) and
   stack traces that highlight missing secrets or invalid tokens.

---

## 3. Deploy to Azure Container Apps

### 3.1 One-time Azure setup

- Sign in and select the target subscription:
  ```powershell
  az login
  az account set --subscription <subscription-id>
  ```
- Create (or reuse) a resource group and Azure Container Registry (ACR):
  ```powershell
  $resourceGroup = "rg-workday-mcp"
  $location = "eastus"
  $registry = "workdaymcpacr"
  az group create --name $resourceGroup --location $location
  az acr create --name $registry --resource-group $resourceGroup --sku Standard
  ```

### 3.2 Configure deployment parameters

1. Edit `infra/azure/parameters.workday.json` with your values:
   - `containerImage`: fully qualified name, e.g., `workdaymcpacr.azurecr.io/workday-mcp:v3`
   - `containerRegistryServer`: registry login server, `workdaymcpacr.azurecr.io`
   - `envVars`: include non-secret environment variables (`MCP_SERVER`, `LOG_LEVEL`, etc.).
2. Secrets are never stored in the parameter file. Record the values you will later inject
   into the Container App:
   - Workday OAuth secrets (`workday-client-id`, `workday-client-secret`, `workday-refresh-token`)
   - Microsoft Entra application identifiers (`aad-app-client-id`, `aad-app-tenant-id`)
   - Microsoft Graph credentials (`graph-client-id`, `graph-client-secret`, `graph-tenant-id`)
   - Optional bundled secret `workday-client-credentials` if you prefer a single blob.

### 3.3 Provision infrastructure with Bicep

Deploy the Azure resources defined in `infra/azure/containerapp.bicep`:

```powershell
$deploymentName = "workday-mcp"
az deployment group what-if `
  --name $deploymentName `
  --resource-group $resourceGroup `
  --template-file infra/azure/containerapp.bicep `
  --parameters @infra/azure/parameters.workday.json

az deployment group create `
  --name $deploymentName `
  --resource-group $resourceGroup `
  --template-file infra/azure/containerapp.bicep `
  --parameters @infra/azure/parameters.workday.json
```

### 3.4 Build and push the container image

Remote builds avoid local Docker requirements:

```powershell
$imageName = "workday-mcp:v3"
az acr build `
  --registry $registry `
  --image $imageName `
  .
```

### 3.5 Configure secrets and update the Container App

1. Set secrets on the Container App (values pulled from your vault or secret store):
   ```powershell
   az containerapp secret set `
     --resource-group $resourceGroup `
     --name workday-mcp-app `
     --secrets \
       workday-client-id=<value> \
       workday-client-secret=<value> \
       workday-refresh-token=<value> \
       aad-app-client-id=<value> \
       aad-app-tenant-id=<value> \
       graph-client-id=<value> \
       graph-client-secret=<value> \
       graph-tenant-id=<value> \
       workday-client-credentials=<value>
   ```
2. Deploy the freshly built image:
   ```powershell
   az containerapp update `
     --resource-group $resourceGroup `
     --name workday-mcp-app `
     --image "$registry.azurecr.io/$imageName"
   ```
3. Verify the revision and stream logs during testing:
   ```powershell
   az containerapp revision list --resource-group $resourceGroup --name workday-mcp-app --output table
   az containerapp logs show --resource-group $resourceGroup --name workday-mcp-app --follow
   ```
4. Test the public endpoint (replace with the provisioned FQDN):
   ```powershell
   Invoke-WebRequest https://workday-mcp-app.<unique-id>.$location.azurecontainerapps.io/mcp -Method Get
   ```

### 3.6 Connect Copilot Studio (optional)

- Configure the MCP connection with the Container App URL.
- Supply `Authorization: Bearer <token>` using the expression picker that points to the
  retrieved OAuth access token.
- Bind `mcp-session-id` to any non-empty string (a stored expression or literal).
- Trigger tool calls while monitoring `az containerapp logs show` for validation.

---

## 4. Deploy to an Existing Azure Function App

The repository now ships a turnkey Azure Functions payload in `azure_function/`. Use this
when you already have a Function App provisioned (consumption or premium plan).

### 4.1 Install local tooling (one time)

1. Ensure the Azure CLI is available as described earlier (`az --version`).
2. Install **Azure Functions Core Tools v4** so you can run the project locally:
   ```powershell
   winget install -e --id Microsoft.AzureFunctionsCoreTools
   ```
3. Keep using Python 3.11 and the virtual environment configured in Section 1.

### 4.2 Run the Function locally for testing

1. Restore dependencies for development:
   ```powershell
   pip install -e .[dev]
   ```
2. Seed local settings by copying the sample file that lives alongside the function assets:
   ```powershell
   Set-Location azure_function
   Copy-Item local.settings.sample.json local.settings.json
   ```
3. Edit `azure_function/local.settings.json` and populate the same secrets described in
   Section 1 (Workday OAuth, Entra, Microsoft Graph). For any value you do not need, leave
   it empty but keep the key in place.
4. From the `azure_function` directory, start the Azure Functions host:
   ```powershell
   func start
   ```
   The host listens on `http://localhost:7071`. Any request path is forwarded to the MCP
   server—for example `http://localhost:7071/mcp` mirrors the HTTP experience from
   `scripts\run-workday.ps1`.
5. Issue test requests (PowerShell example) and monitor the console for logs:
   ```powershell
   Invoke-WebRequest http://localhost:7071/mcp -Headers @{"mcp-session-id" = [guid]::NewGuid()}
   ```
6. Stop the Functions host with **Ctrl+C** when you are done. The standalone scripts in
   Section 2 continue to work; this addition simply provides another local option.

### 4.3 Configure the Function App in Azure

1. Set or update the application settings on the existing Function App. The following
   command applies the same keys that the container deployment uses (replace `...` with
   your secrets):
   ```powershell
   az functionapp config appsettings set `
     --resource-group <rg-name> `
     --name <function-app-name> `
     --settings \
       MCP_SERVER=workday \
       LOG_LEVEL=info \
       WORKDAY_CLIENT_ID=... \
       WORKDAY_CLIENT_SECRET=... \
       WORKDAY_REFRESH_TOKEN=... \
       AAD_APP_CLIENT_ID=... \
       AAD_APP_TENANT_ID=... \
       GRAPH_CLIENT_ID=... \
       GRAPH_CLIENT_SECRET=... \
       GRAPH_TENANT_ID=...
   ```
2. Confirm the Function App is running on the Python 3.11 runtime (`FUNCTIONS_WORKER_RUNTIME`
   should already be `python`). Adjust in the Azure portal if required.

### 4.4 Publish code to the Function App

1. Return to the project root (`mcp_servers/`) and activate your virtual environment.
2. Run the deployment helper that now lives in `scripts/deploy-function.ps1`. Provide the
   existing resource group and Function App name:
   ```powershell
   scripts\deploy-function.ps1 -ResourceGroup <rg-name> -FunctionApp <function-app-name>
   ```
   The script performs the following:
   - Copies the contents of `azure_function/` into a temporary publish folder.
   - Bundles the `src/mcp_servers` package alongside the Function entry point.
   - Installs Python dependencies defined in `azure_function/requirements.txt` into
     `.python_packages/lib/site-packages` (the layout Azure Functions expects).
   - Compresses everything into `azure_function/functionapp.zip` and uploads it using
     `az functionapp deployment source config-zip`.
3. Wait for the command to complete. A success message (`Deployment complete.`) indicates
   the ZIP has been accepted by Azure.

### 4.5 Validate the deployed Function

1. Retrieve the default function key. The example below stores it in `$key`:
   ```powershell
   $key = az functionapp keys list `
     --resource-group <rg-name> `
     --name <function-app-name> `
     --output tsv `
     --query "functionKeys.default"
   ```
2. Call the production endpoint, including the `code` query parameter and your usual MCP
   headers. Replace `<app-hostname>` with the Function App URL:
   ```powershell
   Invoke-WebRequest "https://<app-hostname>/mcp?code=$key" `
     -Headers @{"mcp-session-id" = [guid]::NewGuid(); "Authorization" = "Bearer <token>"}
   ```
3. Use `az monitor activity-log list` or the Azure portal **Monitor > Logs** blade to view
   execution traces if you need to troubleshoot. The scripted deployment does not change
   your existing Container Apps flow—the two options can coexist.

---

## Extending Beyond Workday

- Create new packages under `src/mcp_servers/<system>` with `helpers.py`, `tools.py`, and
  `server.py` mirroring the Workday structure.
- Reuse shared authentication modules to enforce consistent token validation.
- Register additional servers in `mcp_servers/cli.py` once their tools are ready.

The combination of local scripts, parameterized Bicep templates, and ACR-based builds keeps
the repository free of secrets while allowing repeatable deployment from clean machines.
