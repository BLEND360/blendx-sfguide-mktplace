# Local Development with Docker Compose

This guide explains how to run BlendX locally using Docker Compose.

## Prerequisites

- Docker and Docker Compose installed
- Snowflake account with appropriate credentials
- Serper API key

## Setup

### 1. Configure Environment Variables

Copy the example environment file and configure it with your credentials:

```bash
cp .env.example .env
```
Edit `.env` and set the corresponding variables.

### 2. Setup Snowflake Database

Before running the application, ensure your Snowflake database is set up with the required tables.

#### Generate the setup script

First, generate the setup SQL files with your configuration:

```bash
python scripts/generate_local_setup.py \
    --database BLENDX_APP_DEV_DB \
    --schema APP_DATA \
    --role BLENDX_APP_DEV_ROLE \
    --user BLENDX_X_DEV_USER \
    --warehouse BLENDX_APP_DEV_WH
```

This generates two files:
- `local_setup.sql` - Full setup (database, role, grants, tables)
- `local_migrations.sql` - Only migrations (for updating existing DB)

#### JWT Authentication (auto-configured)

If `keys/rsa_key.pub` exists, the script will automatically:
- Create a service user with the same name as `--user`
- Configure JWT authentication with the public key

To generate RSA keys (if you don't have them):

```bash
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out keys/rsa_key.p8 -nocrypt
openssl rsa -in keys/rsa_key.p8 -pubout -out keys/rsa_key.pub
```

To skip service user creation, use `--no-service-user`.

#### Run the setup

```bash
snow sql -f local_setup.sql --connection your_connection_name
```

This will create:
- Database and schema
- Role with appropriate grants (including Snowflake Cortex)
- All required tables (from Alembic migrations)
- Optional service user with JWT auth

#### Updating an existing database

When new migrations are added, regenerate and run only the migrations:

```bash
# Regenerate files (to get latest migrations)
python scripts/generate_local_setup.py \
    --database MY_DEV_DB \
    --schema APP_DATA \
    --role MY_DEV_ROLE \
    --user MY_USERNAME \
    --warehouse MY_DEV_WH

# Apply only migrations
snow sql -f local_migrations.sql --connection your_connection_name
```

## Building Docker Images Locally

Before running with Docker Compose, you need to build the images. Use the build script:

```bash
# Build backend only (default)
./scripts/build-local.sh

# Build all images
./scripts/build-local.sh --all

# Build specific images
./scripts/build-local.sh --frontend
./scripts/build-local.sh --router

# Build with custom tag
./scripts/build-local.sh --all --tag v1.0
```

The script will:
1. Generate `requirements.txt` from `pyproject.toml` (for backend)
2. Build the Docker images with `linux/amd64` platform

## Running the Application

### Option 1: Using Docker Compose

Start all services:

```bash
docker-compose up
```

Or run in detached mode:

```bash
docker-compose up -d
```

### Option 2: Using run-local.sh Script

For development without Docker, you can use the local development script:

```bash
./scripts/run-local.sh
```

#### Available Options:

- `--skip-setup` - Skip dependency installation (useful if dependencies are already installed)
  ```bash
  ./scripts/run-local.sh --skip-setup
  ```

- `--backend-only` - Run only the backend server
  ```bash
  ./scripts/run-local.sh --backend-only
  ```

- `--frontend-only` - Run only the frontend
  ```bash
  ./scripts/run-local.sh --frontend-only
  ```

- `--backend-port N` - Set a custom backend port (default: 8081)
  ```bash
  ./scripts/run-local.sh --backend-port 3000
  ```

- `--frontend-port N` - Set a custom frontend port (default: 8080)
  ```bash
  ./scripts/run-local.sh --frontend-port 5000
  ```

- `-h, --help` - Show help message
  ```bash
  ./scripts/run-local.sh --help
  ```

#### Combining Options:

```bash
# Run only backend on port 3000, skip setup
./scripts/run-local.sh --backend-only --backend-port 3000 --skip-setup

# Run both services with custom ports
./scripts/run-local.sh --backend-port 9000 --frontend-port 3000

# Run only frontend on custom port
./scripts/run-local.sh --frontend-only --frontend-port 4000
```

**Note**: When using `run-local.sh`, the services will run directly on your machine without Docker. Make sure you have Python 3, Node.js, and npm installed.

### Access the application

**When using Docker Compose:**
- **Frontend**: http://localhost:8000
- **API**: http://localhost:8000/api
- **Backend directly**: http://localhost:8081
- **Frontend directly**: http://localhost:8080

**When using run-local.sh:**
- **Backend API**: http://localhost:8081 (or custom port)
- **API Docs**: http://localhost:8081/docs
- **Frontend**: http://localhost:8080 (or custom port)

### View logs

All services:
```bash
docker-compose logs -f
```

Specific service:
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f router
```

### Stop the application

```bash
docker-compose down
```

Remove volumes as well:
```bash
docker-compose down -v
```

## Development Workflow

### Backend Development

The backend code is mounted as a volume, so changes will be reflected immediately with hot-reload.

1. Edit files in `backend/`
2. The backend will automatically reload (gunicorn with auto-reload)

### Frontend Development

The frontend code is also mounted as a volume.

1. Edit files in `frontend/`
2. If using Vue hot-reload, changes will be reflected immediately
3. Otherwise, rebuild: `docker-compose up --build frontend`

### Rebuild Services

After modifying Dockerfiles or dependencies:

```bash
# Rebuild all services
docker-compose up --build

# Rebuild specific service
docker-compose up --build backend
```

## Troubleshooting

### Backend can't connect to Snowflake

1. Verify your `.env` file has correct credentials
2. Check if your IP is whitelisted in Snowflake
3. Verify the role has access to the database and schema

### Serper API not working

1. Verify `SERPER_API_KEY` is set in `.env`
2. Check the backend logs: `docker-compose logs backend`
3. Test the API key directly at https://serper.dev

### Port conflicts

If ports 8000, 8080, or 8081 are already in use:

1. Edit `docker-compose.yml` and change the port mappings:
   ```yaml
   ports:
     - "9000:8000"  # Change external port
   ```

### Database tables don't exist

Generate and run the setup script:
```bash
python scripts/generate_local_setup.py \
    --database MY_DEV_DB \
    --schema APP_DATA \
    --role MY_DEV_ROLE \
    --user MY_USERNAME \
    --warehouse MY_DEV_WH

snow sql -f local_setup.sql --connection your_connection_name
```

## Architecture

The local setup mirrors the production SPCS architecture:

```
┌─────────────────────────────────────────┐
│  Router (Nginx)                         │
│  Port 8000                              │
│  Routes:                                │
│    /      -> Frontend (8080)            │
│    /api   -> Backend (8081)             │
└─────────────────────────────────────────┘
          │                    │
          ▼                    ▼
┌──────────────────┐  ┌──────────────────┐
│  Frontend        │  │  Backend         │
│  Vue.js          │  │  FastAPI         │
│  Port 8080       │  │  Port 8081       │
└──────────────────┘  └──────────────────┘
                               │
                               ▼
                      ┌──────────────────┐
                      │  Snowflake       │
                      │  Database        │
                      └──────────────────┘
```

## Differences from Production

| Feature | Local | Production (SPCS) |
|---------|-------|-------------------|
| Authentication | User/Password | OAuth |
| Secrets | Environment variables | Snowflake Secrets |
| Network | Docker network | SPCS network with External Access Integration |
| Database context | Explicit database/schema | Session context from OAuth |
| Service discovery | Docker service names | Localhost (127.0.0.1) |

## Next Steps

- For production deployment, see [scripts/README.md](scripts/README.md)
- For API documentation, visit http://localhost:8081/docs when running
