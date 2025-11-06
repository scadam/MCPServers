param(
    [Parameter(Mandatory=$true)][string]$ResourceGroup,
    [Parameter(Mandatory=$true)][string]$FunctionApp,
    [string]$PublishFolder = "publish"
)

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$workspaceRoot = Split-Path $scriptRoot -Parent
$functionSource = Join-Path $workspaceRoot "azure_function"
$functionPublishRoot = Join-Path $functionSource $PublishFolder
$sitePackagesPath = Join-Path $functionPublishRoot ".python_packages\lib\site-packages"
$sourcePackageRoot = Join-Path $workspaceRoot "src\mcp_servers"

if (-not (Test-Path $functionSource)) {
    throw "The azure_function directory was not found at $functionSource."
}

if (Test-Path $functionPublishRoot) {
    Remove-Item -Path $functionPublishRoot -Recurse -Force
}
New-Item -Path $functionPublishRoot -ItemType Directory | Out-Null
New-Item -Path $sitePackagesPath -ItemType Directory -Force | Out-Null

# Copy Azure Function artifacts (host.json, requirements.txt, etc.).
Get-ChildItem -Path $functionSource -File | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination $functionPublishRoot
}

# Include the Workday MCP server source package.
Copy-Item -Path $sourcePackageRoot -Destination (Join-Path $functionPublishRoot "mcp_servers") -Recurse

Write-Host "Installing Python dependencies defined in requirements.txt..."
python -m pip install -r (Join-Path $functionSource "requirements.txt") --target $sitePackagesPath

$zipPath = Join-Path $functionSource "functionapp.zip"
if (Test-Path $zipPath) {
    Remove-Item -Path $zipPath -Force
}

Write-Host "Creating deployment archive at $zipPath..."
Compress-Archive -Path (Join-Path $functionPublishRoot '*') -DestinationPath $zipPath

Write-Host "Deploying archive to Azure Function App $FunctionApp in resource group $ResourceGroup..."
az functionapp deployment source config-zip `
    --resource-group $ResourceGroup `
    --name $FunctionApp `
    --src $zipPath

Write-Host "Deployment complete."
