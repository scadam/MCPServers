param(
    [string]$EnvFile = "..\env\workday.local.env"
)

if (Test-Path $EnvFile) {
    Write-Host "Loading environment from $EnvFile"
    Get-Content $EnvFile | ForEach-Object {
        if ([string]::IsNullOrWhiteSpace($_)) { return }
        if ($_ -match "^\s*#") { return }
        $pair = $_.Split('=', 2)
        if ($pair.Length -eq 2) {
            $key = $pair[0]
            $value = $pair[1]
            [System.Environment]::SetEnvironmentVariable($key, $value)
        }
    }
} else {
    Write-Warning "Environment file not found at $EnvFile"
}

python -m mcp_servers.cli workday --transport http --host 0.0.0.0 --port 8080
