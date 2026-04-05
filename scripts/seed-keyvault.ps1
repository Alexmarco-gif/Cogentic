[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$VaultName
)

$ErrorActionPreference = 'Stop'

$secretMap = [ordered]@{
    'redis-url'                    = 'REDIS_URL'
    'secret-key'                   = 'SECRET_KEY'
    'auth0-domain'                 = 'AUTH0_DOMAIN'
    'auth0-audience'               = 'AUTH0_AUDIENCE'
    'auth0-m2m-client-id'          = 'AUTH0_M2M_CLIENT_ID'
    'auth0-m2m-client-secret'      = 'AUTH0_M2M_CLIENT_SECRET'
    'auth0-webhook-secret'         = 'AUTH0_WEBHOOK_SECRET'
    'openai-api-key'               = 'OPENAI_API_KEY'
    'sentry-dsn'                   = 'SENTRY_DSN'
    'logtail-token'                = 'LOGTAIL_TOKEN'
    'posthog-api-key'              = 'POSTHOG_API_KEY'
    'posthog-host'                 = 'POSTHOG_HOST'
    'resend-api-key'               = 'RESEND_API_KEY'
    'resend-from-email'            = 'RESEND_FROM_EMAIL'
    'serpapi-api-key'              = 'SERPAPI_API_KEY'
    'newsapi-api-key'              = 'NEWSAPI_API_KEY'
    'ngx-market-data-api-key'      = 'NGX_MARKET_DATA_API_KEY'
    'ngx-market-data-base-url'     = 'NGX_MARKET_DATA_BASE_URL'
    'x-bearer-token'               = 'X_BEARER_TOKEN'
    'azure-blob-connection-string' = 'AZURE_BLOB_CONNECTION_STRING'
    'azure-blob-model-container'   = 'AZURE_BLOB_MODEL_CONTAINER'
    'auth0-frontend-secret'        = 'AUTH0_SECRET'
    'auth0-issuer-base-url'        = 'AUTH0_ISSUER_BASE_URL'
    'auth0-client-id'              = 'AUTH0_CLIENT_ID'
    'auth0-client-secret'          = 'AUTH0_CLIENT_SECRET'
}

$missing = @()
foreach ($entry in $secretMap.GetEnumerator()) {
    $value = [Environment]::GetEnvironmentVariable($entry.Value)
    if ([string]::IsNullOrWhiteSpace($value)) {
        $missing += "$($entry.Value) -> $($entry.Key)"
    }
}

if ($missing.Count -gt 0) {
    Write-Error ("Missing required environment variables:`n - " + ($missing -join "`n - "))
}

foreach ($entry in $secretMap.GetEnumerator()) {
    $secretName = $entry.Key
    $envVarName = $entry.Value
    $value = [Environment]::GetEnvironmentVariable($envVarName)

    Write-Host "[keyvault] Setting secret: $secretName" -ForegroundColor Green
    az keyvault secret set `
        --vault-name $VaultName `
        --name $secretName `
        --value $value `
        --output none | Out-Null
}

Write-Host "[keyvault] Done. Secrets seeded into Key Vault: $VaultName" -ForegroundColor Green
Write-Host "[keyvault] Note: 'database-url' is created by infrastructure/main.bicep from the Azure PostgreSQL server outputs." -ForegroundColor Green
Write-Host "[keyvault] To verify:" -ForegroundColor Green
Write-Host "[keyvault]   az keyvault secret list --vault-name $VaultName --output table" -ForegroundColor Green
