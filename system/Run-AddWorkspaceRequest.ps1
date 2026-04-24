#Requires -Version 5.1
<#
.SYNOPSIS
    Self-extracting launcher for the Add-WorkspaceRequest feature script.

.DESCRIPTION
    Reads Add-WorkspaceRequest.ps1 (stored as pure ASCII), decodes it from
    base64, writes it to a temp file, executes it, then cleans up.

.NOTES
    Run from the repo root:
        .\system\Run-AddWorkspaceRequest.ps1

    Preview only (no writes):
        .\system\Run-AddWorkspaceRequest.ps1 -WhatIf
#>

[CmdletBinding(SupportsShouldProcess)]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Locate the sibling script and execute it directly
# ---------------------------------------------------------------------------

$_scriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$_targetScript = Join-Path $_scriptDir "Add-WorkspaceRequest.ps1"

if (-not (Test-Path $_targetScript)) {
    Write-Error "Cannot find Add-WorkspaceRequest.ps1 next to this launcher at: $_targetScript"
    exit 1
}

Write-Host ""
Write-Host "Launcher: forwarding to Add-WorkspaceRequest.ps1" -ForegroundColor DarkGray
Write-Host ""

if ($WhatIfPreference) {
    & $_targetScript -WhatIf
} else {
    & $_targetScript
}