# Panduan Setup GitHub Repository

Panduan lengkap untuk membuat dan setup repository GitHub untuk project PZEM Monitoring.

## 📋 Prerequisites

1. Akun GitHub (jika belum punya, daftar di [github.com](https://github.com))
2. Git terinstall di komputer (cek dengan `git --version`)
3. SSH key untuk GitHub (optional, tapi disarankan)

## 🚀 Langkah-langkah Setup

### Langkah 1: Buat Repository di GitHub

1. **Login ke GitHub**
   - Buka [github.com](https://github.com)
   - Login dengan akun Anda

2. **Buat Repository Baru**
   - Klik tombol **"+"** di kanan atas → **"New repository"**
   - Atau langsung ke: https://github.com/new

3. **Isi Form Repository**
   - **Repository name**: `PZEM-Project` (atau nama yang Anda inginkan)
   - **Description**: `IoT Energy Monitoring System dengan PZEM sensors, ESP32, dan Dashboard`
   - **Visibility**: 
     - ✅ **Public** (jika ingin open source)
     - ✅ **Private** (jika ingin private)
   - **JANGAN** centang:
     - ❌ Add a README file (kita sudah punya)
     - ❌ Add .gitignore (kita sudah punya)
     - ❌ Choose a license (bisa ditambahkan nanti)

4. **Klik "Create repository"**

### Langkah 2: Initialize Git Repository Lokal

Jalankan perintah berikut di PowerShell (dari folder project):

```powershell
# Pastikan Anda di folder project
cd "C:\Users\info\Documents\Project\not-released\IoT-Project\PZEM-Project"

# Initialize git repository
git init

# Tambahkan semua file ke staging
git add .

# Commit pertama
git commit -m "Initial commit: PZEM IoT Monitoring Project dengan CI/CD"

# Rename branch ke main (jika perlu)
git branch -M main
```

### Langkah 3: Connect ke GitHub Repository

**Copy URL repository dari GitHub** (setelah membuat repository, GitHub akan menampilkan URL)

Contoh URL:
- HTTPS: `https://github.com/USERNAME/PZEM-Project.git`
- SSH: `git@github.com:USERNAME/PZEM-Project.git`

**Tambahkan remote:**

```powershell
# Ganti USERNAME dengan username GitHub Anda
git remote add origin https://github.com/USERNAME/PZEM-Project.git

# Atau jika menggunakan SSH:
# git remote add origin git@github.com:USERNAME/PZEM-Project.git

# Verify remote
git remote -v
```

### Langkah 4: Push ke GitHub

```powershell
# Push ke GitHub
git push -u origin main

# Jika ada error tentang authentication, ikuti langkah berikutnya
```

### Langkah 5: Setup Authentication (jika diperlukan)

**Jika menggunakan HTTPS dan diminta login:**

1. **Gunakan Personal Access Token (Recommended)**
   - Buka: https://github.com/settings/tokens
   - Klik **"Generate new token"** → **"Generate new token (classic)"**
   - Beri nama: `PZEM-Project-Access`
   - Pilih scopes: ✅ `repo` (full control)
   - Klik **"Generate token"**
   - **COPY TOKEN** (hanya muncul sekali!)
   - Gunakan token sebagai password saat push

2. **Atau Setup SSH Key (Lebih Aman)**
   ```powershell
   # Generate SSH key untuk GitHub
   ssh-keygen -t ed25519 -C "your_email@example.com"
   
   # Copy public key
   Get-Content ~/.ssh/id_ed25519.pub
   
   # Tambahkan ke GitHub:
   # Settings → SSH and GPG keys → New SSH key
   # Paste public key
   ```

### Langkah 6: Verify Setup

1. **Refresh halaman repository di GitHub**
   - Semua file seharusnya sudah muncul

2. **Check Actions Tab**
   - Pergi ke tab **"Actions"** di repository
   - Workflows CI/CD seharusnya sudah terdeteksi

3. **Test Push**
   ```powershell
   # Buat perubahan kecil
   echo "# Test" >> test.txt
   git add test.txt
   git commit -m "Test commit"
   git push
   
   # Hapus file test
   git rm test.txt
   git commit -m "Remove test file"
   git push
   ```

## 🔧 Setup GitHub Secrets untuk CI/CD

Setelah repository dibuat, setup GitHub Secrets untuk deployment:

1. **Buka Repository Settings**
   - Repository → **Settings** → **Secrets and variables** → **Actions**

2. **Tambahkan Secrets** (lihat [.github/SETUP_CI_CD.md](.github/SETUP_CI_CD.md))

3. **Atau jalankan script helper:**
   ```powershell
   cd .github
   .\setup-github-secrets.ps1
   ```

## ✅ Checklist

- [ ] Repository dibuat di GitHub
- [ ] Git repository di-initialize lokal
- [ ] Remote origin ditambahkan
- [ ] File di-push ke GitHub
- [ ] GitHub Secrets di-setup (untuk CI/CD)
- [ ] Actions workflows terdeteksi
- [ ] Test commit berhasil

## 🐛 Troubleshooting

### Error: "remote origin already exists"

```powershell
# Hapus remote yang ada
git remote remove origin

# Tambahkan lagi dengan URL yang benar
git remote add origin https://github.com/USERNAME/PZEM-Project.git
```

### Error: "Authentication failed"

**Solusi 1: Gunakan Personal Access Token**
- Generate token di GitHub Settings → Developer settings → Personal access tokens
- Gunakan token sebagai password

**Solusi 2: Setup SSH Key**
- Generate SSH key dan tambahkan ke GitHub
- Ubah remote URL ke SSH:
  ```powershell
  git remote set-url origin git@github.com:USERNAME/PZEM-Project.git
  ```

### Error: "Large files detected"

Jika ada file besar yang tidak perlu di-commit:
```powershell
# Hapus dari git (tapi tetap di local)
git rm --cached large-file.zip

# Tambahkan ke .gitignore
echo "*.zip" >> .gitignore

# Commit perubahan
git add .gitignore
git commit -m "Remove large files and update gitignore"
git push
```

### Error: "Branch protection rules"

Jika branch `main` protected:
- Repository → Settings → Branches
- Edit protection rules atau disable sementara untuk testing

## 📚 Next Steps

Setelah repository setup:

1. ✅ **Setup CI/CD Secrets** - Lihat [.github/SETUP_CI_CD.md](.github/SETUP_CI_CD.md)
2. ✅ **Test Workflows** - Push perubahan dan check Actions tab
3. ✅ **Setup Branch Protection** (optional) - Protect main branch
4. ✅ **Add Collaborators** (optional) - Invite team members
5. ✅ **Setup Issues & Projects** (optional) - Untuk project management

## 🔗 Useful Links

- [GitHub Documentation](https://docs.github.com)
- [Git Handbook](https://guides.github.com/introduction/git-handbook/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

## 💡 Tips

1. **Commit Message yang Baik:**
   - Gunakan format: `type: description`
   - Contoh: `feat: add report generator`, `fix: database connection issue`

2. **Branch Strategy:**
   - `main` - Production ready code
   - `develop` - Development branch
   - `feature/*` - Feature branches
   - `hotfix/*` - Hotfix branches

3. **Regular Commits:**
   - Commit sering-sering dengan message yang jelas
   - Push ke GitHub secara berkala

4. **Backup:**
   - GitHub sudah backup otomatis
   - Tapi tetap backup lokal penting files

---

**Selamat! Repository Anda sudah siap digunakan! 🎉**
