# Automatic Deployment Guide

This guide explains how to set up and use the automatic CI/CD deployment pipeline for the BlendX Marketplace application.

## Branch Flow

```mermaid
flowchart LR
    subgraph Development
        A[develop] -->|merge| B[qa]
    end

    subgraph QA
        B -->|deploy-qa.yml| C[Build Images]
        C --> D[Deploy to QA Channel]
        D --> E[Upgrade App]
    end

    subgraph Production
        B -->|merge| F[main]
        F -->|release.yml| G[Create Tag]
        G -->|trigger| H[deploy-prod.yml]
        H --> I[Promote to DEFAULT]
    end

    style A fill:#e1f5fe
    style B fill:#fff3e0
    style F fill:#e8f5e9
    style I fill:#f3e5f5
```

### Pipeline Flow

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant GH as GitHub
    participant QA as QA Pipeline
    participant Rel as Release Pipeline
    participant Prod as Prod Pipeline
    participant SF as Snowflake

    Dev->>GH: merge develop → qa
    GH->>QA: trigger deploy-qa.yml
    QA->>SF: Build & push images
    QA->>SF: Register patch in QA channel
    QA->>SF: Upgrade application

    Dev->>GH: merge qa → main
    GH->>Rel: trigger release.yml
    Rel->>GH: create tag (release/vX.Y.Z)
    Rel->>Prod: trigger deploy-prod.yml
    Prod->>SF: Read QA version
    Prod->>SF: Promote to DEFAULT channel
```

| Branch | Environment | Purpose |
|--------|-------------|---------|
| `develop` | Local | Local development and testing (no CI) |
| `qa` | QA | Builds images, deploys to QA release channel (merge from develop) |
| `main` | Production | Auto-creates release tag, triggers production deploy (merge from qa) |

## Prerequisites

Before setting up automatic deployment, ensure you have:

1. A Snowflake account with ACCOUNTADMIN access (for initial setup)
2. Access to the GitHub repository settings
3. The Snowflake CLI installed locally (`snow`)

## Initial Setup (One-Time)

### Step 1: Generate RSA Key Pair

Generate the RSA keys for JWT authentication:

```bash
mkdir -p keys/pipeline
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out keys/pipeline/snowflake_key.p8 -nocrypt
openssl rsa -in keys/pipeline/snowflake_key.p8 -pubout -out keys/pipeline/snowflake_key.pub
```

> **Important**: Keep `snowflake_key.p8` secure. This is your private key and should never be committed to the repository.

### Step 2: Run Provider Setup Script

The setup script creates the CI/CD user, role, and necessary permissions in Snowflake:

```bash
# Ensure you have a connection with ACCOUNTADMIN role configured
./scripts/provider-setup.sh
```

The script will:
1. Create a service user (`MK_BLENDX_DEPLOY_USER`) with JWT authentication
2. Create a role (`MK_BLENDX_DEPLOY_ROLE`) with necessary permissions
3. Grant permissions on warehouse, database, schema, stage, and image repository
4. Grant permission to create Application Packages
5. Optionally create the Application Package

### Step 3: Configure GitHub Secrets

In your GitHub repository, go to **Settings > Secrets and variables > Actions** and create two environments:

#### Environment: `qa`

| Secret | Description | Example |
|--------|-------------|---------|
| `SNOWFLAKE_ACCOUNT` | Snowflake account identifier | `xy12345.us-east-1` |
| `SNOWFLAKE_HOST` | Snowflake host URL | `xy12345.us-east-1.snowflakecomputing.com` |
| `SNOWFLAKE_DEPLOY_USER` | CI/CD user name | `MK_BLENDX_DEPLOY_USER` |
| `SNOWFLAKE_DEPLOY_ROLE` | CI/CD role name | `MK_BLENDX_DEPLOY_ROLE` |
| `SNOWFLAKE_WAREHOUSE` | Warehouse name | `DEV_WH` |
| `SNOWFLAKE_DATABASE` | Database name | `SPCS_APP_TEST` |
| `SNOWFLAKE_SCHEMA` | Schema name | `NAPP` |
| `SNOWFLAKE_PRIVATE_KEY_RAW` | Content of `snowflake_key.p8` | (full PEM content) |
| `SNOWFLAKE_REPO` | Image repository URL | `xy12345.registry.snowflakecomputing.com/spcs_app_test/napp/img_repo` |
| `SNOWFLAKE_APP_PACKAGE` | Application package name | `MK_BLENDX_APP_PKG` |
| `SNOWFLAKE_APP_INSTANCE` | Installed app instance name | `BLENDX_APP` |
| `SNOWFLAKE_COMPUTE_POOL` | Compute pool for the app | `MY_COMPUTE_POOL` |
| `SNOWFLAKE_ROLE` | Role for app management | `nac_test` |

#### Environment: `production`

Configure the same secrets for production, potentially with different values for production resources.

### Step 4: Get the Private Key Content

To copy the private key content for the GitHub secret:

```bash
cat keys/pipeline/snowflake_key.p8
```

Copy the **entire content** including the `-----BEGIN PRIVATE KEY-----` and `-----END PRIVATE KEY-----` headers.

## Pipelines Overview

| Pipeline | File | Trigger | Purpose |
|----------|------|---------|---------|
| QA Deployment | `deploy-qa.yml` | Push to `qa` (merge from develop) | Build, deploy, and restart QA environment |
| Create Release Tag | `release.yml` | Push to `main` or manual | Auto-create release tag and trigger production deploy |
| Production Release | `deploy-prod.yml` | Called by `release.yml` or manual | Promote QA version to production |

## QA Pipeline (deploy-qa.yml)

### Trigger

- **Automatic**: Push to `qa` branch (must be merged from `develop`)
- **Manual**: GitHub Actions workflow dispatch

### Preflight Validation

Before building, the pipeline validates:
- `qa` branch must contain all commits from `develop`
- `qa` must be updated via merge commit from `develop` (no direct commits)

### Steps

1. Validates that `qa` was updated via a merge from `develop`
2. Builds Docker images for backend, frontend, and router (parallel)
3. Pushes images to Snowflake Image Repository
4. Generates `setup.sql` from templates
5. Uploads application files to Snowflake stage
6. Creates the Application Package if it doesn't exist
7. Registers a new patch in the QA release channel
8. Upgrades and restarts the application (if installed)

### Version Strategy

- Version is derived from git tags: `v1.x.x` → `V1`, `v2.x.x` → `V2`
- Each push to `qa` adds a new patch to the current version
- Default version is `V1` if no tags exist

## Release Tag Pipeline (release.yml)

### Trigger

- **Automatic**: Push to `main` branch (merge from qa)
- **Manual**: GitHub Actions workflow dispatch with optional version input

### Auto-increment

When triggered automatically (push to main), the tag version is auto-incremented:
- If no `release/*` tags exist: `release/v1.0.0`
- Otherwise: increments patch number (e.g., `release/v1.0.0` → `release/v1.0.1`)

### Output

Creates an annotated tag on `main` and directly triggers the `deploy-prod.yml` workflow via `workflow_dispatch`.

## Production Pipeline (deploy-prod.yml)

### Trigger

- **Automatic**: Called by `release.yml` after creating the tag
- **Manual**: GitHub Actions workflow dispatch with optional version/patch inputs

### Steps

1. Reads the latest version and patch from the QA release channel
2. Validates the promotion is monotonic (no regressions)
3. Promotes the QA version to the DEFAULT (production) release channel
4. Sets the DEFAULT release directive

### Manual Override

When triggering manually, you can specify:
- `version`: Version to release (e.g., `V1`)
- `patch`: Patch number to release (e.g., `5`)

If not specified, values are auto-detected from QA channel.

## Release Channels

| Channel | Purpose | Updated by |
|---------|---------|------------|
| `QA` | Testing and development | QA pipeline on every push to `qa` |
| `DEFAULT` | Production (marketplace consumers) | Production pipeline (triggered by `release.yml`) |

> **Note**: Versions in DEFAULT channel require Snowflake security review before they are available to marketplace consumers.

## Typical Workflow

1. Developer creates feature branch from `develop`
2. Developer creates PR to `develop`
3. PR is merged to `develop`
4. When ready for QA: merge `develop` → `qa`
5. QA pipeline triggers → builds images, deploys, restarts service
6. QA testing is performed
7. When ready for release: merge `qa` → `main`
8. Release tag is auto-created (e.g., `release/v1.0.1`)
9. Production pipeline is triggered → promotes QA version to DEFAULT channel
10. Submit for Snowflake security review (manual step in Provider Studio)
11. After approval, version is available on Marketplace

## Database Migrations

The application uses Alembic for database schema management. SQLAlchemy models are the source of truth for the database schema.

### How Migrations Work in the Native App

Since Snowflake Native Apps cannot run Python migrations directly, the system converts Alembic migrations to idempotent SQL:

1. **Development**: Developers create/modify SQLAlchemy models and generate Alembic migrations
2. **Build**: `generate_migrations_sql.py` converts migrations to idempotent SQL files
3. **Deployment**: SQL is injected into `setup.sql` via the `{{MIGRATIONS_SQL}}` placeholder
4. **Upgrade**: All SQL uses `IF NOT EXISTS` / `IF EXISTS` clauses, making upgrades safe

```mermaid
flowchart LR
    A[SQLAlchemy Models] -->|alembic revision| B[Alembic Migration .py]
    B -->|generate_migrations_sql.py| C[Individual .sql files]
    C --> D[migrations.sql combined]
    D -->|generate-app-files.py| E[setup.sql]
    E -->|app install/upgrade| F[Database Updated]
```

### Idempotent Migrations for Upgrades

All generated SQL is idempotent to support incremental upgrades:

```sql
-- Tables: CREATE TABLE IF NOT EXISTS
CREATE TABLE IF NOT EXISTS app_data.my_table (...);

-- Columns: ADD COLUMN IF NOT EXISTS
ALTER TABLE app_data.my_table ADD COLUMN IF NOT EXISTS new_column VARCHAR(255);

-- Version tracking: INSERT only if not exists
INSERT INTO app_data.alembic_version (version_num)
SELECT '002_add_column' WHERE NOT EXISTS (
    SELECT 1 FROM app_data.alembic_version WHERE version_num = '002_add_column'
);
```

This means:
- **New installation**: All tables and columns are created
- **Upgrade**: Only new tables/columns are added, existing data is preserved

### Creating New Migrations

When you need to modify the database schema:

1. **Modify SQLAlchemy models** in `backend/app/database/models/`
2. **Generate migration** from the backend directory:
   ```bash
   cd backend
   alembic revision --autogenerate -m "description_of_change"
   ```
3. **Review the generated file** in `backend/alembic/versions/` and adjust if needed
4. **Regenerate SQL**:
   ```bash
   python scripts/generate_migrations_sql.py
   ```
5. **Commit** the model changes, migration file, AND generated SQL files

### Generated Files Structure

```
scripts/sql/
├── migrations/                          # Individual migration files
│   ├── 001_initial_schema.sql          # First migration
│   ├── 002_add_new_column.sql          # Second migration
│   └── ...
├── migrations.sql                       # Combined file (all migrations)
└── migrations_manifest.json             # Metadata about migrations
```

### Local Development Commands

Run these commands from the `backend/` directory:

| Command | Description |
|---------|-------------|
| `alembic revision --autogenerate -m "desc"` | Create new migration from model changes |
| `alembic upgrade head` | Apply all pending migrations (local dev) |
| `alembic history` | View migration history |
| `alembic downgrade -1` | Rollback last migration (local dev) |
| `alembic current` | Show current migration version |

From the project root:

| Command | Description |
|---------|-------------|
| `python scripts/generate_migrations_sql.py` | Regenerate SQL from Alembic migrations |

### Migration Files Reference

| File/Directory | Purpose |
|----------------|---------|
| `backend/alembic/` | Alembic configuration directory |
| `backend/alembic/versions/` | Migration scripts (Python) |
| `backend/app/database/models/` | SQLAlchemy models (source of truth) |
| `scripts/generate_migrations_sql.py` | Converts Alembic migrations to SQL |
| `scripts/sql/migrations/` | Individual SQL migration files |
| `scripts/sql/migrations.sql` | Combined SQL (auto-generated) |
| `scripts/sql/migrations_manifest.json` | Migration metadata |
| `templates/setup_template.sql` | Template with `{{MIGRATIONS_SQL}}` placeholder |

### CI/CD Integration

The migration SQL is automatically generated during the QA deployment pipeline:

1. `generate-app-files.py` calls `generate_migrations_sql.py`
2. Individual `.sql` files are generated in `scripts/sql/migrations/`
3. Combined `migrations.sql` is injected into `setup.sql`
4. When installed/upgraded, idempotent SQL ensures correct schema state

### Pre-commit Hook

A pre-commit hook warns if you modify models or migrations without regenerating SQL:

```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install
```

The hook checks if `migrations.sql` was updated when you change:
- `backend/app/database/models/*.py`
- `backend/alembic/versions/*.py`

> **Note**: The `alembic_version` table tracks which migrations have been applied. Use `CALL app_data.get_migration_status()` to check the current state.

## Considerations

- **Private Key Security**: Never commit `snowflake_key.p8` to the repository
- **Environment Secrets**: Use separate GitHub environments (`qa`, `production`) with different secrets
- **Least Privilege**: CI/CD role only has permissions it needs
- **Version Limits**: Snowflake allows max 2 versions not in any release channel (pipeline auto-cleans orphans)
- **Security Review**: Versions in DEFAULT channel require Snowflake approval before marketplace availability

## Files Reference

| File | Purpose |
|------|---------|
| `.github/workflows/deploy-qa.yml` | QA deployment workflow |
| `.github/workflows/release.yml` | Auto-creates release tags and triggers production deploy |
| `.github/workflows/deploy-prod.yml` | Production promotion workflow (QA → DEFAULT) |
| `scripts/provider-setup.sh` | Initial setup script |
| `scripts/sql/setup_cicd_permissions.sql` | SQL permissions reference |
