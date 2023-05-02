# Usage

The entire point of terminal_sync is to log shell commands automatically. Therefore, once the [server is setup and the hooks are registered](setup.md), no further action is necessary. That said, the following are a few runtime options that can enhance the user experience.

---

## Specify the Source Host

Set the environment variable `SRC_HOST` to the host where your activity will originate. This value will appear in the Source field on GhostWriter and is particularly useful when operating over a SOCKS proxy or tunnel. If the client (i.e., hook) environment is different than the terminal_sync server environment (e.g., if using Docker), the client-side value will override the server-side value.

If this value is not provided, terminal_sync will default to the hostname and IP of the host where the server is running. If using Docker, this will be the container.

## Add a Description

terminal_sync allows users to (optionally) specify a description at the end of each command. Anything that appears after the string specified by the `gw_description_token` setting will be extracted and used as the Description attribute of the log entry.

**Note**: This token must begin with a `#` so that Bash and PowerShell interpret it, and everything that follows, as a comment and don't attempt to execute the description text.

## Log Ad-hoc Commands

Since the `gw_description_token` inherently triggers logging, users can append this string to any command, with or without additional text, to force an individual command to be logged.

## Enable / Disable terminal_sync

Run `Disable-TermSync` to temporarily disable terminal_sync once hooks are registered for that session. To re-enable it, run `Enable-TermSync`. These commands set a flag that is checked when each hook is run, skipping the hook logic if disabled, and consequently only affect the current session.

To permanently disable terminal_sync, delete or comment out the line in `~/.bashrc` or your PowerShell `$PROFILE` that loads the hooks.

## Adjust Console Output at Runtime

Both the Bash script and PowerShell module contain a configuration setting that allows users to set the default console output; however, this can be changed (temporarily) for a session, using the `Set-TermSyncVersbosity` command.

In Bash, simply run `Set-TermSyncVersbosity`; this will print a list of display settings and prompt you for a number. Enter the number that matches your preferred setting.

In PowerShell, type `Set-TermSyncVerbosity`, followed by a space, then press **Tab** to cycle through the available options. Press **Enter** to select your preferred setting.

## Export Logs to GhostWriter CSV

Any log entries that cannot be sent to GhostWriter successfully, such as due to a configuration or connectivity issue, will be saved (local to the server) in JSON format. The configuration setting `termsync_save_all_local` can be used to override this behavior and save all entries, even those logged to GhostWriter successfully. If the GhostWrite URL or API keys are not provided, this setting is automatically enabled to prevent accidental loss of logs.

On shutdown, the terminal_sync server will attempt to export these saved logs to a timestamped CSV file that can be imported to GhostWriter. The `export_csv.py` script can also be run manually to generate a CSV file without stopping the server.

```bash
# Usage:
# export_csv.py [-h] -l LOG_DIR [-o OUTPUT_DIR]

# Example:
python src/terminal_sync/export_csv.py -l log_archive
```
