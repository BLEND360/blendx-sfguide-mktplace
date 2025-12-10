# BlendX - AI Workflow Platform

BlendX is a native Snowflake application that enables you to build and execute AI workflows using CrewAI.

## Quick Start

### Local Development

To run BlendX locally with Docker Compose:

1. Configure environment:
```bash
cp .env.example .env
# Edit .env with your Snowflake credentials and API keys
```

2. Start services:
```bash
docker-compose up
```

3. Access the application at http://localhost:8000

For detailed local development instructions, see [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md)

### Production Deployment (Snowflake Native App)

For deploying to Snowflake as a Native App, see [scripts/README.md](scripts/README.md)

## Prerequisites

1. Install Docker
    - [Windows](https://docs.docker.com/desktop/install/windows-install/)
    - [Mac](https://docs.docker.com/desktop/install/mac-install/)
    - [Linux](https://docs.docker.com/desktop/install/linux-install/)


## Set your SnowCLI connection (optional, need to be accountadmin)

We use your default connection to connect to Snowflake and deploy the images / app. Set your
default connection by modifying your `config.toml` file or by exporting the following environment variable:

```sh
export SNOWFLAKE_DEFAULT_CONNECTION_NAME=<your connection name>
```

## Deploy the application

Deploy the app package and instance as such:

1. Run provider setup:
```sh
./scripts/provider-setup.sh
```

2. Deploy in setup mode:
```sh
./scripts/deploy.sh --setup-mode
```

3. Edit consumer_example.sql to set your Serper API key:
```sh
# Edit scripts/sql/consumer_example.sql and set your SERPER_API_KEY
```

4. Run consumer setup:
```sh
snow sql -f scripts/sql/consumer_example.sql --connection mkt_blendx_demo
```

5. Create the application:
```sh
./scripts/create-application.sh
```

6. Go to the Snowflake UI and **grant privileges** and **activate** the app.

   When the application is opened for the first time, you will be prompted to grant the following account-level privileges to it:

   - IMPORT PRIVILEGES ON SNOWFLAKE DB
   - EXTERNAL ACCESS INTEGRATION

   Click on the `Grant` button to proceed.

   ![Grant privileges](docs/images/grant.png)

7. In the app UI, go to **Connections** and configure the secret with your API keys.
   Once privileges are granted, a new `Activate` button should appear. Click the button and wait until the application is fully activated.

   ![Configure secret](docs/images/config_secret.png)


8. Deploy the application:
```sh
./scripts/deploy.sh
```

9. Get url to access the app:
```sh
snow sql -q "USE ROLE nac_test; CALL spcs_app_instance_test.app_public.app_url();" --connection mkt_blendx_demo```
```
### Other commands

- Clean up / remove app:
```sh
./scripts/cleanup.sh
```

- Restart the app (calls stop and start):
```sh
./scripts/restart.sh
```

