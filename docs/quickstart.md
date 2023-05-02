# Quickstart

The following sections provide the minimum steps required to configure terminal_sync without all those pesky explanations. If you encounter problems or want additional details, please refer to the [Setup](setup.md) page.

These directions assume:

1. You have the following software installed:
    - Git
    - Python 3.10+ and pip **OR** Docker and Docker Compose
2. You will be running the terminal_sync server locally
3. You will be capturing commands from a local Bash session on Linux or a local PowerShell session on Windows

```bash
# Step 1: Get the Code
git clone https://github.com/breakid/terminal_sync
cd terminal_sync

# Step 2: Configure the Server
cp config_template.yaml config.yaml
# ACTION: Modify the gw_url, gw_oplog_id, and gw_api_key_graphql or
#         gw_api_key_rest settings to match your environment

# Step 3: Run the Server

# Step 3a: Docker
touch terminal_sync.log # On Linux
$null > terminal_sync.log # On Windows
docker-compose up -d

# Step 3b: PDM
pip install pdm
pdm install --prod
pdm serve

# Step 4: Setup Terminal Hooks

# Bash:
source terminal_sync.sh
# ACTION: Answer the prompts that appear on first run

# PowerShell:
Import-Module terminal_sync.psm1
```
