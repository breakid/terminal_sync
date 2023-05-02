# =============================================================================
# ******                     Configuration Settings                      ******
# =============================================================================

# The name / identifier of the user creating the log entries
$env:OPERATOR = ""

# The IP and port where the terminal_sync server is running
$global:TermSyncServer = "127.0.0.1:8000"

# Enable / disable terminal_sync logging at runtime
$global:TermSyncLogging = $true

# Controls the verbosity of the terminal_sync console output
#   0 (None): No terminal_sync output will be displayed
#   1 (ExecOnly): Only the executed command and timestamps will be displayed
#   2 (SuccessOnly): terminal_sync will display a message on logging success
#   3 (IgnoreTermSyncConnError): Only errors contacting the terminal_sync server will be suppressed
#   4 (All): All terminal_sync output will be displayed
$global:TermSyncVerbosity = 4

# The number of seconds the client will wait for a response from the terminal_sync server
$global:TimeoutSec = 4


# =============================================================================
# ******                      Management Functions                       ******
# =============================================================================

function Enable-TermSync {
    $global:TermSyncLogging = $true
    Write-Host "[+] terminal_sync logging enabled"
}

function Disable-TermSync {
    $global:TermSyncLogging = $False
    Write-Host "[+] terminal_sync logging disabled"
}

function Set-TermSyncVerbosity {
    # Use the DisplayLevel enum as the parameter type to allow tab completion
    param(
        [Parameter(Mandatory)]
        [ValidateNotNullOrEmpty()]
        [DisplayLevel]$Level
    )
    $global:TermSyncVerbosity = $Level

    Write-Host "[+] terminal_sync log level set to: $Level"
}

# =============================================================================
# ******                      Terminal Sync Client                       ******
# =============================================================================

# Define the console verbosity levels
Add-Type -TypeDefinition @"
    public enum DisplayLevel
    {
        None = 0,
        ExecOnly = 1,
        SuccessOnly = 2,
        IgnoreTermSyncConnError = 3,
        All = 4
    }
"@

# Enumerated type to track the log status of each command
Add-Type -TypeDefinition @"
    public enum LogStatus
    {
        Logged,
        Completed
    }
"@

# Dictionary used to track which commands have be logged and successfully updated
$global:CommandTracker = @{}

# Initialize the command index so our command count aligns with the Id attribute in PowerShell's history
# Add 1 because the command to load this module (e.g., `Import-Module terminal_sync.psm1`) will increment the history
$global:CommandIndex = $(Get-History -Count 1).Id + 1

# Pre-exec hook
function PSConsoleHostReadLine {
    # Prompt the user for a command line to submit, save it in a variable and
    # pass it through, by enclosing it in (...)
    $Command = [Microsoft.PowerShell.PSConsoleReadLine]::ReadLine($Host.Runspace, $ExecutionContext)

    if ($TermSyncLogging) {
        $StartTime = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd HH:mm:ss")

        try {
            # Only react to non-blank lines
            if ($command.Trim()) {
                # Increment command index so it will match `$(Get-History -Count 1).Id` for this command
                $global:CommandIndex += 1

                if ($TermSyncVerbosity -gt [DisplayLevel]::None) {
                    Write-Host "[*] Executed: `"$Command`" at $StartTime"
                }

                $Params = @{
                    Method      = "Post"
                    Uri         = "http://$TermSyncServer/commands/"
                    ContentType = "application/json"
                    TimeoutSec  = $TimeoutSec
                    Body        = (@{
                            uuid        = "$($Host.InstanceId).$global:CommandIndex"
                            command     = $Command
                            start_time  = $StartTime
                            source_host = $env:SRC_HOST
                            comments    = "PowerShell Session: $($Host.InstanceId)"
                            operator    = $env:OPERATOR
                        } | ConvertTo-Json
                    )
                }

                try {
                    $Response = Invoke-RestMethod @Params

                    # If the request is successful, the response will be a string to be displayed to the user
                    # If the command does not trigger logging, an HTTP 204 with no body is returned; don't print anything
                    if ($Response) {
                        if ($TermSyncVerbosity -gt [DisplayLevel]::ExecOnly) {
                            Write-Host $Response
                        }

                        # Store the status of the command
                        $global:CommandTracker.Set_Item($global:CommandIndex.ToString(), [LogStatus]::Logged)
                    }
                }
                catch {
                    # Get the HTTP status code
                    $StatusCode = $_.Exception.Response.StatusCode.value__

                    # An error occurred; the server will return a JSON object with a "detail" attribute
                    # (e.g., '{"detail":"An error occurred while trying to log to GhostWriter: Cannot connect to host"}')
                    if ($StatusCode) {
                        # If an exception occurred server-side; throw an exception with the message from the server
                        throw $($_ | ConvertFrom-Json).detail
                    }
                    elseif ($_.ToString() -eq "Unable to connect to the remote server") {
                        if ($TermSyncVerbosity -gt [DisplayLevel]::IgnoreTermSyncConnError) {
                            # Clarify which server could not be contacted
                            throw "Unable to connect to terminal_sync server"
                        }
                    }
                    else {
                        # Otherwise, re-raise the exception
                        throw $_
                    }
                }
            }
        }
        catch {
            if ($TermSyncVerbosity -gt [DisplayLevel]::SuccessOnly) {
                # Clearly indicate the error is from terminal_sync and not the command the user ran
                Write-Host -ForegroundColor Red "[terminal_sync] [ERROR]: $_"
            }
        }
    }

    # IMPORTANT: Ensure the original command is returned so it gets executed
    $command
}

# Post-exec hook
function Prompt {
    if ($TermSyncLogging) {
        try {
            # Retrieve the last command
            $LastCommand = Get-History -Count 1

            # If the last command exists and isn't complete, process it
            if ($LastCommand -and $global:CommandTracker[$LastCommand.Id.ToString()] -ne [LogStatus]::Completed) {

                # Convert the start and end timestamps to properly formatted strings (in UTC)
                $StartTime = $LastCommand.StartExecutionTime.ToUniversalTime().ToString("yyyy-MM-dd HH:mm:ss")
                $EndTime = $LastCommand.EndExecutionTime.ToUniversalTime().ToString("yyyy-MM-dd HH:mm:ss")

                if ($TermSyncVerbosity -gt [DisplayLevel]::None) {
                    Write-Host "[+] Completed: `"$($LastCommand.CommandLine)`" at $EndTime"
                }

                $Params = @{
                    Method      = "Put"
                    Uri         = "http://$TermSyncServer/commands/"
                    ContentType = "application/json"
                    TimeoutSec  = $TimeoutSec
                    Body        = (@{
                            # Use the PowerShell session ID and the index of the command to uniquely identify it
                            uuid        = "$($Host.InstanceId).$($LastCommand.Id)"
                            command     = $LastCommand.CommandLine
                            start_time  = $StartTime
                            end_time    = $EndTime
                            source_host = $env:SRC_HOST
                            # Set output to the execution status of the command
                            output      = if ($?) { "Success" } else { "Failed" }
                            comments    = "PowerShell Session: $($Host.InstanceId)"
                            operator    = $env:OPERATOR
                        } | ConvertTo-Json
                    )
                }

                try {
                    $Response = Invoke-RestMethod @Params

                    # If the request is successful, the response will be a string to be displayed to the user
                    # If the command does not trigger logging, an HTTP 204 with no body is returned; don't print anything
                    if ($Response) {
                        if ($TermSyncVerbosity -gt [DisplayLevel]::ExecOnly) {
                            Write-Host $Response
                        }

                        # Mark the command as completed so we don't get a duplicate if the user presses Enter on an empty line
                        $global:CommandTracker.Set_Item($LastCommand.Id.ToString(), [LogStatus]::Completed)
                    }
                }
                catch {
                    # Get the HTTP status code
                    $StatusCode = $_.Exception.Response.StatusCode.value__

                    # An error occurred; the server will return a JSON object with a "detail" attribute
                    # (e.g., '{"detail":"An error occurred while trying to log to GhostWriter: Cannot connect to host"}')
                    if ($StatusCode) {
                        # If an exception occurred server-side; throw an exception with the message from the server
                        throw $($_ | ConvertFrom-Json).detail
                    }
                    elseif ($_.ToString() -eq "Unable to connect to the remote server") {
                        if ($TermSyncVerbosity -gt [DisplayLevel]::IgnoreTermSyncConnError) {
                            # Clarify which server could not be contacted
                            throw "Unable to connect to terminal_sync server"
                        }
                    }
                    else {
                        # Otherwise, re-raise the exception
                        throw $_
                    }
                }
            }
        }
        catch {
            if ($TermSyncVerbosity -gt [DisplayLevel]::SuccessOnly) {
                # Clearly indicate the error is from terminal_sync and not the command the user ran
                Write-Host -ForegroundColor Red "[terminal_sync] [ERROR]: $_"
            }
        }
    }

    # Return the PowerShell prompt
    "PS $($executionContext.SessionState.Path.CurrentLocation.Path)$('>' * ($nestedPromptLevel + 1)) "
}
