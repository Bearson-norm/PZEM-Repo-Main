# Script untuk Setup GitHub Secrets untuk CI/CD
# Menampilkan SSH key yang perlu di-copy ke GitHub Secrets

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup GitHub Secrets untuk CI/CD" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$sshKeyPath = "C:\Users\info\.ssh\github_actions_vps"

# Check if key file exists
if (-not (Test-Path $sshKeyPath)) {
    Write-Host "❌ SSH key tidak ditemukan di: $sshKeyPath" -ForegroundColor Red
    Write-Host ""
    Write-Host "Pastikan file SSH key ada di lokasi tersebut." -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ SSH key ditemukan: $sshKeyPath" -ForegroundColor Green
Write-Host ""

# Read private key
Write-Host "📋 Private Key Content (untuk GitHub Secret: VPS_SSH_KEY):" -ForegroundColor Yellow
Write-Host "------------------------------------------------------------" -ForegroundColor Yellow
$privateKey = Get-Content $sshKeyPath -Raw
Write-Host $privateKey
Write-Host "------------------------------------------------------------" -ForegroundColor Yellow
Write-Host ""

# Copy to clipboard
$privateKey | Set-Clipboard
Write-Host "✅ Private key sudah di-copy ke clipboard!" -ForegroundColor Green
Write-Host ""

Write-Host "📝 Langkah selanjutnya:" -ForegroundColor Cyan
Write-Host "1. Buka GitHub Repository → Settings → Secrets and variables → Actions" -ForegroundColor White
Write-Host "2. Klik 'New repository secret'" -ForegroundColor White
Write-Host "3. Name: VPS_SSH_KEY" -ForegroundColor White
Write-Host "4. Value: Paste dari clipboard (Ctrl+V)" -ForegroundColor White
Write-Host "5. Klik 'Add secret'" -ForegroundColor White
Write-Host ""

Write-Host "6. (Optional) Tambahkan secret VPS_HOST:" -ForegroundColor Cyan
Write-Host "   Name: VPS_HOST" -ForegroundColor White
Write-Host "   Value: 103.31.39.189" -ForegroundColor White
Write-Host ""

Write-Host "🔍 Test SSH Connection:" -ForegroundColor Cyan
Write-Host "ssh -i `"$sshKeyPath`" foom@103.31.39.189" -ForegroundColor Gray
Write-Host ""

$testConnection = Read-Host "Test koneksi sekarang? (y/n)"
if ($testConnection -eq "y" -or $testConnection -eq "Y") {
    Write-Host ""
    Write-Host "Testing SSH connection..." -ForegroundColor Yellow
    ssh -i $sshKeyPath foom@103.31.39.189 "echo '✅ SSH connection successful!'"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ SSH connection berhasil!" -ForegroundColor Green
        Write-Host "✅ Setup selesai! Workflows siap digunakan." -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "❌ SSH connection gagal. Periksa:" -ForegroundColor Red
        Write-Host "   - Key sudah ada di VPS authorized_keys" -ForegroundColor Yellow
        Write-Host "   - VPS IP address benar (103.31.39.189)" -ForegroundColor Yellow
        Write-Host "   - User 'foom' ada di VPS" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup selesai!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
