# Forensic Incident Report #34: Repository Update Shallow Clone Blockade, Hidden Path Discovery Deficit & Patch Synchronization Gap

## 1. Executive Summary & Incident Chronology

### Incident Context
When executing `manage-antigravity.sh update-repo`, the operator observed:
```bash
❯ manage-antigravity.sh update-repo
[INFO] Detecting Antigravity Suite Manager repository...
[INFO] Updating repository at /home/reza/.antigravity-suite-manager via git pull...
From https://github.com/RezaRashidi/antigravity-suite-manager
 * branch            main       -> FETCH_HEAD
Already up to date.
[SUCCESS] Repository successfully updated from origin/main.
[INFO] Recompiling Catmull-Rom resampler...
[INFO] Redeploying suite scripts and libraries to /home/reza/.local/bin...
[INFO] Restarting background services with updated codebase...
[INFO] Restarting Antigravity Suite background services...
[SUCCESS] Systemd history sync daemon restarted.
[SUCCESS] X11 icon injector daemon restarted.
[SUCCESS] All Antigravity Suite background services restarted.
[SUCCESS] Antigravity Suite Manager repository update complete!
```

Despite upstream commits existing on `origin/main` (e.g. modularization and sync commits `6cedc3f`, `259110c`), the local repository remained frozen on commit `cba4359` and claimed it was `Already up to date.`.

Furthermore, changes pushed to the repository for UI/binary patching (such as conversation forking isolation) did not propagate into the running Electron applications (`/opt/antigravity2/resources/app.asar` and `/opt/antigravity/resources/app/out/ui/mount.js`).

---

## 2. Root Cause Analysis (RCA)

Investigation into `bin/lib/sh/repo_update.sh` and the local `.git` metadata identified three distinct root causes:

### Cause A: Git Shallow Clone Boundary (`.git/shallow`)
The repository at `/home/reza/.antigravity-suite-manager` was initially provisioned via a shallow clone (`git clone --depth 1 ...`).
- In Git, shallow repositories contain a `.git/shallow` file listing boundary commit hashes.
- When `git pull` runs without `--unshallow`, git fetches commits relative to the shallow graft boundary. If the remote branch history bifurcates or the depth horizon cannot resolve non-contiguous ancestor objects, `git pull` can report `Already up to date.` despite remote `origin/main` having advanced, or it can fail to update the local tracking branch.
- Running `git rev-parse --is-shallow-repository` returned `true`.

### Cause B: Path Discovery Deficit in `find_suite_repo_root()`
The updater script `bin/lib/sh/repo_update.sh` implements an automated repository detection function:
```bash
find_suite_repo_root() {
    local candidates=(
        "$(pwd)"
        "${SCRIPT_DIR}/../.."
        "${REAL_HOME}/antigravity-suite-manager"
        "${REAL_HOME}/projects/antigravity-suite-manager"
        "${REAL_HOME}/src/antigravity-suite-manager"
    )
    ...
```
The primary operational installation on Linux workstations is located at `${REAL_HOME}/.antigravity-suite-manager` (a hidden dotfile directory). Because this path was omitted from the candidate list, if `manage-antigravity.sh update-repo` was invoked from an arbitrary working directory (e.g. from `/home/reza`), discovery depended entirely on `${SCRIPT_DIR}/../..` resolution through symlinks, failing to find the target if symlinks resolved to `~/.local/bin/`.

### Cause C: Decoupling of Repository Update and Binary Patch Deployment
`manage-antigravity.sh update-repo` was designed to:
1. `git pull` repository code.
2. Recompile C resamplers (`scale_icon`).
3. Deploy CLI scripts and libraries to `~/.local/bin`.
4. Restart background systemd services (`antigravity-history-sync.service`, `antigravity-icon-injector.service`).

Crucially, **it did not trigger application binary patches**:
- `/opt/antigravity2/resources/app.asar` (Hub)
- `/opt/antigravity/resources/app/out/ui/mount.js` (IDE)

Thus, even after a successful git pull of new patch code (such as clean conversation forking), the live Electron app bundles retained whatever patches had been previously packed into `app.asar`.

---

## 3. Surgical Remediation

### 1. Repository Unshallowing
The local repository was converted from a shallow clone into a complete Git tree:
```bash
git fetch --unshallow origin
```
Verification confirmed `git rev-parse --is-shallow-repository` returned `false` and all upstream commits (`6cedc3f`, `259110c`) became immediately accessible for rebasing.

### 2. Enhancing `bin/lib/sh/repo_update.sh`
The updater was hardened with two permanent mechanisms:

#### a. Adding the Hidden Dotfile Path to Discovery
```bash
find_suite_repo_root() {
    local candidates=(
        "$(pwd)"
        "${SCRIPT_DIR}/../.."
        "${REAL_HOME}/.antigravity-suite-manager"
        "${REAL_HOME}/antigravity-suite-manager"
        "${REAL_HOME}/projects/antigravity-suite-manager"
        "${REAL_HOME}/src/antigravity-suite-manager"
    )
```

#### b. Automated Shallow Clone Detection and Self-Healing
```bash
# Auto-detect and fix shallow clones to prevent false 'Already up to date'
if git -C "${repo_dir}" rev-parse --is-shallow-repository 2>/dev/null | grep -q "true" || [[ -f "${repo_dir}/.git/shallow" ]]; then
    log_info "Detected shallow git repository. Unshallowing from origin..."
    if ! git -C "${repo_dir}" fetch --unshallow origin; then
        log_warn "Failed to unshallow repository from origin; proceeding with standard fetch."
    else
        log_success "Repository successfully converted to full commit history."
    fi
fi
```

### 3. Synchronization to Executable Path
The updated script was deployed to `/home/reza/.local/bin/lib/sh/repo_update.sh` to ensure subsequent invocations of `manage-antigravity.sh update-repo` use the unshallowed discovery logic.

---

## 4. Operational Safety Adherence

1. **Antigravity Process Isolation**:
   In strict adherence to user directives, no Antigravity Hub or IDE instances were killed or restarted during this investigation and remediation.
2. **Quota Router Bug Scope**:
   The Core Quota Router Bug (Bug 3 in `bin/lib/patch/router/server.js`) was strictly preserved and untouched, awaiting explicit user instruction.
