# AWS Secret Seeding Script for PowerShell
# Usage: .\scripts\seed-secret-manager.ps1

$Region = "eu-west-2"
$Environment = "staging"
$ProjectName = "cogent"
$Prefix = "$ProjectName-$Environment"

Write-Host "Starting AWS Secret Seeding for $Prefix..." -ForegroundColor Blue

# 1. Load .env file into a dictionary
$envVars = @{}
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        # Match lines that aren't comments and have an = sign
        if ($_ -match "^(?<name>[^#\s][^=]*)=(?<value>.*)$") {
            $name = $Matches['name'].Trim()
            $value = $Matches['value'].Trim().Trim('"').Trim("'")
            if ($value) {
                $envVars[$name] = $value
            }
        }
    }
    Write-Host "Loaded $($envVars.Count) variables from .env" -ForegroundColor Gray
} else {
    Write-Error "Could not find .env file in the current directory."
    return
}

# 2. List of secrets expected by the infrastructure (from variables.tf)
$secretNames = @(
    "SECRET_KEY",
    "AUTH0_DOMAIN",
    "AUTH0_AUDIENCE",
    "AUTH0_SECRET",
    "AUTH0_ISSUER_BASE_URL",
    "AUTH0_CLIENT_ID",
    "AUTH0_CLIENT_SECRET",
    "AUTH0_M2M_CLIENT_ID",
    "AUTH0_M2M_CLIENT_SECRET",
    "AUTH0_WEBHOOK_SECRET",
    "OPENAI_API_KEY",
    "NEWSAPI_API_KEY",
    "NGX_MARKET_DATA_API_KEY",
    "NGX_MARKET_DATA_BASE_URL",
    "X_BEARER_TOKEN",
    "SERPAPI_API_KEY",
    "RESEND_API_KEY",
    "RESEND_FROM_EMAIL",
    "PAYSTACK_PUBLIC_KEY",
    "PAYSTACK_SECRET_KEY",
    "SENTRY_DSN",
    "LOGTAIL_TOKEN",
    "POSTHOG_API_KEY",
    "POSTHOG_HOST"
)

# 3. Process each secret
foreach ($name in $secretNames) {
    $value = $envVars[$name]
    $secretId = "$Prefix/$name"

    if (-not $value) {
        Write-Host "[aws-secrets] Skipping $secretId; $name is not set in .env" -ForegroundColor Gray
        continue
    }

    Write-Host "[aws-secrets] Syncing $secretId..." -NoNewline

    # Check if the secret exists in AWS
    aws secretsmanager describe-secret --secret-id $secretId --region $Region 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        # Create the secret if it doesn't exist
        aws secretsmanager create-secret --name $secretId --secret-string "$value" --region $Region | Out-Null
        Write-Host " [CREATED]" -ForegroundColor Green
    } else {
        # Update the secret value if it already exists
        aws secretsmanager put-secret-value --secret-id $secretId --secret-string "$value" --region $Region | Out-Null
        Write-Host " [UPDATED]" -ForegroundColor Yellow
    }
}

Write-Host "`nSeeding complete! Your AWS Secrets Manager is now synchronized with your .env file." -ForegroundColor Green
