<#
.SYNOPSIS
    Build, push, and deploy the MCP servers container to Azure Container Apps.

.DESCRIPTION
    One-command deployment for all MCP servers (taskserver, workday, servicenow,
    salesforce, jira).  Builds the Docker image, pushes it to Azure Container
    Registry, and updates the Azure Container App with the new image and
    environment variables from infra/azure/envars.json.

.PARAMETER ResourceGroup
    Azure resource group containing the Container App.

.PARAMETER ContainerApp
    Name of the Azure Container App to update.

.PARAMETER Registry
    ACR login server (e.g. m365copilotmcpacr.azurecr.io).

.PARAMETER ImageName
    Docker image name (without tag). Defaults to 'mcp-servers'.

.PARAMETER Tag
    Docker image tag. Defaults to a timestamp like '20260208-193000'.

.PARAMETER SkipBuild
    Skip the Docker build/push and only update the Container App config.

.EXAMPLE
    .\deploy-mcp.ps1 -ResourceGroup rg-m365copilot-mcp -ContainerApp m365copilot-mcp-app -Registry m365copilotmcpacr.azurecr.io
#>
param(
    [string]$ResourceGroup  = "rg-m365copilot-mcp",
    [string]$ContainerApp   = "m365copilot-mcp-app",
    [string]$Registry       = "m365copilotmcpacr.azurecr.io",
    [string]$ImageName      = "mcp-servers",
    [string]$Tag            = (Get-Date -Format "yyyyMMdd-HHmmss"),
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

$scriptRoot   = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot  = Split-Path $scriptRoot -Parent
$envarsFile   = Join-Path $projectRoot "infra\azure\envars.json"
$fullImage    = "$Registry/${ImageName}:${Tag}"

Write-Host "=== MCP Servers Deployment ===" -ForegroundColor Cyan
Write-Host "Resource Group : $ResourceGroup"
Write-Host "Container App  : $ContainerApp"
Write-Host "Image          : $fullImage"
Write-Host ""

# ── 1. Build & push ─────────────────────────────────────────────────
if (-not $SkipBuild) {
    $acrName = $Registry -replace '\.azurecr\.io$',''

    # Try local Docker first; fall back to ACR Build (cloud-side build)
    $useAcrBuild = $false
    try {
        docker info 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) { $useAcrBuild = $true }
    } catch {
        $useAcrBuild = $true
    }

    if ($useAcrBuild) {
        Write-Host "[1/3] Docker not available — using ACR Build (cloud)..." -ForegroundColor Yellow
        az acr build --registry $acrName --image "${ImageName}:${Tag}" $projectRoot --no-logs
        if ($LASTEXITCODE -ne 0) { throw "ACR Build failed." }
    } else {
        Write-Host "[1/3] Logging in to ACR..." -ForegroundColor Yellow
        az acr login --name $acrName

        Write-Host "[1/3] Building Docker image..." -ForegroundColor Yellow
        docker build -t $fullImage $projectRoot
        if ($LASTEXITCODE -ne 0) { throw "Docker build failed." }

        Write-Host "[1/3] Pushing image to $Registry..." -ForegroundColor Yellow
        docker push $fullImage
        if ($LASTEXITCODE -ne 0) { throw "Docker push failed." }
    }
} else {
    Write-Host "[1/3] Skipping build/push (--SkipBuild)." -ForegroundColor DarkGray
}

# ── 2. Prepare environment variables ────────────────────────────────
Write-Host "[2/3] Reading environment variables from envars.json..." -ForegroundColor Yellow
if (-not (Test-Path $envarsFile)) {
    throw "Environment variables file not found at $envarsFile."
}

$envars = Get-Content $envarsFile -Raw | ConvertFrom-Json

# Build the --set-env-vars argument list.  Secret-referenced vars use
# secretref:<name>, plain vars use the value directly.
$envVarArgs = @()
foreach ($e in $envars) {
    if ($e.PSObject.Properties.Name -contains "secretRef") {
        $envVarArgs += "$($e.name)=secretref:$($e.secretRef)"
    } else {
        $envVarArgs += "$($e.name)=$($e.value)"
    }
}
$envVarString = $envVarArgs -join " "

# ── 3. Update the Container App ─────────────────────────────────────
Write-Host "[3/3] Updating Container App '$ContainerApp'..." -ForegroundColor Yellow

$updateArgs = @(
    "containerapp", "update",
    "--name",            $ContainerApp,
    "--resource-group",  $ResourceGroup,
    "--image",           $fullImage,
    "--set-env-vars",    $envVarArgs
)

az @updateArgs
if ($LASTEXITCODE -ne 0) { throw "Container App update failed." }

Write-Host ""
Write-Host "Deployment complete." -ForegroundColor Green
Write-Host "Endpoints:" -ForegroundColor Cyan

$fqdn = az containerapp show `
    --name $ContainerApp `
    --resource-group $ResourceGroup `
    --query "properties.configuration.ingress.fqdn" `
    --output tsv

$servers = @("taskserver", "workday", "servicenow", "salesforce", "jira")
foreach ($svc in $servers) {
    $label = $svc.PadRight(12)
    Write-Host "  $label (SSE)            : https://$fqdn/$svc/sse"
    Write-Host "  $label (Streamable HTTP) : https://$fqdn/$svc/mcp"
}
Write-Host "  Health                       : https://$fqdn/healthz"
