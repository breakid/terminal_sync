# terminal_sync

terminal_sync is a standalone tool for logging Bash and PowerShell commands to [GhostWriter](https://github.com/GhostManager/Ghostwriter) automatically. The provided Bash script and PowerShell module register pre-exec and post-exec hooks that capture executed commands and function as clients, sending command information to the terminal_sync server for additional processing and enrichment. Any commands that meet the logging criteria (e.g., contain a specific keyword) are sent to GhostWriter.

The terminal_sync server is intended to be run locally and therefore does not include authentication or encryption. Should you choose to run the server on a remote host, it is highly recommended that you run it on `localhost` and use an SSH forward tunnel to access it.

Similarly, terminal_sync was (mostly) designed with a single user per instance in mind. The one exception is that if the `OPERATOR` environment variable is set within a client shell session, this value will override the `operator` setting on the server, thus allowing multiple users to share a terminal_sync server. That said, the server itself only supports a single API key / token per instance, so make sure all users with access to the server are authorized for that level of access to GhostWriter.

For the purpose of this documentation, the terms "API key" and "token" are used interchangeably.

---

## Getting Started

**Prerequisites**: These instructions assume you have Python3 and pip installed. Additionally, if you want to use Docker, it is assumed you already have Docker and Docker Compose installed.

1. Clone this repo, or download and extract a zip archive of the files

    ```bash
    git clone https://github.com/breakid/terminal_sync
    cd terminal_sync
    ```

2. Configure the server

    1. Create a `config.yaml` file

        ```bash
        copy src/terminal_sync/config_template.yaml config.yaml
        ```

    2. Edit `config.yaml` and provide appropriate values for: `gw_url`, `gw_oplog_id`, and at least one of `gw_api_key_graphql` or `gw_api_key_rest`
        - If both are set, terminal_sync will use GraphQL
    3. Optionally, modify other settings to suit your needs

    - Alternatively, any setting that appears in `config.yaml` can be set using an environment variable matching the upper-case version of the setting name (e.g., `GW_URL`, `GW_OPLOG_ID`, etc.)
    - The environment variable `TERMSYNC_CONFIG` can be used to specify the path to a custom config file

3. Run the server
    - Using Docker and Docker Compose (**recommended**)

        ```bash
        docker-compose up -d
        ```

        - The compose config will build the image locally and reuse this image for subsequent executions
        - To stop the server, run `docker-compose down`
        - Subsequent executions will reuse the locally build image; to force a rebuild, append `--build` to the command above

    - Using Python
        1. Install PDM

            ```bash
            pip install pdm
            ```

        2. Use PDM to install the dependencies and terminal_sync package

            ```bash
            pdm install --prod
            ```

        3. Run the server using uvicorn (**Note**: This will run the server in the foreground, occupying your terminal)

            ```bash
            pdm serve
            ```

            - To stop the server, press `CTRL+C`
            - uvicorn may ignore `CTRL+C`, in this case, simply kill the `uvicorn` process

4. Setup Terminal Hooks

    - Bash

        1. Edit the **Configuration Settings** section at the top of `terminal_sync.sh`
        2. Run `chmod +x ./terminal_sync.sh && ./terminal_sync.sh`
            - **Note**: This must be done in each new bash session
            - You will be prompted to install any missing dependencies
            - On first run, you will also be prompted whether you want to install the hooks permanently

        - If you want to install the hooks later, just append `source <PATH_TO>/terminal_sync.sh` to your `~/.bashrc` file.

    - PowerShell

        1. Edit the **Configuration Settings** section at the top of `terminal_sync.psm1`
        2. Run `Import-Module terminal_sync.psm1`
            - **Note**: This must be done in each new PowerShell session

        - If you want the module to load automatically, run the following:

            ```powershell
            # Set the execution policy to allow scripts to run
            # Alternatively, you can set the policy to 'Bypass' to disable all warnings
            Set-ExecutionPolicy Unrestricted -Scope CurrentUser

            # Ensure the PowerShell modules directory exists
            # If you receive an error message stating that the directory already exists, you may disregard it
            mkdir $PROFILE\..\Modules

            $ModuleDir = Resolve-Path "$PROFILE\..\Modules"

            # Copy terminal_sync module to your PowerShell modules directory
            Copy-Item .\terminal_sync.psm1 $ModuleDir

            # Add terminal_sync.psm1 to your PowerShell profile so it will be loaded automatically
            Write-Output "Import-Module '$ModuleDir\terminal_sync.psm1'" | Out-File -Append -Encoding utf8 $PROFILE
            ```

---

## Updating terminal_sync

1. Use `git pull` to get the latest updates or download an updated zip archive from GitHub
2. Update the server
    - If using Docker, run `docker-compose up -d --build` to rebuild the image
    - If using Python, run `pdm install --prod` to install any new or updated packages
3. Update any installed terminal hooks
    - For Bash, copy the new `terminal_sync.sh` to the location referenced in your `~/.bashrc`, overwriting the previous version
    - For PowerShell, run `Copy-Item .\terminal_sync.psm1 $(Resolve-Path "$PROFILE\..\Modules")`

---

## Usage

The entire point of terminal_sync is to log shell commands automatically; therefore, once the server is configured / started and the hooks are registered, no further action is required. That said, there are a few options that may improve your experience.

### Set the Source Host

You may set the environment variable `SRC_HOST` to the host where your activity will originate. This is particularly useful when operating over a SOCKS proxy or tunnel. If not set, the source will be the host where the terminal_sync server is running.

### Enable / Disable terminal_sync

To temporarily disable terminal_sync in a session after the hooks are registered, run `Disable-TermSync`. To re-enable it, run `Enable-TermSync`. These commands set a flag that is checked when each hook is run, skipping the hook logic if disabled, and consequently only affect the current session.

To permanently disable terminal_sync, delete or comment out the line in `~/.bashrc` or your PowerShell `$PROFILE` that loads the hooks.

### Adjust Console Output at Runtime

Both the Bash script and PowerShell module contain a configuration setting that allows you to set the default console output. If you want to (temporarily) change this for a session, use one of the following commands.

In Bash, run `set_termsync_versbosity`; this will print a list of display settings and prompt you for a number. Simply enter the number that matches your preferred setting.

In PowerShell, type `Set-TermSyncVerbosity`, followed by a space, then press **TAB** to cycle through the available options. Press **Enter** to select your preferred setting.

---

## Known Limitations

- Background jobs (i.e., Bash commands ending with `&` and PowerShell `Start-Job` commands) will always be reported as successful since the post-exec hook runs when the prompt returns, which happens before the command completes.

### Bash Limitations

- Compound commands (i.e., multiple commands joined by `&&`) run in the background will not be logged
  - These commands trigger the `precmd` (i.e., post-exec) hook but not the `preexec` hook; the current post-exec implementation relies on a variable set in the pre-exec hook to prevent logging duplicate entries when a user submits an empty line

---

## Development and Test Environments

Development and testing were performed using the following configurations. If you encounter any problems attributable to a different environment, please submit a GitHub issue; be sure to include a detailed description of the problem and relevant information about your environment. I can't fix what I can't replicate.

- Windows 11 (terminal_sync server and PowerShell hooks)
  - Docker 20.10.24, build 297e128
  - Docker Compose v2.17.2
  - PowerShell 5.1.22621.963
  - Python 3.11
- Debian 11 (Bash hooks)
  - Python 3.9.2
- GhostWriter running over HTTPS

---

## Troubleshooting

The following is a list of potential errors identified during testing and potential ways to resolve them.

### Server Problems

| Error Message                      | Problem | Solution |
| ---------------------------------- | ------- | -------- |
| `No GhostWriter API key specified` | Neither a GraphQL nor REST API key were provided| Make sure to enter a valid API key for at least one of these settings in the `config.yaml` file or set the `GW_API_KEY_GRAPHQL` or `GW_API_KEY_REST` environment variables.|

### Client Problems

| Error Message                                                                | Problem                                                                    | Solution                                                                                                                                                                              |
| ---------------------------------------------------------------------------- | -------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Cannot connect to host <GHOSTWRITER_SERVER> ssl:False [getaddrinfo failed]` | terminal_sync is unable to resolve the hostname of your GhostWriter server | 1. Verify the `gw_url` setting contains the correct hostname<br />2. Verify connectivity to your GhostWriter server (e.g., check any VPNs, SSH tunnels, etc.)<br />3. Check your DNS settings |
| `Cannot connect to host <GHOSTWRITER_SERVER> ssl:False [The remote computer refused the network connection]` |terminal_sync can reach the GhostWriter server, but the port is blocked| 1. Verify the `gw_url` setting contains any applicable port numbers<br />2. Check the firewall settings on your GhostWriter server|
|`Authentication hook unauthorized this request` | Your GraphQL token is invalid | 1. Verify your token hasn't expired<br />2. Verify the token you specified is correct and complete<br />3. Generate a new GraphQL token key|
|`check constraint of an insert/update permission has failed`|You're using the GraphQL API, and either the Oplog ID you're trying to write to doesn't exist, or you don't have permission to write to it|1. Verify an Oplog with the specified ID exists<br />2. Verify your user account is assigned to the project to which the specified Oplog belongs|
|`Authentication credentials were not provided`|You're using the REST API and provided an API key, but your `gw_url` is using `http://` rather than `https://`|Modify your `gw_url` to use `https://`|
|`404, message='Not Found', url=URL('https://<GHOSTWRITER_SERVER>/v1/graphql')`|While there are likely many causes for this generic issue, this was observed when using the GraphQL API and a `gw_url` containing `http://` rather than `https://`|Modify your `gw_url` to use `https://`|

---

## References

- [Ghostwriter](https://github.com/GhostManager/Ghostwriter) - Engagement Management and Reporting Platform
- [Ghostwriter Documentation - Operation Logs](https://www.ghostwriter.wiki/features/operation-logs) - Guidance on operation logging setup and usage with Ghostwriter

---

## Credits

Many thanks to:

- Everyone who contributed to [GhostWriter](https://github.com/GhostManager/Ghostwriter) and specifically [chrismaddalena](https://github.com/chrismaddalena), [its-a-feature](https://github.com/its-a-feature), and [hotnops](https://github.com/hotnops) for their work on [mythic_sync](https://github.com/GhostManager/mythic_sync) (GraphQL) and [mythic-sync](https://github.com/hotnops/mythic-sync) (REST), from which terminal_sync "borrowed" liberally
- [rcaloras](https://github.com/rcaloras) and everyone who contributed to [bash-preexec](https://github.com/rcaloras/bash-preexec)
  - Finding this tool inspired me to build the first prototype of what later became terminal_sync
