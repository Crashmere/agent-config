# Windows OpenSSH preparation

Use these commands on the Windows computer in an elevated PowerShell session when SSH is not already configured. Inspect current state first and skip changes that are already satisfied.

Check the `sshd` service and executable path as well as the Windows capability. A separately installed OpenSSH server can be running from a path such as `C:\Program Files\OpenSSH\sshd.exe` while `OpenSSH.Server~~~~0.0.1.0` reports `NotPresent`; do not reinstall or replace a working server based on capability state alone.

## Install and start the server

```powershell
Get-WindowsCapability -Online -Name 'OpenSSH.Server*'
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Set-Service -Name sshd -StartupType Automatic
Start-Service sshd
Get-Service sshd
```

Create a firewall rule only if an equivalent enabled rule does not already exist:

```powershell
$rule = Get-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -ErrorAction SilentlyContinue
if (-not $rule) {
    New-NetFirewallRule `
        -Name 'OpenSSH-Server-In-TCP' `
        -DisplayName 'OpenSSH Server (sshd)' `
        -Enabled True `
        -Direction Inbound `
        -Protocol TCP `
        -Action Allow `
        -LocalPort 22 `
        -Profile Private
}
```

Prefer the `Private` network profile for LAN access. Do not silently broaden the rule to public networks.

## Install a public key

For a standard Windows account, put one public key per line in:

```text
C:\Users\<username>\.ssh\authorized_keys
```

Create the directory and file under that user's identity when possible. Restrict ACLs to the user and SYSTEM; remove inherited access only after confirming the exact path and account.

For an account in the local Administrators group, the default Windows OpenSSH configuration commonly uses:

```text
C:\ProgramData\ssh\administrators_authorized_keys
```

Install the key from an elevated PowerShell session and restrict the ACL:

```powershell
$keyFile = 'C:\ProgramData\ssh\administrators_authorized_keys'
$publicKey = '<PUBLIC KEY>'.Trim()
New-Item -ItemType Directory -Path (Split-Path $keyFile) -Force | Out-Null
if (-not (Test-Path -LiteralPath $keyFile)) {
    New-Item -ItemType File -Path $keyFile | Out-Null
}
$existingKeys = @(Get-Content -LiteralPath $keyFile -ErrorAction Stop)
if ($existingKeys -cnotcontains $publicKey) {
    Add-Content -LiteralPath $keyFile -Value $publicKey -Encoding ascii
}

$system = [Security.Principal.SecurityIdentifier]::new('S-1-5-18')
$administrators = [Security.Principal.SecurityIdentifier]::new('S-1-5-32-544')
$acl = [Security.AccessControl.FileSecurity]::new()
$acl.SetAccessRuleProtection($true, $false)
$acl.SetOwner($administrators)
foreach ($sid in @($system, $administrators)) {
    $rule = [Security.AccessControl.FileSystemAccessRule]::new(
        $sid,
        [Security.AccessControl.FileSystemRights]::FullControl,
        [Security.AccessControl.AccessControlType]::Allow
    )
    $acl.AddAccessRule($rule)
}
Set-Acl -LiteralPath $keyFile -AclObject $acl
icacls.exe $keyFile
```

The SID-based ACL is language-independent and replaces inherited or unrelated explicit access with Full Control for SYSTEM and the built-in Administrators group. Never place a private key on the remote Windows host.

## Verify before ending the current session

```powershell
sshd.exe -t
Restart-Service sshd
Get-NetTCPConnection -LocalPort 22 -State Listen
```

From the client, open a second connection before closing the first:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=5 user@host 'whoami'
```

If authentication fails, inspect the effective `sshd_config`, selected key file, ACLs, username, host key, and the OpenSSH operational event log before weakening authentication settings.
