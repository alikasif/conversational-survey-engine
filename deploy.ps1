<#
.SYNOPSIS
    Deploy the Conversational Survey Engine to Kubernetes.
.DESCRIPTION
    Builds Docker images, pushes to registry, and applies K8s manifests.
.PARAMETER Registry
    Container registry URL (e.g., ghcr.io/myorg).
.PARAMETER Tag
    Image tag (default: latest).
.PARAMETER DryRun
    Print commands without executing.
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$Registry,

    [string]$Tag = "latest",

    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$services = @(
    @{ Name = "cse-backend";     Context = "./backend" },
    @{ Name = "cse-llm-service"; Context = "./llm-service" },
    @{ Name = "cse-frontend";    Context = "./frontend" }
)

function Invoke-Step {
    param([string]$Description, [string]$Command)
    Write-Host "`n==> $Description" -ForegroundColor Cyan
    if ($DryRun) {
        Write-Host "  [DRY RUN] $Command" -ForegroundColor Yellow
    } else {
        Write-Host "  $Command" -ForegroundColor Gray
        Invoke-Expression $Command
        if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {
            Write-Error "FAILED: $Description (exit code $LASTEXITCODE)"
            exit $LASTEXITCODE
        }
    }
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host " CSE Kubernetes Deployment" -ForegroundColor Green
Write-Host " Registry: $Registry" -ForegroundColor Green
Write-Host " Tag: $Tag" -ForegroundColor Green
Write-Host " DryRun: $DryRun" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

# Step 1: Build images
foreach ($svc in $services) {
    $image = "$Registry/$($svc.Name):$Tag"
    Invoke-Step "Build $($svc.Name)" "docker build -t $image $($svc.Context)"
}

# Step 2: Push images
foreach ($svc in $services) {
    $image = "$Registry/$($svc.Name):$Tag"
    Invoke-Step "Push $($svc.Name)" "docker push $image"
}

# Step 3: Apply K8s manifests
Invoke-Step "Create namespace" "kubectl apply -f k8s/namespace.yaml"

Write-Host "`n  [WARNING] Ensure k8s/secrets.yaml has real base64-encoded values!" -ForegroundColor Red
Invoke-Step "Apply secrets" "kubectl apply -f k8s/secrets.yaml"
Invoke-Step "Apply configmap" "kubectl apply -f k8s/configmap.yaml"

# Step 4: Run migration
Invoke-Step "Delete old migration job (if exists)" "kubectl delete job alembic-migrate -n cse --ignore-not-found"
Invoke-Step "Run Alembic migration" "kubectl apply -f k8s/migration-job.yaml"
Invoke-Step "Wait for migration" "kubectl wait --for=condition=complete job/alembic-migrate -n cse --timeout=120s"

# Step 5: Deploy services
Invoke-Step "Deploy backend" "kubectl apply -f k8s/backend-deployment.yaml -f k8s/backend-service.yaml"
Invoke-Step "Deploy LLM service" "kubectl apply -f k8s/llm-service-deployment.yaml -f k8s/llm-service-service.yaml"
Invoke-Step "Deploy frontend" "kubectl apply -f k8s/frontend-deployment.yaml -f k8s/frontend-service.yaml"

# Step 6: Verify rollouts
Invoke-Step "Verify backend rollout" "kubectl rollout status deployment/backend -n cse --timeout=120s"
Invoke-Step "Verify LLM service rollout" "kubectl rollout status deployment/llm-service -n cse --timeout=120s"
Invoke-Step "Verify frontend rollout" "kubectl rollout status deployment/frontend -n cse --timeout=120s"

# Step 7: Print endpoints
Write-Host "`n========================================" -ForegroundColor Green
Write-Host " Deployment Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

if (-not $DryRun) {
    Write-Host "`nService endpoints:" -ForegroundColor Cyan
    kubectl get services -n cse -o wide
}
