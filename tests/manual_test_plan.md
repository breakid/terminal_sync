# terminal_sync Test Plan

The following is a list of features to test manually prior to release.

## Linux

- `terminal_sync.sh`
  - [ ] Automatically downloads `bash-preexec.sh` if it doesn't exist
  - [ ] Warns and obtains confirmation from the user before downloading `bash-preexec.sh`
  - [ ] Prompts the user whether they want to add `terminal_sync.sh` to `~/.bashrc` (if `bash-preexec.sh` did not exist)
  - [ ] Automatically installs Docker and Docker Compose (on Debian-based OSes), if not present and execution method is set to `docker`
  - [ ] Automatically builds the Docker image, if not present and execution method is set to `docker`
  - [ ] Automatically installs `python3` and `pip3`, if not present and execution method is set to `python`
  - [ ] Runs `terminal_sync` prior to command execution, passing in at minimum:
    - [ ] Command
    - [ ] Command UUID
    - [ ] Source Host
    - [ ] Comment
  - [ ] Runs `terminal_sync` after command execution, passing in at minimum:
    - [ ] Command
    - [ ] Command UUID
    - [ ] Source Host
    - [ ] Result (and optionally command output)
    - [ ] Comment
  - [ ] Submitting an empty command (i.e., pressing Enter with no command specified) does not produce duplicate command entries

---

## Windows

- `terminal_sync.psm1`
  - [ ] Runs `terminal_sync` prior to command execution, passing in at minimum:
    - [ ] Command
    - [ ] Command UUID
    - [ ] Comment
  - [ ] Runs `terminal_sync` after command execution, passing in at minimum:
    - [ ] Command
    - [ ] Command UUID
    - [ ] Source Host
    - [ ] Result
    - [ ] Comment
  - [ ] Submitting an empty command (i.e., pressing Enter with no command specified) does not produce duplicate command entries

---

## Python Client

### Configuration

- The following configuration options can be set using environment variables:
  - [ ] GW_API_KEY_GRAPHQL
  - [ ] GW_API_KEY_REST
  - [ ] GW_DEST_HOST
  - [ ] GW_OPLOG_ID
  - [ ] GW_SRC_HOST
  - [ ] GW_SSL_CHECK
  - [ ] GW_TIMEOUT_SECONDS
  - [ ] GW_URL
  - [ ] OPERATOR
  - [ ] TERMSYNC_CACHE_DIR
  - [ ] TERMSYNC_DESC_TOKEN
  - [ ] TERMSYNC_ENABLED
  - [ ] TERMSYNC_LOG_DIR
  - [ ] TERMSYNC_NOLOG_TOKEN
  - [ ] TERMSYNC_SAVE_ALL_LOCAL
- Allows the user to specify the following using command-line arguments:
  - [ ] Command
  - [ ] Command UUID
  - [ ] Start Time
  - [ ] End Time
  - [ ] Source Host
  - [ ] Destination Host
  - [ ] Operator
  - [ ] Comment
  - [ ] Output
  - [ ] Ghostwriter Log Entry ID

### Log Entry Validation

- [ ] Whitespace is stripped from the beginning and end of the command text
- [ ] Whitespace is stripped from the beginning and end of the descripton
- [ ] The end time always comes after the start time

### Plugin Framework

- [ ] The log entry object is passed to each plugin
- [ ] A plugin can modify the log entry
- [ ] Multiple plugins can modify the same log entry (in series)

### Application Logic

- [ ] Commands containing the configured `termsync_nolog_token` are not logged
- [ ] Anything following the configured `termsync_desc_token` is stored in the description field
- [ ] An existing Ghostwriter entry can be updated by specifying the Ghostwriter log entry ID
  - [ ] Only fields specified in the update command are modified
- Log entry data is stored as a JSON file when:
  - [ ] Ghostwriter does not successfully log the message
  - [ ] The `termsync_save_all_local` setting is enabled
  - [ ] A command has been executed but not yet completed
- [ ] Locally cached log entry JSON files are removed when a completed command successfully logs to Ghostwriter and the `termsync_save_all_local` setting is disabled
- Console messages inform the user when:
  - [ ] A configuration setting has the wrong data type (e.g., string instead of int)
  - [ ] Local logging (to JSON files) is automatically enabled due to invalid Ghostwriter configuration
  - [ ] A command is executed
  - [ ] A command finishes executing
  - [ ] A command has been successfully logged to Ghostwriter
  - [ ] A command has been successfully updated on Ghostwriter
  - [ ] An error occurs while communicating with Ghostwriter
  - [ ] A command is logged to a JSON file because of an error communicating with Ghostwriter
  - [ ] A command is logged to a JSON file because the `termsync_save_all_local` setting is enabled

### Ghostwriter Client

- [ ] A log entry is sent to Ghostwriter if the Ghostwriter URL and either a GraphQL token, a REST token, or both are supplied
  - [ ] GraphQL is used when both a GraphQL and REST token are provided
- [ ] Log entries can be submitted via GraphQL
- [ ] Log entries can be submitted via REST
