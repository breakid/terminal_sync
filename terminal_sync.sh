# =============================================================================
# ******                     Configuration Settings                      ******
# =============================================================================

# The name / identifier of the user creating the log entries
export OPERATOR=""

# The IP and port where the terminal_sync server is running
TERMSYNC_SERVER="127.0.0.1:8000"

# Whether terminal_sync logging is enabled; any value greater than 0 means enabled
TERMSYNC_LOGGING=1

# Controls the verbosity of the terminal_sync console output
#   0 (None): No terminal_sync output will be displayed
#   1 (ExecOnly): Only the executed command and timestamps will be displayed
#   2 (SuccessOnly): terminal_sync will display a message on logging success
#   3 (IgnoreTermSyncConnError): Only errors contacting the terminal_sync server will be suppressed
#   4 (All): All terminal_sync output will be displayed
#   5 (Debug): Additional debugging information will be displayed
TERMSYNC_VERBOSITY=4

# The number of seconds the client will wait for a response from the terminal_sync server
TERMSYNC_TIMEOUT=4


# =============================================================================
# ******                     Installation and Setup                      ******
# =============================================================================

# NOTE: These installation steps are run automatically every time the script is invoked to make sure the necessary
# dependencies are in place and haven't been removed since the last execution

BASH_PREEXEC_PATH=~/bash-preexec.sh

# If bash-preexec.sh does not exist, warn the user about running scripts from the Internet,
# if they accept the risk, download it
if [[ ! -f $BASH_PREEXEC_PATH ]]; then
    echo -e "\e[31m[!] Security Warning\e[0m: This script will download and run bash-preexec.sh (https://raw.githubusercontent.com/rcaloras/bash-preexec/master/bash-preexec.sh). Downloading and running scripts from the Internet can be dangerous; you are advised to review the contents of this script before continuing."

    read -p "[?] I accept the risk [y|N]: " -N 1
    echo '' # Start a new line after the previous 'read' command

    # Bail unless the user specifically agrees
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "\e[31m[X] Operation cancelled\e[0m"
        # IMPORTANT: Use 'return' rather than 'exit' because this script will be invoked via 'source' and
        # 'exit' would kill the shell
        return 1
    fi

    echo -e "\e[1;34m[*] Downloading bash-preexec.sh...\e[0m"

    # Download bash-preexec.sh
    # This is used to hook commands before they execute
    curl https://raw.githubusercontent.com/rcaloras/bash-preexec/master/bash-preexec.sh > $BASH_PREEXEC_PATH

    if [[ ! -f $BASH_PREEXEC_PATH ]]; then
        echo -e "\e[31m[-] Error: Failed to download bash-preexec.sh\e[0m"
        return 1
    fi

    # Ensure bash-preexec.sh is executable
    chmod +x $BASH_PREEXEC_PATH

    echo -e "\e[1;32m[+] Successfully downloaded bash-preexec.sh\e[0m"

    # If bash-preexec doesn't exist, assume this is the first run, prompt the user whether they want to install terminal_sync
    echo "[*] This looks like your first time running terminal_sync on this host."
    read -p "[?] Would you like to permanently install the bash hooks? [Y|n]: " -N 1
    echo '' # Start a new line after the previous 'read' command

    # Default to installing unless the user says no
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        echo "source '$(realpath $PWD/$BASH_SOURCE)'" >> ~/.bashrc
        echo -e "\e[1;32m[+] Successfully added terminal_sync.sh to ~/.bashrc\e[0m"
    fi
fi

# Install required packages (only if one doesn't exist, so we don't do this every time terminal_sync runs)
# Source: https://unix.stackexchange.com/questions/46081/identifying-the-system-package-manager
packages_needed='curl jq'

for package in $packages_needed; do
    if [[ ! -x $(command -v $package) ]]; then
        echo -e "\e[1;34m[*] ${package} not installed; attempting to install...\e[0m"

        if [ -x "$(command -v apk)" ];       then sudo apk add -y --no-cache $packages_needed
        elif [ -x "$(command -v apt-get)" ]; then sudo apt-get install -y $packages_needed
        elif [ -x "$(command -v dnf)" ];     then sudo dnf install -y $packages_needed
        elif [ -x "$(command -v zypper)" ];  then sudo zypper install -y $packages_needed
        else
            echo -e "\e[31m[-] Error: Package manager not found. You must manually install: ${packages_needed}\e[0m" >&2
            return 1
        fi
    fi
done


# =============================================================================
# ******                      Management Functions                       ******
# =============================================================================

DISPLAY_LEVELS=(NONE EXEC_ONLY SUCCESS_ONLY IGNORE_TERMSYNC_CONN_ERROR ALL DEBUG)

num_display_levels=${#DISPLAY_LEVELS[@]}

# Declare variables for each display level so they can be referenced in the code
for ((i=0; i < $num_display_levels; i++)); do
    name="DISPLAY_${DISPLAY_LEVELS[i]}"
    declare ${name}=$i
done

function Enable-TermSync {
    TERMSYNC_LOGGING=1
    echo "[+] terminal_sync logging enabled"
}

function Disable-TermSync {
    TERMSYNC_LOGGING=0
    echo "[+] terminal_sync logging disabled"
}

function Set-TermSyncVersbosity() {
    echo "Display Levels:"
    echo "---------------"

    for ((i=0; i < $num_display_levels; i++)); do
        echo "${i} = ${DISPLAY_LEVELS[i]}"
    done

    # Add an extra new line for visual separation
    echo ""
    echo "[*] Current log level: ${DISPLAY_LEVELS[TERMSYNC_VERBOSITY]}"

    while [ 1 ]; do
        read -p "[?] Enter the number of your desired display level: " -N 1

        # Verify the input is within the valid range
        if [[ $REPLY -ge 0 && $REPLY -lt $num_display_levels ]]; then
            TERMSYNC_VERBOSITY=$REPLY
            break
        fi

        echo "[-] '${REPLY}' is not a valid log level"
    done

    echo "" # Print a newline, since read only accepts a single character
    echo "[+] terminal_sync log level set to: ${DISPLAY_LEVELS[TERMSYNC_VERBOSITY]}"
}


# =============================================================================
# ******                      Terminal Sync Client                       ******
# =============================================================================

# Load bash-preexec to enable `preexec` and `precmd` hooks
source $BASH_PREEXEC_PATH

# Set the history time format to timestamp each command run (format: 'YYYY-mm-dd HH:MM:SS')
# This is useful as a fallback and is expected by the `sed` command that parses the command line from the history
export HISTTIMEFORMAT="%F %T "

# Set the comment to: "<shell_binary> session: <session_id>"
COMMENT="$(ps -p $$ -o comm | tail -n 1) session: $(cat /proc/sys/kernel/random/uuid)"


function display_response() {
    response=$*

    # If an error occured the server will return a JSON object with a "detail" attribute
    # (e.g., '{"detail":"An error occurred while trying to log to GhostWriter: Cannot connect to host"}')
    # Use `jq` to parse it and display the error message; otherwise print the message from the server
    if [[ $response == *"{\"detail\":"* ]]; then
        if [[ $TERMSYNC_VERBOSITY -gt $DISPLAY_SUCCESS_ONLY ]]; then
            error_msg="$(echo $response | jq -r '.detail')"
            echo -e "\e[31m[terminal_sync] [ERROR]: ${error_msg}\e[0m"
        fi
    elif [[ $TERMSYNC_VERBOSITY -gt $DISPLAY_EXEC_ONLY && ${#response} -gt 0 ]]; then
        # Print the response, stripping leading and trailing quotes
        echo $response | sed -e 's/^"//' -e 's/"$//'
    fi
}

function create_log() {
    command=$1

    if [[ $TERMSYNC_VERBOSITY -gt $DISPLAY_NONE ]]; then
        echo "[*] Executed: \"${command}\" at ${CMD_START_TIME}"
    fi

    json_data="$(jq --null-input \
        --arg uuid "${CMD_UUID}" \
        --arg command "${command}" \
        --arg start_time "${CMD_START_TIME}" \
        --arg source_host "${SRC_HOST}" \
        --arg comments "${COMMENT}" \
        --arg operator "${OPERATOR}" \
        '{"uuid": $uuid, "command": $command, "start_time": $start_time,
        "source_host": $source_host, "comments": $comments, "operator": $operator}'\
    )"

    if [[ $TERMSYNC_VERBOSITY -gt $DISPLAY_ALL ]]; then
        echo $json_data | jq
    fi

    # Set whether curl should display connection error messages
    [[ $TERMSYNC_VERBOSITY -gt $DISPLAY_IGNORE_TERMSYNC_CONN_ERROR ]] && show_error='-S' || show_error=''

    response=$(curl -s ${show_error} -X 'POST' "http://${TERMSYNC_SERVER}/commands/" -H 'accept: application/json' \
        -H 'Content-Type: application/json' --connect-timeout ${TERMSYNC_TIMEOUT} -d "${json_data}")

    if [[ $TERMSYNC_VERBOSITY -gt $DISPLAY_EXEC_ONLY ]]; then
        display_response $response
    fi
}

function update_log() {
    command=$1
    error_code=$2

    end_time=$(date -u +'%F %H:%M:%S')

    if [[ $TERMSYNC_VERBOSITY -gt $DISPLAY_NONE ]]; then
        echo -e "\n[+] Completed: \"${command}\" at ${end_time}"
    fi

    # Determine whether the command succeeded; if the command failed return the error code as well
    [[ $error_code -eq 0 ]] && output='Success' || output="Failed; Return Code: ${error_code}"

    json_data="$(jq --null-input \
        --arg uuid "${CMD_UUID}" \
        --arg command "${command}" \
        --arg start_time "${CMD_START_TIME}" \
        --arg end_time "${end_time}" \
        --arg source_host "${SRC_HOST}" \
        --arg output "${output}" \
        --arg comments "${COMMENT}" \
        --arg operator "${OPERATOR}" \
        '{"uuid": $uuid, "command": $command, "start_time": $start_time, "end_time": $end_time,
        "source_host": $source_host, "output": $output, "comments": $comments, "operator": $operator}'\
    )"

    if [[ $TERMSYNC_VERBOSITY -gt $DISPLAY_ALL ]]; then
        echo $json_data | jq
    fi

    # Set whether curl should display connection error messages
    [[ $TERMSYNC_VERBOSITY -gt $DISPLAY_IGNORE_TERMSYNC_CONN_ERROR ]] && show_error='-S' || show_error=''

    response=$(curl -s ${show_error} -X 'PUT' "http://${TERMSYNC_SERVER}/commands/" -H 'accept: application/json' \
        -H 'Content-Type: application/json' --connect-timeout ${TERMSYNC_TIMEOUT} -d "${json_data}")

    if [[ $TERMSYNC_VERBOSITY -gt $DISPLAY_EXEC_ONLY ]]; then
        display_response $response
    fi
}

# Defines a pre-execution hook to log the command to GhostWriter
function preexec() {
    command="$*"

    if [[ $TERMSYNC_VERBOSITY -gt $DISPLAY_ALL ]]; then
        echo "Command: $command"
    fi

    # If terminal_sync is enabled and the command isn't empty (i.e., length of `command` > 0), try to log the command
    if [[ $TERMSYNC_LOGGING -gt 0 && ${#command} -gt 0 ]]; then
        # Generate a UUID for the command; save it and the start time as environment variables so they can be accessed
        # by the post-exec hook
        CMD_UUID="$(cat /proc/sys/kernel/random/uuid)"
        CMD_START_TIME="$(date -u +'%F %H:%M:%S')"

        create_log "${command}"
    fi
}

# Defines a post-execution hook that updates the command entry in GhostWriter
function precmd() {
    # IMPORTANT: This must be the first command or else we'll get the status of a command we run
    error_code="$?"

    if [[ $TERMSYNC_VERBOSITY -gt $DISPLAY_ALL ]]; then
        echo "Command UUID: $CMD_UUID"
        echo "Command Start Time: $CMD_UUID"
        echo "Error Code: $error_code"
    fi

    # If logging is enabled and CMD_UUID was set by the pre-exec hook, try to update the entry
    # The CMD_UUID check prevents duplicate submissions when the user submits a blank line
    if [[ $TERMSYNC_LOGGING -gt 0 && ${#CMD_UUID} -gt 0 ]]; then
        # Get the last command and strip the index and timestamp from the front
        last_command=$(export LC_ALL=C; builtin history 1 | sed '1 s/^[^:]*[^ ]* *//');
        # last_command="$(export LC_ALL=C; builtin history 1)"
        # start_time="$(echo $last_command | awk '{print $2,$3}')"

        update_log "${last_command}" "${error_code}"

        # Unset variables to prevent logging unless another command is run (i.e., ignore blank lines)
        unset CMD_UUID
        unset CMD_UUID
    fi
}


echo -e "\e[1;32m[+] Successfully loaded terminal_sync hooks\e[0m"
