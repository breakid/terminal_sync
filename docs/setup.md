# Setup

## Introduction

The following is a high-level overview of the steps required to setup terminal_sync. Additional details are provided in the sections below.

1. [Get the Code](#1-get-the-code)
2. [Configure the Server](#2-configure-the-server)
3. [Run the Server](#3-run-the-server)
    - [Docker](#docker)
    - [PDM](#pdm)
4. [Setup Terminal Hooks](#4-setup-terminal-hooks)
    - [Bash](#bash)
    - [PowerShell](#powershell)

If you encounter problems, please refer to the [Troubleshooting](troubleshooting.md) page.

**Prerequisites**: These instructions assume you have either Python 3.10+ and pip or Docker and Docker Compose installed.

---

## 1. Get the Code

Use `git` to clone this repo, or download and extract a zip archive of the files.

```bash
git clone https://github.com/breakid/terminal_sync
cd terminal_sync
```

All subsequent instructions are provided from the context of the root project directory.

---

## 2. Configure the Server

The server can be configured using a YAML config file, environment variables, or a combination thereof, with environment variables overriding config file values. By default, terminal_sync will look for `config.yaml` in the current working directory (relative to where you run the server). You may use the `TERMSYNC_CONFIG` environment variable to specify an alternate config file path.

An example configuration file, `config_template.yaml`, is provided and contains comments that explain the purpose of each setting. To create a new config file, we recommend that you copy this template and edit the copy to meet your needs.

```bash
cp config_template.yaml config.yaml
```

Environment variables match the upper-case version (on case-sensitive systems) of the setting name found in the config file. For instance, the config file settings `gw_url` and `gw_oplog_id` become the environment variables `GW_URL` and `GW_OPLOG_ID`. The values are parsed as YAML, so all options found in the config file are supported, including complex structures such as lists and dictionaries.

The server will automatically load any environment variables defined in a `.env` file.

At a minimum, the `gw_url`, `gw_oplog_id`, and at least one of `gw_api_key_graphql` or `gw_api_key_rest` must be configured for terminal_sync to log to GhostWriter. If both API keys are set, terminal_sync will use GraphQL by default.

**Note**: To allow terminal_sync to be used off-line or independent of GhostWriter, the server will display a warning but _**start successfully**_ even if these values are not provided. In this case, local logging will be enabled by default.

---

## 3. Run the Server

The server can be run as a Docker container or using [PDM](https://pdm.fming.dev/latest/).

### Docker

While there is not currently a pre-built image, a `Dockerfile` and `docker-compose.yaml` config are provided to simplify the build process. The default Compose config assumes:

1. You created a `config.yaml` file in the previous step
2. You have a `terminal_sync.log` file in the root project directory
    - This will be bind mounted into the container to persist application logs
    - Use `touch terminal_sync.log` in Bash or `$null > terminal_sync.log` in PowerShell to initialize this file

If you prefer to use environment variables rather than a config file, uncomment the `environment` section, fill in the appropriate values, and comment out or remove the `config.yaml` volume entry.

**Note**: If the `config.yaml` or `terminal_sync.log` files do not exist, Compose will create an empty directory for each missing source path. If you choose not to use these volumes, comment out or remove them from the Compose config.

Once you have made any desired modifications to the Compose config, use the following command to start the server, optionally in detached mode (`-d`). On first run, Docker Compose should automatically build a local copy of the image, which will be used for subsequent executions.

```bash
docker-compose up -d
```

If you need to rebuild the image, such as after making or pulling changes to the code, add the `--build` flag to the command.

```bash
docker-compose up -d --build
```

When running in detached mode, you won't see any output from the container. Use the following command to view the logs; this is especially useful for troubleshooting.

```bash
docker-compose logs
```

If the build fails, you may need to build the image manually using Docker.

```bash
docker build --network=host --tag=terminal_sync:latest .
```

To stop the server, run the following:

```bash
docker-compose down
```

### PDM

If you have Python 3.10 or later, you can run the server using PDM.

```bash
# Install PDM
pip install pdm

# Use PDM to install the production dependencies and terminal_sync package
pdm install --prod

# Use the PDM 'serve' script to run the application with uvicorn
# Note: This will run the server in the foreground, occupying your terminal
pdm serve
```

To stop the server, press `CTRL+C`. If that doesn't work, kill the `uvicorn` process manually.

---

## 4. Setup Terminal Hooks

### Bash

1. Review and optionally edit the **Configuration Settings** section at the top of `terminal_sync.sh`
2. Run `source ./terminal_sync.sh`
    - **Note**: This must be done in each new bash session
    - You will be prompted to install any missing dependencies
    - On first run, you will also be prompted whether you want to install the hooks (i.e., automatically source the script in each new session)

If you decide later that you want to install the hooks, just append `source '<PATH_TO>/terminal_sync.sh'` to your `~/.bashrc` file.

### PowerShell

1. Review and optionally edit the **Configuration Settings** section at the top of `terminal_sync.psm1`
2. Run `Import-Module terminal_sync.psm1`
    - **Note**: This must be done in each new PowerShell session
    - If this fails, you may need to use `Set-ExecutionPolicy` to allow scripts

If you want to load the module automatically, run the following:

```bash
# Set the execution policy to allow scripts to run
# Alternatively, you can set the policy to 'Bypass' to disable all warnings
Set-ExecutionPolicy Unrestricted -Scope CurrentUser

# Add terminal_sync.psm1 to your PowerShell profile so it will be loaded automatically
Write-Output "Import-Module '$(Resolve-Path terminal_sync.psm1)'" | Out-File -Append -Encoding utf8 $PROFILE
```
