# Script untuk Setup GitHub Repository
# Membantu initialize git dan connect ke GitHub

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup GitHub Repository" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if git is installed
try {
    $gitVersion = git --version
    Write-Host "✅ Git ditemukan: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Git tidak ditemukan. Install Git terlebih dahulu:" -ForegroundColor Red
    Write-Host "   https://git-scm.com/download/win" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Check if already a git repository
if (Test-Path .git) {
    Write-Host "⚠️  Repository Git sudah di-initialize" -ForegroundColor Yellow
    $continue = Read-Host "Lanjutkan setup? (y/n)"
    if ($continue -ne "y" -and $continue -ne "Y") {
        exit 0
    }
} else {
    Write-Host "📦 Initializing Git repository..." -ForegroundColor Yellow
    git init
    Write-Host "✅ Git repository initialized" -ForegroundColor Green
}

Write-Host ""

# Check remote
$remotes = git remote -v
if ($remotes) {
    Write-Host "📡 Remote yang sudah ada:" -ForegroundColor Yellow
    Write-Host $remotes
    Write-Host ""
    $changeRemote = Read-Host "Ubah remote origin? (y/n)"
    if ($changeRemote -eq "y" -or $changeRemote -eq "Y") {
        git remote remove origin 2>$null
    } else {
        Write-Host "✅ Menggunakan remote yang sudah ada" -ForegroundColor Green
        exit 0
    }
}

Write-Host ""
Write-Host "🔗 Setup Remote Repository" -ForegroundColor Cyan
Write-Host ""

# Get GitHub username
$githubUsername = Read-Host "Masukkan GitHub username Anda"
if ([string]::IsNullOrWhiteSpace($githubUsername)) {
    Write-Host "❌ Username tidak boleh kosong" -ForegroundColor Red
    exit 1
}

# Get repository name
$repoName = Read-Host "Masukkan nama repository (default: PZEM-Project)"
if ([string]::IsNullOrWhiteSpace($repoName)) {
    $repoName = "PZEM-Project"
}

# Choose connection method
Write-Host ""
Write-Host "Pilih metode koneksi:" -ForegroundColor Cyan
Write-Host "1. HTTPS (mudah, perlu token)" -ForegroundColor White
Write-Host "2. SSH (lebih aman, perlu setup SSH key)" -ForegroundColor White
$method = Read-Host "Pilihan (1/2)"

if ($method -eq "1") {
    $repoUrl = "https://github.com/$githubUsername/$repoName.git"
} elseif ($method -eq "2") {
    $repoUrl = "git@github.com:$githubUsername/$repoName.git"
} else {
    Write-Host "❌ Pilihan tidak valid" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "📡 Menambahkan remote origin..." -ForegroundColor Yellow
git remote add origin $repoUrl

# Verify remote
Write-Host "✅ Remote ditambahkan: $repoUrl" -ForegroundColor Green
Write-Host ""
git remote -v

Write-Host ""
Write-Host "📝 Menambahkan file ke staging..." -ForegroundColor Yellow
git add .

Write-Host ""
Write-Host "💾 Membuat commit pertama..." -ForegroundColor Yellow
$commitMessage = "Initial commit: PZEM IoT Monitoring Project dengan CI/CD"
git commit -m $commitMessage

Write-Host ""
Write-Host "🌿 Mengatur branch ke 'main'..." -ForegroundColor Yellow
git branch -M main 2>$null

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup Selesai!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 Langkah selanjutnya:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Pastikan repository sudah dibuat di GitHub:" -ForegroundColor White
Write-Host "   https://github.com/new" -ForegroundColor Gray
Write-Host "   Nama: $repoName" -ForegroundColor Gray
Write-Host "   JANGAN centang README, .gitignore, atau license" -ForegroundColor Yellow
Write-Host ""
Write-Host "2. Push ke GitHub:" -ForegroundColor White
Write-Host "   git push -u origin main" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Jika diminta authentication:" -ForegroundColor White
if ($method -eq "1") {
    Write-Host "   - Gunakan Personal Access Token sebagai password" -ForegroundColor Gray
    Write-Host "   - Generate di: https://github.com/settings/tokens" -ForegroundColor Gray
} else {
    Write-Host "   - Pastikan SSH key sudah ditambahkan ke GitHub" -ForegroundColor Gray
    Write-Host "   - Settings → SSH and GPG keys → New SSH key" -ForegroundColor Gray
}
Write-Host ""
Write-Host "4. Setup GitHub Secrets untuk CI/CD:" -ForegroundColor White
Write-Host "   cd .github" -ForegroundColor Gray
Write-Host "   .\setup-github-secrets.ps1" -ForegroundColor Gray
Write-Host ""

$pushNow = Read-Host "Push ke GitHub sekarang? (y/n)"
if ($pushNow -eq "y" -or $pushNow -eq "Y") {
    Write-Host ""
    Write-Host "🚀 Pushing ke GitHub..." -ForegroundColor Yellow
    git push -u origin main
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ Berhasil push ke GitHub!" -ForegroundColor Green
        Write-Host "🌐 Repository: https://github.com/$githubUsername/$repoName" -ForegroundColor Cyan
    } else {
        Write-Host ""
        Write-Host "❌ Push gagal. Periksa:" -ForegroundColor Red
        Write-Host "   - Repository sudah dibuat di GitHub" -ForegroundColor Yellow
        Write-Host "   - Authentication sudah benar" -ForegroundColor Yellow
        Write-Host "   - Internet connection aktif" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
