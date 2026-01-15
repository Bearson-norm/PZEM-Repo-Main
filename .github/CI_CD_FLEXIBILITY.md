# Fleksibilitas dan Konfigurasi CI/CD

Dokumentasi lengkap tentang seberapa fleksibel CI/CD dengan GitHub Actions dan berbagai opsi konfigurasi yang tersedia.

## 🎯 Overview

CI/CD dengan GitHub Actions **sangat fleksibel** dan bisa dikonfigurasi sesuai kebutuhan project Anda. Hampir semua aspek workflow bisa diatur, dari trigger hingga deployment strategy.

## 📋 Aspek yang Bisa Dikonfigurasi

### 1. **Trigger Events** (Kapan Workflow Berjalan)

#### Trigger yang Tersedia:

```yaml
on:
  # Push ke branch tertentu
  push:
    branches: [ main, master, develop ]
    tags: [ 'v*' ]  # Tag releases
  
  # Pull Request
  pull_request:
    branches: [ main ]
    types: [ opened, synchronize, reopened ]
  
  # Manual trigger dengan input
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to deploy'
        required: true
        default: 'production'
        type: choice
        options:
          - production
          - staging
          - development
  
  # Schedule (cron)
  schedule:
    - cron: '0 0 * * *'  # Setiap hari jam 00:00
  
  # Release events
  release:
    types: [ published, created ]
  
  # Issue events
  issues:
    types: [ opened, labeled ]
  
  # Custom events
  repository_dispatch:
    types: [ custom-event ]
```

#### Path-based Triggering (Hanya trigger jika file tertentu berubah):

```yaml
on:
  push:
    branches: [ main ]
    paths:
      - 'pzem-monitoring/V9-Docker/**'  # Hanya trigger jika ada perubahan di folder ini
      - '.github/workflows/**'           # Atau jika workflow berubah
      - '!**/*.md'                       # Exclude markdown files
```

#### Contoh: Multi-Environment Deployment

```yaml
on:
  push:
    branches:
      - main      # Production
      - staging   # Staging
      - develop   # Development
  workflow_dispatch:
    inputs:
      environment:
        description: 'Deployment environment'
        required: true
        type: choice
        options:
          - production
          - staging
          - development
```

### 2. **Jobs dan Dependencies**

#### Job Dependencies (Sequential/Parallel):

```yaml
jobs:
  test:
    name: Run Tests
    runs-on: ubuntu-latest
    steps:
      - name: Test
        run: echo "Running tests"
  
  build:
    name: Build
    runs-on: ubuntu-latest
    needs: test  # Hanya berjalan setelah test selesai
    steps:
      - name: Build
        run: echo "Building"
  
  deploy:
    name: Deploy
    runs-on: ubuntu-latest
    needs: [test, build]  # Berjalan setelah test DAN build selesai
    if: github.ref == 'refs/heads/main'  # Conditional execution
    steps:
      - name: Deploy
        run: echo "Deploying"
```

#### Parallel Jobs:

```yaml
jobs:
  test-python:
    name: Test Python
    runs-on: ubuntu-latest
    steps:
      - run: echo "Python tests"
  
  test-javascript:
    name: Test JavaScript
    runs-on: ubuntu-latest
    steps:
      - run: echo "JS tests"
  
  # Kedua job berjalan parallel (tidak ada needs)
```

### 3. **Runner Selection**

#### Runner Types:

```yaml
jobs:
  ubuntu:
    runs-on: ubuntu-latest  # Ubuntu 22.04
  
  windows:
    runs-on: windows-latest  # Windows Server 2022
  
  macos:
    runs-on: macos-latest    # macOS 13
  
  # Matrix strategy (test di multiple OS/versions)
  matrix:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ['3.9', '3.10', '3.11']
  
  # Self-hosted runners
  custom:
    runs-on: self-hosted
    labels: [linux, docker]
```

### 4. **Environment Variables dan Secrets**

#### Global Environment Variables:

```yaml
env:
  NODE_VERSION: '18'
  PYTHON_VERSION: '3.11'
  DEPLOY_ENV: ${{ github.ref == 'refs/heads/main' && 'production' || 'staging' }}

jobs:
  build:
    runs-on: ubuntu-latest
    env:
      BUILD_TYPE: 'release'  # Job-specific env
    steps:
      - name: Build
        env:
          API_KEY: ${{ secrets.API_KEY }}  # Step-specific env
        run: echo "Building with $BUILD_TYPE"
```

#### Conditional Environment Variables:

```yaml
env:
  DEPLOY_HOST: ${{ github.ref == 'refs/heads/main' && secrets.PROD_HOST || secrets.STAGING_HOST }}
  DEPLOY_USER: ${{ github.ref == 'refs/heads/main' && 'prod-user' || 'staging-user' }}
```

### 5. **Conditional Execution**

#### Job-level Conditions:

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'  # Hanya deploy dari main
    steps:
      - run: echo "Deploying"
  
  notify:
    runs-on: ubuntu-latest
    if: failure()  # Hanya jika job sebelumnya gagal
    steps:
      - run: echo "Sending notification"
```

#### Step-level Conditions:

```yaml
steps:
  - name: Build
    if: github.event_name == 'push'
    run: echo "Building"
  
  - name: Deploy
    if: success() && github.ref == 'refs/heads/main'
    run: echo "Deploying"
  
  - name: Cleanup
    if: always()  # Selalu berjalan, bahkan jika gagal
    run: echo "Cleaning up"
```

### 6. **Matrix Strategy** (Test Multiple Configurations)

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11']
        database: ['postgres:14', 'postgres:15', 'postgres:16']
        include:
          - python-version: '3.11'
            database: 'postgres:15'
            test-extra: true
        exclude:
          - python-version: '3.9'
            database: 'postgres:16'
    steps:
      - name: Test Python ${{ matrix.python-version }} with ${{ matrix.database }}
        run: echo "Testing"
```

### 7. **Services** (Database, Cache, dll)

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
      
      mysql:
        image: mysql:8
        env:
          MYSQL_ROOT_PASSWORD: root
        ports:
          - 3306:3306
```

### 8. **Caching** (Speed Up Builds)

```yaml
steps:
  - name: Cache Python dependencies
    uses: actions/cache@v3
    with:
      path: ~/.cache/pip
      key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
      restore-keys: |
        ${{ runner.os }}-pip-
  
  - name: Cache Docker layers
    uses: actions/cache@v3
    with:
      path: /tmp/.buildx-cache
      key: ${{ runner.os }}-buildx-${{ github.sha }}
      restore-keys: |
        ${{ runner.os }}-buildx-
```

### 9. **Artifacts** (Save Build Outputs)

```yaml
steps:
  - name: Build
    run: |
      docker build -t myapp:latest .
      docker save myapp:latest > myapp.tar
  
  - name: Upload artifact
    uses: actions/upload-artifact@v3
    with:
      name: docker-image
      path: myapp.tar
      retention-days: 7
  
  - name: Download artifact (di job lain)
    uses: actions/download-artifact@v3
    with:
      name: docker-image
```

### 10. **Deployment Strategies**

#### Blue-Green Deployment:

```yaml
jobs:
  deploy-blue:
    name: Deploy to Blue
    steps:
      - name: Deploy to blue environment
        run: echo "Deploying to blue"
  
  test-blue:
    name: Test Blue
    needs: deploy-blue
    steps:
      - name: Test
        run: echo "Testing blue"
  
  switch-to-blue:
    name: Switch Traffic to Blue
    needs: test-blue
    if: success()
    steps:
      - name: Switch
        run: echo "Switching traffic"
```

#### Rolling Deployment:

```yaml
jobs:
  deploy:
    strategy:
      max-parallel: 1  # Deploy satu server pada satu waktu
      fail-fast: false  # Lanjutkan meskipun satu gagal
    steps:
      - name: Deploy to server ${{ matrix.server }}
        run: echo "Deploying to ${{ matrix.server }}"
```

#### Canary Deployment:

```yaml
jobs:
  deploy-canary:
    name: Deploy Canary
    steps:
      - name: Deploy 10% traffic
        run: echo "Deploying canary"
  
  monitor-canary:
    name: Monitor Canary
    needs: deploy-canary
    steps:
      - name: Wait and monitor
        run: sleep 300 && echo "Monitoring"
  
  promote-canary:
    name: Promote to Production
    needs: monitor-canary
    if: success()
    steps:
      - name: Promote
        run: echo "Promoting to 100%"
```

### 11. **Notifications dan Integrations**

```yaml
steps:
  - name: Notify Slack
    if: failure()
    uses: slackapi/slack-github-action@v1
    with:
      webhook-url: ${{ secrets.SLACK_WEBHOOK }}
      payload: |
        {
          "text": "Deployment failed!",
          "blocks": [{
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "Deployment to production failed!"
            }
          }]
        }
  
  - name: Send Email
    uses: dawidd6/action-send-mail@v3
    with:
      server_address: smtp.gmail.com
      server_port: 465
      username: ${{ secrets.EMAIL_USERNAME }}
      password: ${{ secrets.EMAIL_PASSWORD }}
      subject: "Deployment Status"
      body: "Deployment completed successfully!"
```

### 12. **Custom Scripts dan Actions**

```yaml
steps:
  - name: Run custom script
    run: |
      # Bash script
      ./scripts/deploy.sh
      ./scripts/health-check.sh
  
  - name: Use custom action
    uses: ./.github/actions/my-custom-action
    with:
      input1: value1
      input2: value2
```

### 13. **Timeouts dan Retries**

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    timeout-minutes: 30  # Job timeout
    steps:
      - name: Deploy
        timeout-minutes: 10  # Step timeout
        continue-on-error: true  # Lanjutkan meskipun error
        retries: 3  # Retry 3 kali jika gagal
        run: |
          echo "Deploying"
```

### 14. **Workflow Reusability**

#### Reusable Workflows:

```yaml
# .github/workflows/reusable-deploy.yml
name: Reusable Deploy
on:
  workflow_call:
    inputs:
      environment:
        required: true
        type: string
    secrets:
      SSH_KEY:
        required: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to ${{ inputs.environment }}
        run: echo "Deploying"
```

#### Call Reusable Workflow:

```yaml
# .github/workflows/main.yml
name: Main Workflow
on:
  push:
    branches: [ main ]

jobs:
  deploy:
    uses: ./.github/workflows/reusable-deploy.yml
    with:
      environment: production
    secrets:
      SSH_KEY: ${{ secrets.VPS_SSH_KEY }}
```

## 🎨 Contoh Konfigurasi untuk Project Anda

### Contoh 1: Multi-Environment dengan Approval

```yaml
name: Deploy with Approval

on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment'
        required: true
        type: choice
        options:
          - staging
          - production

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ github.event.inputs.environment }}  # Requires approval
    steps:
      - name: Deploy
        run: echo "Deploying to ${{ github.event.inputs.environment }}"
```

### Contoh 2: Conditional Deployment berdasarkan File Changes

```yaml
on:
  push:
    branches: [ main ]

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      dashboard: ${{ steps.changes.outputs.dashboard }}
      mqtt: ${{ steps.changes.outputs.mqtt }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v2
        id: changes
        with:
          filters: |
            dashboard:
              - 'pzem-monitoring/V9-Docker/dashboard/**'
            mqtt:
              - 'pzem-monitoring/V9-Docker/mqtt/**'
  
  deploy-dashboard:
    needs: detect-changes
    if: needs.detect-changes.outputs.dashboard == 'true'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy Dashboard
        run: echo "Deploying dashboard"
  
  deploy-mqtt:
    needs: detect-changes
    if: needs.detect-changes.outputs.mqtt == 'true'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy MQTT
        run: echo "Deploying MQTT"
```

### Contoh 3: Scheduled Tasks

```yaml
on:
  schedule:
    - cron: '0 2 * * *'  # Setiap hari jam 02:00
  workflow_dispatch:

jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
      - name: Backup Database
        run: |
          ssh user@server "pg_dump database > backup.sql"
          # Upload to cloud storage
```

### Contoh 4: Multi-Stage Deployment

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Run tests
        run: pytest
  
  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Build Docker images
        run: docker build -t myapp:${{ github.sha }} .
  
  deploy-staging:
    needs: build
    if: github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to staging
        run: echo "Deploying to staging"
  
  deploy-production:
    needs: build
    if: github.ref == 'refs/heads/main'
    environment: production  # Requires approval
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production
        run: echo "Deploying to production"
```

## 🔧 Best Practices

1. **Gunakan Matrix untuk Test Multiple Versions**
   ```yaml
   strategy:
     matrix:
       python-version: ['3.9', '3.10', '3.11']
   ```

2. **Cache Dependencies untuk Speed**
   ```yaml
   - uses: actions/cache@v3
     with:
       path: ~/.cache/pip
       key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
   ```

3. **Gunakan Environment Protection untuk Production**
   ```yaml
   environment: production  # Requires approval in GitHub settings
   ```

4. **Conditional Steps untuk Efficiency**
   ```yaml
   if: github.ref == 'refs/heads/main'
   ```

5. **Reusable Workflows untuk DRY Principle**
   ```yaml
   uses: ./.github/workflows/reusable-deploy.yml
   ```

## 📊 Comparison: Flexibility Level

| Feature | Flexibility | Notes |
|---------|-------------|-------|
| Triggers | ⭐⭐⭐⭐⭐ | Banyak opsi: push, PR, schedule, manual, dll |
| Jobs | ⭐⭐⭐⭐⭐ | Parallel, sequential, conditional, matrix |
| Runners | ⭐⭐⭐⭐ | Multiple OS, self-hosted, matrix |
| Environment Variables | ⭐⭐⭐⭐⭐ | Global, job, step level, secrets |
| Conditions | ⭐⭐⭐⭐⭐ | Job, step, expression-based |
| Deployment | ⭐⭐⭐⭐⭐ | Multiple strategies, environments |
| Integrations | ⭐⭐⭐⭐⭐ | Slack, email, custom APIs |
| Caching | ⭐⭐⭐⭐ | Dependencies, build artifacts |
| Timeouts | ⭐⭐⭐⭐ | Job, step level, retries |

## 🎯 Kesimpulan

**CI/CD dengan GitHub Actions sangat fleksibel!** Hampir semua aspek bisa dikonfigurasi sesuai kebutuhan:

- ✅ **Trigger Events**: Push, PR, schedule, manual, custom events
- ✅ **Job Dependencies**: Sequential, parallel, conditional
- ✅ **Environment Variables**: Global, job, step level
- ✅ **Deployment Strategies**: Blue-green, rolling, canary
- ✅ **Multi-Environment**: Staging, production, development
- ✅ **Integrations**: Slack, email, custom APIs
- ✅ **Caching**: Speed up builds
- ✅ **Matrix Strategy**: Test multiple configurations
- ✅ **Reusable Workflows**: DRY principle

**Tingkat fleksibilitas: 5/5 ⭐⭐⭐⭐⭐**

Anda bisa mengatur CI/CD sesuai kebutuhan project, dari yang sederhana hingga kompleks dengan multiple environments, approval gates, dan deployment strategies.
