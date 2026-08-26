[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
$isAdministrator = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
$os = Get-CimInstance Win32_OperatingSystem
$sshService = Get-Service sshd -ErrorAction SilentlyContinue
$sshFeature = Get-WindowsCapability -Online -Name 'OpenSSH.Server*' -ErrorAction SilentlyContinue |
    Select-Object -First 1
$listeners = @(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
    Where-Object LocalPort -eq 22 |
    Select-Object LocalAddress, LocalPort, OwningProcess)
$addresses = @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object {
        $_.IPAddress -notlike '127.*' -and
        $_.IPAddress -notlike '169.254.*'
    } |
    Select-Object InterfaceAlias, IPAddress, PrefixLength)

[ordered]@{
    computer_name = $env:COMPUTERNAME
    user = $identity.Name
    is_administrator = $isAdministrator
    windows = [ordered]@{
        caption = $os.Caption
        version = $os.Version
        build = $os.BuildNumber
        architecture = $os.OSArchitecture
    }
    powershell = [ordered]@{
        edition = $PSVersionTable.PSEdition
        version = $PSVersionTable.PSVersion.ToString()
        output_encoding = [Console]::OutputEncoding.WebName
    }
    openssh_server = [ordered]@{
        capability_state = if ($sshFeature) { $sshFeature.State.ToString() } else { $null }
        service_status = if ($sshService) { $sshService.Status.ToString() } else { $null }
        service_start_type = if ($sshService) { $sshService.StartType.ToString() } else { $null }
        listeners = $listeners
    }
    ipv4 = $addresses
} | ConvertTo-Json -Depth 6 -Compress
