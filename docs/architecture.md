# terminal_sync Architecture

This page provides additional details about how terminal_sync works and is intended for those who are:

1. Interested in contributing to the project
2. Passionately curious

---

## Design Evolution

terminal_sync began life as a prototype intended specifically for capturing command-line tools, such as Impacket scripts, run with `proxychains`. The original version was a Python script called directly from the Bash pre-exec hook. Unfortunately, this had several limitations.

1. It only supported commands run via proxychains
2. It only supported Bash
3. The lack of a post-exec hook meant it couldn't capture when a command completed or its success/failure status
4. There was no way to provide a description

The second iteration set out to address these issues. The first challenge was how to save state so that the completion time and output of a command could be matched to the original execution, thus allowing the initial log entry to be updated rather than creating a near duplicate entry. There was also a concern that, as the application configuration became more complex, the overhead of loading the config each time the script was run (i.e., before and after each execution) would negatively impact performance and the overall user experience.

This second iteration used a client-server model where the server, which contained the majority of the processing logic, would load the configuration once and stay running. The client would remain lightweight and naive, containing only enough logic to capture raw data and send it to the server. Additionally, the clients would be written using native capabilities (i.e., Bash and PowerShell) to minimize dependencies, both for security and ease of installation.

---

## How terminal_sync Works

The current version of terminal_sync uses a client-server model.

### Server

The terminal_sync server is a Python package consisting of four main components:

1. Config class
    - Defined in `config.py`
2. GhostWriterClient class
    - Defined in `ghostwriter.py`
3. FastAPI server
    - Defined in `api.py`
4. Entry class
    - Defined in `log_entry.py`

The server must be installed or run as a module since it uses absolute imports to reference internal modules. This was done to prevent `isort` from grouping the internal modules into the third-party libraries import section.

#### Config

The `Config` class defines default settings, loads the YAML config file (if it exists), and checks for any environment variables that match defined settings. If the optional `python-dotenv` package is installed, environment variables will be loaded from a `.env` file before loading the YAML config. This is done because the path to the config file can be specified using the `TERMSYNC_CONFIG` variable. If `TERMSYNC_CONFIG` was included in the `.env` file but the environment variables were loaded later, the wrong config file would be loaded, which would likely confuse users. All other environment variables are evaluated after, and therefore override values from, the YAML config file. Finally, some additional validation is performed and the config object is returned.

#### GhostWriter Client

The GhostWriter client is largely a consolidation of the REST-based [mythic-sync](https://github.com/hotnops/mythic-sync) and GraphQL-based [mythic_sync](https://github.com/GhostManager/mythic_sync) projects with some logic to determine which flow to use based on which API key was provided. Additionally, the exception handling was moved to the API server to allow it to send error messages back to the client.

#### API Server

The API server uses FastAPI to create two REST endpoints, `POST /commands/` and `PUT /commands/`, intended to create and update command log entries, respectively. In practice, the update endpoint will also create an entry if a matching one is not found in the internal buffer; this is to increase the likelihood of a command being logged successfully, even if the initial creation attempt failed. Since both endpoints contain nearly identical logic, the majority of the work is done in the shared `log_command()` function. This function checks whether the input command contains any keywords that would trigger logging. If so, the description is split from the command (if applicable), an `Entry` object is either created or retrieved from the internal buffer and updated, then the `Entry` object is sent to the GhostWriter client, which sends it to GhostWriter. If the submission fails, or if the config specifies all logs should be saved, the `Entry` is passed to the `save_log()` function which saves it as a JSON object.

#### Entry

The `Entry` class is mostly responsible for encapsulating data as it's passed around the application but contains some logic to normalize and return it in different formats for the distinct REST and GraphQL APIs.

### Clients

The current clients, written using Bash and PowerShell, are integrated into their respective hook code and implement similar logic. They define client-side configuration settings at the top, include functions to enable/disable hooking and control verbosity, and define the hook functions themselves. The hook functions capture the raw data such as the executed command and timestamps, as well as operator and source host if the environment variables are set. This data is then packaged as a JSON object and sent to the server. The response is received and optionally printed, depending on the verbosity settings.

The Bash client uses [bash-preexec](https://github.com/rcaloras/bash-preexec) to create the `preexec` and `precmd` (i.e., post-exec) hook points and uses `jq` to construct and parse the JSON objects exchanged with the server.

The PowerShell client overrides the `PSConsoleHostReadLine` and `Prompt` functions to create pre-exec and post-exec hooks.

---

### Execution Flow

The terminal_sync server is started by executing `python -m terminal_sync` either directly or by running `pdm serve`. This runs the `__main__.py` module, which parses any host and port arguments and calls the `run()` function in `api.py`. When `api.py` is loaded, it instantiates a `Config` object, a `GhostWriterClient` object, and an instance of FastAPI. The `run()` method starts uvicorn to host the FastAPI instance.

When a user runs a command, the client hook code intercepts it, packages the command with additional metadata (including a UUID), and sends it to the creation endpoint on the terminal_sync server. The `pre_exec()` function calls `log_command()`, which checks whether the command contains any of the configured keywords. If so, a new `Entry` object is created, added to an internal buffer, and sent to the `create_log()` method of the GhostWriter client. The GhostWriter client then uses either `_create_entry_graphql()` or `_create_entry_rest()`, depending on which API key was specified, to send the command data to GhostWriter. If succcessful, GhostWriter returns a JSON object containing the ID of the GhostWriter log entry. The GhostWriter client passes this ID back to `log_command()` where it is added to the `Entry` object. The `Entry` object and a success message are returned to the `pre_exec()` function, triggering the `finally` clause in `log_command()`. If the connection to GhostWriter had failed or if the application is configured to save all logs, `log_command()` will call `save_log()` to write the `Entry` data to a JSON file. Back in `pre_exec()`, the message is returned to the terminal_sync client. The terminal_sync client optionally displays the message, depending on the verbosity settings, and returns, allowing the command to execute.

When the command completes, the client hook code intercepts execution again, records the exit status of the command, retrieves additional information about the command from the shell history, packages it all up, and sends it to the update endpoint on the terminal_sync server. The `post_exec()` function calls `log_command()`, which uses the UUID string sent with the command to retrieve the previously created `Entry` object from the internal buffer. The `Entry` is updated and sent to the GhostWriter client's `update_log()` method, which maps to either `_update_entry_graphql()` or `_update_entry_rest()`. The remainder of the flow is essentially identical to the creation flow, except, when execution returns to `post_exec()`, the `Entry` is removed from the internal buffer, since it has been processed.
