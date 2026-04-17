param(
    [string]$Version = "dev",
    [string]$Platforms = "linux/amd64"
)

$ErrorActionPreference = "Stop"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "AutoBangumi Docker Build" -ForegroundColor Cyan
Write-Host "Version: $Version" -ForegroundColor Cyan
Write-Host "Platforms: $Platforms" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# Build frontend
Write-Host "[1/4] Building frontend..." -ForegroundColor Yellow
Set-Location webui
pnpm install
pnpm build
Set-Location ..

# Copy dist to backend
Write-Host "[2/4] Copying frontend assets..." -ForegroundColor Yellow
if (Test-Path "backend/src/dist") {
    Remove-Item -Recurse -Force "backend/src/dist"
}
Copy-Item -Recurse "webui/dist" "backend/src/dist"

# Create version info
Write-Host "[3/4] Creating version info..." -ForegroundColor Yellow
Set-Content -Path "backend/src/module/__version__.py" -Value "VERSION='$Version'"

# Build Docker image
Write-Host "[4/4] Building Docker image..." -ForegroundColor Yellow
if ($Platforms -like "*,*") {
    # Multi-platform build (requires buildx)
    docker buildx build `
        --platform $Platforms `
        -t "auto_bangumi:$Version" `
        -t "auto_bangumi:latest" `
        --load `
        .
} else {
    # Single platform build
    docker build `
        -t "auto_bangumi:$Version" `
        -t "auto_bangumi:latest" `
        .
}

Write-Host "=========================================" -ForegroundColor Green
Write-Host "Build complete!" -ForegroundColor Green
Write-Host "Image: auto_bangumi:$Version" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Run with:" -ForegroundColor Cyan
Write-Host "  docker run -p 7892:7892 -v ./config:/app/config -v ./data:/app/data auto_bangumi:$Version"
