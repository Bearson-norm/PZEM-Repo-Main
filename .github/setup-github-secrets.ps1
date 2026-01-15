# Script untuk Setup GitHub Secrets untuk CI/CD
# Menampilkan SSH key yang perlu di-copy ke GitHub Secrets

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup GitHub Secrets untuk CI/CD" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$sshKeyPath = "C:\Users\info\.ssh\github_actions_vps"

# Check if key file exists
if (-not (Test-Path $sshKeyPath)) {
    Write-Host "ERROR: SSH key tidak ditemukan di: $sshKeyPath" -ForegroundColor Red
    Write-Host ""
    Write-Host "Pastikan file SSH key ada di lokasi tersebut." -ForegroundColor Yellow
    exit 1
}

Write-Host "OK: SSH key ditemukan: $sshKeyPath" -ForegroundColor Green
Write-Host ""

# Read private key
Write-Host "Private Key Content (untuk GitHub Secret: VPS_SSH_KEY):" -ForegroundColor Yellow
Write-Host "------------------------------------------------------------" -ForegroundColor Yellow

# Read and clean key
$privateKey = Get-Content $sshKeyPath -Raw
$privateKey = $privateKey.Trim()  # Remove leading/trailing whitespace

# Verify format
$keyValid = $true
if ($privateKey -notmatch '^-----BEGIN.*PRIVATE KEY-----') {
    Write-Host "WARNING: Key tidak dimulai dengan BEGIN line!" -ForegroundColor Red
    Write-Host "   Pastikan key dalam format yang benar." -ForegroundColor Yellow
    $keyValid = $false
}

if ($privateKey -notmatch '-----END.*PRIVATE KEY-----$') {
    Write-Host "WARNING: Key tidak diakhiri dengan END line!" -ForegroundColor Red
    Write-Host "   Pastikan key dalam format yang benar." -ForegroundColor Yellow
    $keyValid = $false
}

if ($keyValid) {
    Write-Host "OK: Key format valid" -ForegroundColor Green
}

Write-Host ""
Write-Host $privateKey
Write-Host ""
Write-Host "------------------------------------------------------------" -ForegroundColor Yellow
Write-Host ""

# Copy to clipboard (cleaned key)
$privateKey | Set-Clipboard
Write-Host "OK: Private key sudah di-copy ke clipboard (cleaned)!" -ForegroundColor Green
Write-Host "   Key sudah di-trim (tidak ada extra spaces)" -ForegroundColor Gray
Write-Host ""

Write-Host "Langkah selanjutnya:" -ForegroundColor Cyan
Write-Host "1. Buka GitHub Repository -> Settings -> Secrets and variables -> Actions" -ForegroundColor White
Write-Host "2. Klik 'New repository secret'" -ForegroundColor White
Write-Host "3. Name: VPS_SSH_KEY" -ForegroundColor White
Write-Host "4. Value: Paste dari clipboard (Ctrl+V)" -ForegroundColor White
Write-Host "5. Klik 'Add secret'" -ForegroundColor White
Write-Host ""

Write-Host "6. (Optional) Tambahkan secret VPS_HOST:" -ForegroundColor Cyan
Write-Host "   Name: VPS_HOST" -ForegroundColor White
Write-Host "   Value: 103.31.39.189" -ForegroundColor White
Write-Host ""

Write-Host "Test SSH Connection:" -ForegroundColor Cyan
Write-Host "ssh -i `"$sshKeyPath`" foom@103.31.39.189" -ForegroundColor Gray
Write-Host ""

$testConnection = Read-Host "Test koneksi sekarang? (y/n)"
if ($testConnection -eq "y" -or $testConnection -eq "Y") {
    Write-Host ""
    Write-Host "Testing SSH connection..." -ForegroundColor Yellow
    ssh -i $sshKeyPath foom@103.31.39.189 "echo 'SSH connection successful!'"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "OK: SSH connection berhasil!" -ForegroundColor Green
        Write-Host "OK: Setup selesai! Workflows siap digunakan." -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "ERROR: SSH connection gagal. Periksa:" -ForegroundColor Red
        Write-Host "   - Key sudah ada di VPS authorized_keys" -ForegroundColor Yellow
        Write-Host "   - VPS IP address benar (103.31.39.189)" -ForegroundColor Yellow
        Write-Host "   - User 'foom' ada di VPS" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup selesai!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
