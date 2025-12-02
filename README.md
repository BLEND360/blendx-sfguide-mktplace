# Instructions

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

1. First time:
```sh
./scripts/complete-setup.sh
```

2. Update app:
```sh
./scripts/deploy.sh
```

3. Clean up / remove app:
```sh
./scripts/cleanup.sh
```

4. Restart the app (calls stop and start):
```sh
./scripts/restart.sh
```

## Setup the application

When the application is opened for the first time, you will be prompted to grant the following account-level privileges to it:

- CREATE COMPUTE POOL
- BIND SERVICE ENDPOINT

Click on the `Grant` button to proceed.

## Activate the application

Once privileges are granted, a new `Activate` button should appear. Click the button and wait until the application is fully activated.
The `Activate` button invokes the `grant_callback` defined in the [manifest.yml](app/manifest.yml) file, which then creates the `COMPUTE POOL` and `SERVICE` needed to launch the application.

## Grant Snowflake Cortex Permissions

**IMPORTANT**: After activating the application, you must grant Cortex permissions for the application to access LLMs:

```sql
-- Grant Cortex user role to the application
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO APPLICATION <your_app_name>;

-- Grant imported privileges on Snowflake database
-- Required for REST API access to Cortex
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO APPLICATION <your_app_name>;
```

Or you can execute the script below:

```sh
snow sql -f grant_cortex_permissions.sql --connection <your_connection_name>```
```
