# Build a Native App with SPCS

## Overview

In this guide you will learn how to incorporate Snowpark Container Services into a Native App allowing you to deploy a variety of new capabilities to Native App consumers.

## Step-By-Step Guide

For prerequisites, environment setup, step-by-step guide and instructions, please refer to the [QuickStart Guide](https://quickstarts.snowflake.com/guide/build-a-native-app-with-spcs/index.html).

## Connecting with token 

### Create the connection

```bash
snow connection add --connection-name mkt_blendx_admin \
    --account c2gpartners.us-east-1 \
    --user MIKAELA.PISANI@BLEND360.COM \
    --role accountadmin \
    --warehouse wh_nap \
    --database spcs_app_test \
    --schema napp \
    --host c2gpartners.us-east-1.snowflakecomputing.com \
    --port 443 \
    --region us-east-1 \
    --authenticator SNOWFLAKE_JWT \
    --private-key-file /Users/mikaelapisani/Projects/blendx-sfguide-mktplace/keys/rsa_key.p8 \
    --no-interactive

```
### Test the connection
```bash
snow connection test --connection mkt_blendx_admin
```

### Docker login with token 


### Configure image reposotory

```bash
./configure 
```

### Build docker images and push
```bash
make all
```

### Remove existing app and deploy new one
```bash
./deploy.sh
```
