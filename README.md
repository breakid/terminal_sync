# terminal_sync

**No Longer Maintained**: I rewrote terminal_sync as a pure CLI application, without the overhead, complexity, or security risks of FastAPI. This new version also supported plugin-based command parsing; however, testing was incomplete when I lost motivation to work on this project. After intending to finish these changes for almost a year, I've decided to officially shelve this project. For anyone who is interested, I highly recommend checking out and finishing the new version, which is available on the `cli_client` branch. I'll leave the project active, for now, in case anyone wants to submit a pull request for the finalized CLI client.

terminal_sync is a standalone tool for logging Bash and PowerShell commands to [GhostWriter](https://github.com/GhostManager/Ghostwriter) automatically. The provided Bash script and PowerShell module register pre-exec and post-exec hooks that capture executed commands and function as clients, sending command information to the terminal_sync server for additional processing and enrichment. Any commands that meet the logging criteria (e.g., contain a specific keyword) are sent to GhostWriter.

For more information, including [how to get started](https://breakid.github.io/terminal_sync/setup), please refer to our [documentation](https://breakid.github.io/terminal_sync/)

---

## Features

- **Automatic Shell Logging**
      - Logs Bash and PowerShell commands directly to GhostWriter based on a configurable keyword list

- **Export Log Entries to CSV**
      - Saves failed (or optionally all) command log entries to JSON files that can be [converted to CSV](usage.md#export-logs-to-ghostwriter-csv) and imported into GhostWriter
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

## References

- [Ghostwriter](https://github.com/GhostManager/Ghostwriter) - Engagement Management and Reporting Platform
- [Ghostwriter Documentation - Operation Logs](https://www.ghostwriter.wiki/features/operation-logs) - Guidance on operation logging setup and usage with Ghostwriter

---

## Credits

Many thanks to:

- Everyone who contributed to [GhostWriter](https://github.com/GhostManager/Ghostwriter) and specifically [chrismaddalena](https://github.com/chrismaddalena), [its-a-feature](https://github.com/its-a-feature), and [hotnops](https://github.com/hotnops) for their work on [mythic_sync](https://github.com/GhostManager/mythic_sync) (GraphQL) and [mythic-sync](https://github.com/hotnops/mythic-sync) (REST), from which terminal_sync "borrowed" liberally
- [rcaloras](https://github.com/rcaloras) and everyone who contributed to [bash-preexec](https://github.com/rcaloras/bash-preexec)
  - Finding this tool inspired me to build the first prototype of what later became terminal_sync
