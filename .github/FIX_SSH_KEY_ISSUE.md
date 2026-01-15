# Fix SSH Key Issue untuk Deployment

Panduan untuk memperbaiki error `Error loading key "(stdin)": error in libcrypto` saat deployment.

## 🔍 Masalah

Error yang muncul:
```
Command failed: ssh-add - Error loading key "(stdin)": error in libcrypto
The process '/usr/bin/git' failed with exit code 128
```

## ✅ Solusi

### 1. Pastikan Format SSH Key Benar

SSH key di GitHub Secrets harus dalam format yang benar tanpa:
- ❌ Extra spaces di awal/akhir
- ❌ Extra line breaks
- ❌ Missing BEGIN/END lines
- ❌ Wrong line endings (harus LF, bukan CRLF)

### 2. Format yang Benar

**RSA Key (Format Lama):**
```
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA...
(multiple lines)
...
-----END RSA PRIVATE KEY-----
```

**OpenSSH Key (Format Baru):**
```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAABlwAAAAdzc2gtcn
(multiple lines)
...
-----END OPENSSH PRIVATE KEY-----
```

### 3. Cara Copy Key yang Benar

#### Windows PowerShell:

```powershell
# Baca key dengan encoding yang benar
$key = Get-Content "C:\Users\info\.ssh\github_actions_vps" -Raw

# Pastikan tidak ada trailing spaces
$key = $key.Trim()

# Tampilkan untuk verifikasi
Write-Host $key

# Copy ke clipboard
$key | Set-Clipboard
```

#### Atau gunakan script helper:

```powershell
cd .github
.\setup-github-secrets.ps1
```

### 4. Update GitHub Secret

1. **Buka GitHub Repository**
   - Settings → Secrets and variables → Actions

2. **Edit atau Buat Secret `VPS_SSH_KEY`**
   - Klik secret yang ada atau "New repository secret"
   - Name: `VPS_SSH_KEY`
   - Value: Paste key dari clipboard
   - **Pastikan:**
     - Tidak ada extra spaces di awal/akhir
     - Include BEGIN dan END lines
     - Tidak ada extra line breaks

3. **Verifikasi Format**
   - Key harus dimulai dengan `-----BEGIN`
   - Key harus diakhiri dengan `-----END`
   - Tidak ada karakter aneh di awal/akhir

### 5. Test Key Format

Setelah update secret, test dengan workflow manual:

1. Pergi ke **Actions** tab
2. Pilih workflow **CD - Deploy to Production VPS**
3. Klik **Run workflow**
4. Pilih branch dan environment
5. Monitor logs untuk melihat apakah error masih muncul

## 🔧 Alternatif: Convert Key Format

Jika key masih tidak bekerja, coba convert ke format OpenSSH:

### Windows (dengan PuTTYgen atau OpenSSH):

```powershell
# Jika key dalam format PPK (PuTTY), convert dulu
# Install PuTTYgen atau gunakan OpenSSH

# Convert dengan OpenSSH (jika tersedia)
ssh-keygen -p -m PEM -f "C:\Users\info\.ssh\github_actions_vps"
```

### Linux/Mac:

```bash
# Convert ke OpenSSH format
ssh-keygen -p -m PEM -f ~/.ssh/github_actions_vps

# Atau convert dari RSA ke OpenSSH
ssh-keygen -p -f ~/.ssh/github_actions_vps -m PEM
```

## 🛠️ Perbaikan yang Sudah Dilakukan

Workflow sudah diperbaiki untuk:
1. ✅ **Menggunakan file-based SSH key** (bukan ssh-agent)
2. ✅ **Menambahkan timeout** untuk SSH connections
3. ✅ **Cleanup key file** setelah deployment
4. ✅ **Better error handling**

## 📝 Checklist

- [ ] SSH key di GitHub Secrets dalam format yang benar
- [ ] Tidak ada extra spaces di awal/akhir key
- [ ] Include BEGIN dan END lines
- [ ] Public key sudah ada di VPS `~/.ssh/authorized_keys`
- [ ] Test SSH connection manual berhasil
- [ ] Workflow sudah di-update (menggunakan file-based SSH)

## 🧪 Test Manual

Test SSH connection dari lokal:

```powershell
# Windows PowerShell
ssh -i "C:\Users\info\.ssh\github_actions_vps" foom@103.31.39.189 "echo 'Connection successful'"
```

Jika ini berhasil, maka key format sudah benar.

## 🆘 Jika Masih Error

1. **Check Key Format:**
   ```powershell
   # Baca key dan check format
   Get-Content "C:\Users\info\.ssh\github_actions_vps" | Select-Object -First 1
   # Harus: -----BEGIN RSA PRIVATE KEY----- atau -----BEGIN OPENSSH PRIVATE KEY-----
   ```

2. **Regenerate Key (jika perlu):**
   ```powershell
   # Generate key baru
   ssh-keygen -t rsa -b 4096 -C "github-actions-deploy" -f "C:\Users\info\.ssh\github_actions_vps_new"
   
   # Copy public key ke VPS
   Get-Content "C:\Users\info\.ssh\github_actions_vps_new.pub" | ssh foom@103.31.39.189 "cat >> ~/.ssh/authorized_keys"
   
   # Update GitHub Secret dengan key baru
   ```

3. **Check VPS authorized_keys:**
   ```bash
   # SSH ke VPS
   ssh foom@103.31.39.189
   
   # Check authorized_keys
   cat ~/.ssh/authorized_keys
   
   # Pastikan format benar (satu line per key)
   ```

## 📚 Referensi

- [GitHub Actions SSH Documentation](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments)
- [OpenSSH Key Format](https://www.openssh.com/)
- [Troubleshooting SSH](https://docs.github.com/en/authentication/troubleshooting-ssh)
