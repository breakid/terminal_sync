# Create an enumerated type to track the log status of each command
Add-Type -TypeDefinition @"
   public enum LogStatus
   {
      Logged,
      Completed
   }
"@

# Dictionary used to track which commands have be logged and successfully updated
$global:commandTracker = @{}

# Initialize the command index so our command count aligns with the Id attribute in PowerShell's history
# Add 1 because the command to load this module (e.g., `Import-Module terminal_sync.psm1`) will increment the history
$global:commandIndex = $(Get-History -Count 1).Id + 1

# Pre-exec hook
function PSConsoleHostReadLine {
    # Prompt the user for a command line to submit, save it in a variable and
    # pass it through, by enclosing it in (...)
    $command = [Microsoft.PowerShell.PSConsoleReadLine]::ReadLine($Host.Runspace, $ExecutionContext)

    $startTime = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd HH:mm:ss")

    try {
        # Only react to non-blank lines
        if ($command.Trim()) {
            # Increment command index so it will match `$(Get-History -Count 1).Id` for this command
            $global:commandIndex += 1

            Write-Host "[*] Executed: `"$command`" at $startTime"

            $Params = @{
                Method      = "Post"
                Uri         = "http://127.0.0.1:8000/commands/"
                ContentType = "application/json"
                Body        = (@{
                        uuid       = "$($Host.InstanceId).$global:commandIndex"
                        command    = $command
                        start_time = $startTime
                        comments   = "PowerShell Session: $($Host.InstanceId)"
                    } | ConvertTo-Json
                )
                TimeoutSec  = 10
            }

            $response = Invoke-RestMethod @Params

            # The log entry will be returned if the command triggered logging; otherwise, the response will be "null"
            if ($response -ne "null") {
                # If the entry has a `gw_id` attribute, it logged successfully
                if ($response.gw_id) {
                    Write-Host "[+] Logged to GhostWriter with ID: $($response.gw_id)"

                    # Store the status of the command
                    $global:commandTracker.Set_Item($global:commandIndex.ToString(), [LogStatus]::Logged)
                }
                else {
                    # If the gw_id is $null, an error occurred
                    throw "Failed to log command to GhostWriter"
                }
            }
        }
    }
    catch {
        # Clearly indicate the error is from terminal_sync and not the command the user ran
        Write-Host -ForegroundColor Red "[terminal_sync] [ERROR]: $_"
    }

    # IMPORTANT: Ensure the original command is returned so it gets executed
    $command
}

# Post-exec hook
function Prompt {
    try {
        # Retrieve the last command
        $lastCommand = Get-History -Count 1

        # If the last command exists and isn't complete, process it
        if ($lastCommand -and $global:commandTracker[$lastCommand.Id.ToString()] -ne [LogStatus]::Completed) {
            # Convert the start and end timestamps to properly formatted strings (in UTC)
            $startTime = $lastCommand.StartExecutionTime.ToUniversalTime().ToString("yyyy-MM-dd HH:mm:ss")
            $endTime = $lastCommand.EndExecutionTime.ToUniversalTime().ToString("yyyy-MM-dd HH:mm:ss")

            $Params = @{
                Method      = "Put"
                Uri         = "http://127.0.0.1:8000/commands/"
                ContentType = "application/json"
                Body        = (@{
                        # Use the PowerShell session ID and the index of the command to uniquely identify it
                        uuid       = "$($Host.InstanceId).$($lastCommand.Id)"
                        command    = $lastCommand.CommandLine
                        start_time = $startTime
                        end_time   = $endTime
                        # Set output to the execution status of the command
                        output     = if ($?) { "Success" } else { "Failed" }
                        comments   = "PowerShell Session: $($Host.InstanceId)"
                    } | ConvertTo-Json
                )
                TimeoutSec  = 10
            }

            $response = Invoke-RestMethod @Params

            # The log entry will be returned if the command triggered logging; otherwise, the response will be "null"
            if ($response -ne "null") {
                # If the entry has a `gw_id` attribute, it logged successfully
                if ($response.gw_id) {
                    Write-Host "[+] Updated GhostWriter log: $($response.gw_id)"

                    # Mark the command as completed so we don't get a duplicate if the user presses Enter on an empty line
                    $global:commandTracker.Set_Item($lastCommand.Id.ToString(), [LogStatus]::Completed)
                }
                else {
                    # If the gw_id is $null, an error occurred
                    throw "Failed to log command to GhostWriter"
                }
            }
        }
    }
    catch {
        # Clearly indicate the error is from terminal_sync and not the command the user ran
        Write-Host -ForegroundColor Red "[terminal_sync] [ERROR]: $_"
    }

    # Return the PowerShell prompt
    "PS $($executionContext.SessionState.Path.CurrentLocation.Path)$('>' * ($nestedPromptLevel + 1)) "
}