# terminal_sync

## Overview

terminal_sync is a standalone tool for logging Bash and PowerShell commands to [Ghostwriter](https://github.com/GhostManager/Ghostwriter) automatically. The provided Bash script and PowerShell module register pre-exec and post-exec hooks that capture and send information about executed commands to the terminal_sync server for additional processing and enrichment. Once properly configured, any commands that meet the configured logging criteria (e.g., contain a specific keyword) are sent to Ghostwriter.

---

## Features

- **Automatic Shell Logging**
      - Logs Bash and PowerShell commands directly to Ghostwriter based on a configurable keyword list

- **Export Log Entries to CSV**
      - Saves failed (or optionally all) command log entries to JSON files that can be [converted to CSV](usage.md#export-logs-to-ghostwriter-csv) and imported into Ghostwriter
      - Supports off-line logging

- **Command Timestamps**
      - Displays execution and completion timestamps for each command
      - Useful reference for commands not configured to auto-log

- **In-line Descriptions**
      - Supports [adding a description](usage.md#add-a-description) to the end of a command
      - Allows users to [force an individual command to be logged](usage.md#log-ad-hoc-commands)
      - Maintains flow by keeping users at the command-line

- **Simple Configuration**
      - Easy [setup and configuration using YAML config file and/or environment variables](setup.md#2-configure-the-server)

- **Management Commands**
      - Ability to [enable/disable terminal_sync](usage.md#enable--disable-terminal_sync) or [change the verbosity](usage.md#adjust-console-output-at-runtime) for an individual session

---

## Known Limitations

- Background jobs (i.e., Bash commands ending with `&` and PowerShell `Start-Job` commands) will always be reported as successful since the post-exec hook runs when the prompt returns, which happens before the command completes.

### Bash Limitations

- Compound commands (i.e., multiple commands joined by `&&`) run in the background will not be logged
      - These commands trigger the `precmd` (i.e., post-exec) hook but not the `preexec` hook; however, the current post-exec implementation relies on a variable set in the pre-exec hook to prevent logging duplicate entries when a user submits an empty line

---

## Local vs Remote Usage

The terminal_sync server is intended to be run locally and therefore does not include authentication or encryption. Should you choose to run the server on a remote host, it is highly recommended that you run it on `localhost` and use an SSH forward tunnel, or similar mechanism, to access it.

Similarly, terminal_sync was (mostly) designed with a single user per instance in mind. The one exception is that if the `OPERATOR` environment variable is set within a client shell session, this value will override the operator setting on the server, thus allowing multiple users to share a terminal_sync server. That said, the server itself only supports a single API key / token per instance, so make sure all users with access to the server are authorized for that level of access to Ghostwriter.
