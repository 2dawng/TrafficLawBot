# Start Qdrant with Storage on D:\traffic_law
# This script sets up Qdrant to store all data on your D: drive

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host "🚀 Qdrant Setup - Custom Storage Location" -ForegroundColor Green
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 69) -ForegroundColor Cyan

# Configuration
$storagePath = "D:\traffic_law\qdrant_data"
$containerName = "qdrant"

Write-Host "`n📂 Target storage location: $storagePath" -ForegroundColor Yellow

# Check if directory exists
if (Test-Path $storagePath) {
    Write-Host "✅ Directory already exists" -ForegroundColor Green
    
    # Check size
    $size = (Get-ChildItem $storagePath -Recurse -File -ErrorAction SilentlyContinue | 
             Measure-Object -Property Length -Sum).Sum / 1GB
    Write-Host "   Current size: $([math]::Round($size, 2)) GB" -ForegroundColor Cyan
} else {
    Write-Host "⚠️  Directory does not exist. Creating..." -ForegroundColor Yellow
    New-Item -Path $storagePath -ItemType Directory -Force | Out-Null
    Write-Host "✅ Created directory: $storagePath" -ForegroundColor Green
}

# Check if Docker is installed
Write-Host "`n🐳 Checking Docker..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version
    Write-Host "✅ Docker found: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker not found!" -ForegroundColor Red
    Write-Host "`n💡 Please install Docker Desktop:" -ForegroundColor Yellow
    Write-Host "   https://www.docker.com/products/docker-desktop/" -ForegroundColor Cyan
    exit 1
}

# Check if container already exists
Write-Host "`n🔍 Checking for existing Qdrant container..." -ForegroundColor Yellow
$existingContainer = docker ps -a --filter "name=$containerName" --format "{{.Names}}" 2>$null

if ($existingContainer -eq $containerName) {
    Write-Host "⚠️  Container '$containerName' already exists!" -ForegroundColor Yellow
    
    $response = Read-Host "`n❓ Remove and recreate? (yes/no)"
    
    if ($response -eq "yes" -or $response -eq "y") {
        Write-Host "`n🛑 Stopping container..." -ForegroundColor Yellow
        docker stop $containerName 2>$null
        
        Write-Host "🗑️  Removing container..." -ForegroundColor Yellow
        docker rm $containerName 2>$null
        
        Write-Host "✅ Old container removed" -ForegroundColor Green
    } else {
        Write-Host "❌ Setup cancelled" -ForegroundColor Red
        exit 0
    }
}

# Start Qdrant container
Write-Host "`n🚀 Starting Qdrant container..." -ForegroundColor Yellow
Write-Host "   Storage: $storagePath" -ForegroundColor Cyan

try {
    docker run -d `
        -p 6333:6333 `
        -p 6334:6334 `
        -v "${storagePath}:/qdrant/storage" `
        --name $containerName `
        qdrant/qdrant
    
    Write-Host "✅ Qdrant started successfully!" -ForegroundColor Green
    
    # Wait for Qdrant to be ready
    Write-Host "`n⏳ Waiting for Qdrant to be ready..." -ForegroundColor Yellow
    Start-Sleep -Seconds 3
    
    # Test connection
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:6333" -UseBasicParsing -TimeoutSec 5
        Write-Host "✅ Qdrant is responding!" -ForegroundColor Green
    } catch {
        Write-Host "⚠️  Qdrant might still be starting up..." -ForegroundColor Yellow
    }
    
    # Show info
    Write-Host "`n" -NoNewline
    Write-Host "=" -NoNewline -ForegroundColor Cyan
    Write-Host ("=" * 69) -ForegroundColor Cyan
    Write-Host "✅ Setup Complete!" -ForegroundColor Green
    Write-Host "=" -NoNewline -ForegroundColor Cyan
    Write-Host ("=" * 69) -ForegroundColor Cyan
    
    Write-Host "`n📍 Storage location: $storagePath" -ForegroundColor Cyan
    Write-Host "🌐 Web UI: http://localhost:6333/dashboard" -ForegroundColor Cyan
    Write-Host "🔌 API URL: http://localhost:6333" -ForegroundColor Cyan
    
    Write-Host "`n💡 Next steps:" -ForegroundColor Yellow
    Write-Host "   1. Verify setup: python verify_storage_location.py" -ForegroundColor White
    Write-Host "   2. Embed documents: python embed_local.py" -ForegroundColor White
    Write-Host "   3. Check storage: python check_qdrant_storage.py" -ForegroundColor White
    
    Write-Host "`n🔧 Useful commands:" -ForegroundColor Yellow
    Write-Host "   docker ps                 # Check if running" -ForegroundColor White
    Write-Host "   docker stop qdrant        # Stop Qdrant" -ForegroundColor White
    Write-Host "   docker start qdrant       # Start Qdrant" -ForegroundColor White
    Write-Host "   docker logs qdrant        # View logs" -ForegroundColor White
    
} catch {
    Write-Host "❌ Failed to start Qdrant!" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
}

Write-Host "`n"
