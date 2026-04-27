param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectId,

    [string]$Environment = "staging"
)

$prefix = "cogent-$Environment"

$secretMap = @{
    "redis-url"                   = "REDIS_URL"
    "secret-key"                  = "SECRET_KEY"
    "auth0-domain"                = "AUTH0_DOMAIN"
    "auth0-audience"              = "AUTH0_AUDIENCE"
    "auth0-m2m-client-id"         = "AUTH0_M2M_CLIENT_ID"
    "auth0-m2m-client-secret"     = "AUTH0_M2M_CLIENT_SECRET"
    "auth0-webhook-secret"        = "AUTH0_WEBHOOK_SECRET"
    "auth0-frontend-secret"       = "AUTH0_SECRET"
    "auth0-client-id"             = "AUTH0_CLIENT_ID"
    "auth0-client-secret"         = "AUTH0_CLIENT_SECRET"
    "openai-api-key"              = "OPENAI_API_KEY"
    "newsapi-api-key"             = "NEWSAPI_API_KEY"
    "ngx-market-data-api-key"     = "NGX_MARKET_DATA_API_KEY"
    "ngx-market-data-base-url"    = "NGX_MARKET_DATA_BASE_URL"
    "x-bearer-token"              = "X_BEARER_TOKEN"
    "serpapi-api-key"             = "SERPAPI_API_KEY"
    "resend-api-key"              = "RESEND_API_KEY"
    "paystack-public-key"         = "PAYSTACK_PUBLIC_KEY"
    "paystack-secret-key"         = "PAYSTACK_SECRET_KEY"
    "sentry-dsn"                  = "SENTRY_DSN"
    "logtail-token"               = "LOGTAIL_TOKEN"
    "posthog-api-key"             = "POSTHOG_API_KEY"
    "neo4j-uri"                   = "NEO4J_URI"
    "neo4j-user"                  = "NEO4J_USER"
    "neo4j-password"              = "NEO4J_PASSWORD"
}

foreach ($entry in $secretMap.GetEnumerator()) {
    $secretName = "$prefix-$($entry.Key)"
    $envName = $entry.Value
    $value = [Environment]::GetEnvironmentVariable($envName)

    if ([string]::IsNullOrWhiteSpace($value)) {
        Write-Host "[secret-manager] Skipping $secretName; $envName is not set"
        continue
    }

    gcloud secrets describe $secretName --project $ProjectId *> $null
    if ($LASTEXITCODE -ne 0) {
        gcloud secrets create $secretName --project $ProjectId --replication-policy automatic
    }

    $tempFile = New-TemporaryFile
    try {
        Set-Content -LiteralPath $tempFile -Value $value -NoNewline
        gcloud secrets versions add $secretName --project $ProjectId --data-file $tempFile
        Write-Host "[secret-manager] Updated $secretName"
    }
    finally {
        Remove-Item -LiteralPath $tempFile -Force
    }
}

