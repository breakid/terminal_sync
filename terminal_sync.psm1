# =============================================================================
# ******                     Configuration Settings                      ******
# =============================================================================

# Enable / disable terminal_sync logging at runtime
$global:TermSyncLogging = $true

$TermSyncExecMethod = "docker"

# =============================================================================
# ******                      Management Functions                       ******
# =============================================================================

function Enable-TermSync {
    $global:TermSyncLogging = $true
    Write-Host "[+] terminal_sync logging enabled"
}

function Disable-TermSync {
    $global:TermSyncLogging = $false
    Write-Host "[+] terminal_sync logging disabled"
}


# =============================================================================
# ******                         Terminal Sync                           ******
# =============================================================================

if ($TermSyncExecMethod -ne "docker" -and $TermSyncExecMethod -ne "python") {
    Write-Host "[-] Invalid execution type; please specify 'docker' or 'python'"
}

# Enumerated type to track the log status of each command
Add-Type -TypeDefinition @"
    public enum LogStatus
    {
        Logged,
        Completed
    }
"@

# Set the install directory as the parent directory of this script
$TermSyncInstallDir = Split-Path $MyInvocation.MyCommand.Path -Parent

# Initialize the command index so our command count aligns with the Id attribute in PowerShell's history
# Add 1 because the command to load this module (e.g., `Import-Module terminal_sync.psm1`) will increment the history
$global:CommandIndex = $(Get-History -Count 1).Id + 1

# Dictionary used to track which commands have be logged and successfully updated
$global:CommandTracker = @{}

function Log {
    Param
    (
        [Parameter(Mandatory = $true)]
        [string] $Command,
        [Parameter()]
        [string] $Output,
        [Parameter()]
        [ValidatePattern('^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$')]
        [string] $StartTime,
        [Parameter()]
        [ValidatePattern('^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$')]
        [string] $EndTime
    )

    # Note: PowerShell won't pass empty strings for arguments properly, so we have to construct a command with only populated arguments
    $ArgList = @("terminal_sync", "--uuid", "'$($Host.InstanceId).$global:CommandIndex'", "--comment", "'PowerShell Session: $($Host.InstanceId)'", "'$command'")

    if ($StartTime) {
        $ArgList += ("--start-time", "'$StartTime'")
    }

    if ($EndTime) {
        $ArgList += ("--end-time", "'$EndTime'")
    }

    if ($env:SRC_HOST) {
        $ArgList += ("--src-host", "'$env:SRC_HOST'")
    }

    if ($env:DEST_HOST) {
        $ArgList += ("--dest-host", "'$env:DEST_HOST'")
    }

    if ($Output) {
        $ArgList += ("--output", "'$Output'")
    }

    if ($env:OPERATOR) {
        $ArgList += ("--operator", "'$env:OPERATOR'")
    }

    if ($TermSyncExecMethod -eq "docker") {
        $ArgList = @("compose", "-f", "$TermSyncInstallDir\docker-compose.yaml", "run", "--rm") + $ArgList
    }
    elseif ($TermSyncExecMethod -eq "python") {
        $ArgList = @("-m") + $ArgList
    }

    $TermSyncCommand = "$TermSyncExecMethod $($ArgList -Join ' ')"

    # Execute the command
    Write-Host $TermSyncCommand
    # Pipe to Out-Host to force the script to wait for the command to complete
    Invoke-Expression $TermSyncCommand #| Out-Host

    #& docker compose -f D:\Workspace\terminal_sync\docker-compose.yaml run --rm terminal_sync --uuid "'$($Host.InstanceId).$global:CommandIndex'" --comment "'PowerShell Session: $($Host.InstanceId)'" --start-time "'$StartTime'" --end-time "'$EndTime'" --output "'$Output'" "'$command'" | Out-Host
}


# Pre-exec hook
function PSConsoleHostReadLine {
    # Read the command from the session runtime
    $Command = [Microsoft.PowerShell.PSConsoleReadLine]::ReadLine($Host.Runspace, $ExecutionContext).Trim()

    if ($global:TermSyncLogging) {
        # If command isn't blank and isn't a manual terminal_sync invocation, then process it
        if ($Command -and `
                -not $Command -eq "exit" -and `
                -not $Command.StartsWith("terminal_sync ")) {
            # Increment command index so it will match `$(Get-History -Count 1).Id` for this command
            $global:CommandIndex += 1

            #& py -c "print('test')"
            #docker compose -f D:\Workspace\terminal_sync\docker-compose.yaml run --rm terminal_sync "env"
            Log -Command $Command

            # Store the status of the command
            $global:CommandTracker.Set_Item($global:CommandIndex.ToString(), [LogStatus]::Logged)
        }
    }

    # IMPORTANT: Ensure the original command is returned so it gets executed
    $Command
}

# Post-exec hook
function Prompt {
    if ($global:TermSyncLogging) {
        $Output = if ($?) { "Success" } else { "Failed" }

        # Retrieve the last command
        $LastCommand = Get-History -Count 1
        $Command = $LastCommand.CommandLine

        # If the last command exists, isn't a manual terminal_sync invocation, and isn't complete, then process it
        if ($LastCommand -and `
                -not $Command.StartsWith("terminal_sync ") -and `
                $global:CommandTracker[$LastCommand.Id.ToString()] -ne [LogStatus]::Completed) {
            # Convert the start and end timestamps to properly formatted strings (in UTC)
            $StartTime = $LastCommand.StartExecutionTime.ToUniversalTime().ToString("yyyy-MM-dd HH:mm:ss")
            $EndTime = $LastCommand.EndExecutionTime.ToUniversalTime().ToString("yyyy-MM-dd HH:mm:ss")

            #& py -c "print('test')"
            Log -StartTime $StartTime -EndTime $EndTime -Command $Command -Output $Output

            # Mark the command as completed so we don't get a duplicate if the user presses Enter on an empty line
            $global:CommandTracker.Set_Item($LastCommand.Id.ToString(), [LogStatus]::Completed)
        }
    }

    # Return the PowerShell prompt
    "PS $($executionContext.SessionState.Path.CurrentLocation.Path)$('>' * ($nestedPromptLevel + 1)) "
}
