# Windows native import failures

Use this workflow when Windows Python reports that a package is installed but importing it or one of its `.pyd` modules fails. Common messages include `ImportError`, `DLL load failed`, `The specified module could not be found`, `The specified procedure could not be found`, or an access/security error.

## Preserve the first failure

Capture the complete traceback, exact import command, interpreter path, exit code, and any Windows dialog before changing the environment. A failing `.pyd` is a Windows DLL; the named module may exist while one of its dependent DLLs is missing or blocked.

Run all Python and package checks through the project's selected interpreter:

```powershell
& .venv\Scripts\python.exe -c "import sys,platform; print(sys.executable); print(sys.version); print(platform.machine()); print(platform.architecture())"
& .venv\Scripts\python.exe -m pip show <package>
& .venv\Scripts\python.exe -m pip check
& .venv\Scripts\python.exe -c "import importlib.util; print(importlib.util.find_spec('<module>'))"
```

Do not use a bare `pip` or another Python installation to infer the state of the selected environment.

## Classify before repairing

Work through these classes in order:

1. **Wrong interpreter or missing package**
   - Compare `sys.executable` with the interpreter used by the application or launcher.
   - Confirm `pip show` and `find_spec` through that exact interpreter.
   - If the package is absent, install it through the project's established dependency workflow.

2. **Python ABI or CPU architecture mismatch**
   - Check Python major/minor version, 32/64-bit architecture, processor architecture, and the installed wheel tag or package metadata.
   - Treat errors such as `not a valid Win32 application`, missing exported procedures, or a wheel built for another Python version as compatibility evidence.
   - Select a compatible package build or interpreter through the main `$python-environment` workflow; do not copy `.pyd` files between environments.

3. **Missing dependent native runtime or DLL**
   - Locate the exact `.pyd` from the traceback or module spec.
   - Inspect package documentation for required Microsoft Visual C++ runtimes, CUDA libraries, vendor runtimes, or sibling DLLs.
   - Distinguish a missing dependency from the top-level `.pyd` being absent. Use an available trusted dependency inspection tool only when ordinary evidence is insufficient; do not install diagnostic software automatically.

4. **Incomplete, corrupt, or mixed installation**
   - Use `pip check`, package metadata, and file presence before reinstalling.
   - Suspect a mixed installation when files from multiple package versions coexist, installation was interrupted, or hashes/files differ from a trusted wheel.
   - Reinstall only after the selected interpreter, compatibility, dependent runtimes, and security events have been checked. Preserve project manifests and lockfiles unless the dependency itself must change.

5. **Mark-of-the-Web or Windows security enforcement**
   - Inspect the exact wheel, archive, `.pyd`, or DLL for an alternate data stream without changing it:

     ```powershell
     Get-Item -LiteralPath 'C:\path\module.pyd' -Stream * -ErrorAction SilentlyContinue
     Get-Content -LiteralPath 'C:\path\module.pyd' -Stream Zone.Identifier -ErrorAction SilentlyContinue
     Get-AuthenticodeSignature -LiteralPath 'C:\path\module.pyd'
     ```

   - Review relevant Windows logs near the failure time. Depending on the active controls, useful read-only sources can include Code Integrity, AppLocker, Windows Defender, or the organization's endpoint-security console. Correlate the event's path, timestamp, rule, and disposition with the failing file.
   - Treat quarantine, policy denial, or application-control blocking as a security-policy result, not proof that the Python dependency is corrupt. Reinstalling the same wheel often reproduces the failure.

## Repair by confirmed cause

- Install a missing package or compatible wheel only through the selected project environment.
- Install a required native runtime through `$software-installation` and its trusted-source rules.
- Recreate an environment only when it is actually inconsistent or incompatible; do not delete a healthy environment as a first response.
- Remove Mark-of-the-Web with `Unblock-File` only for an exact file or trusted downloaded archive whose provenance has been verified and when the user has authorized the change. Re-extract from the trusted unblocked archive when appropriate rather than mass-unblocking an environment.
- If organizational policy or endpoint protection blocked the file, report the exact component and evidence. Let the user or administrator choose an allow rule, approved distribution, or policy-compliant alternative.

Never disable antivirus, Smart App Control, AppLocker, Windows Defender Application Control, firewall, execution policy, or related protections globally as a generic Python fix. Do not recursively unblock a project, environment, Downloads directory, or drive.

## Verify the repair

Re-run the smallest original import through the exact interpreter, then run `pip check` and the application command that exposed the problem. Confirm that no new Code Integrity, AppLocker, Defender, or endpoint-security event was emitted for the module. Report the identified failure class, evidence, change made, interpreter used, and verification result.
