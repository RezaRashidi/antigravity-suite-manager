# Desktop App Electron Supervisor (`dist/languageServer.js`)

Extracted from `/opt/antigravity2/resources/app.asar/dist/languageServer.js`.

### 8.1 Process Lifecycle & Auto-Restart Mechanics

The Electron main process manages the Go Language Server binary as a child process:

```javascript
// Source: resources/app.asar/dist/languageServer.js
async function startAndMonitorLanguageServer(port, csrf, options) {
    const lsBinaryPath = getLanguageServerPath(); // /opt/antigravity2/resources/bin/language_server
    const lsArgs = [
        "--standalone",
        "--override_ide_name", "antigravity",
        "--subclient_type", "hub",
        "--override_ide_version", "2.23.1",
        "--override_user_agent_name", "antigravity",
        "--https_server_port", "0",              // 0 forces OS to assign dynamic ephemeral port
        "--csrf_token", csrf,
        "--app_data_dir", "antigravity",
        "--api_server_url", "https://generativelanguage.googleapis.com",
        "--cloud_code_endpoint", "https://daily-cloudcode-pa.googleapis.com",
        "--enable_sidecars"
    ];

    const child = child_process.spawn(lsBinaryPath, lsArgs, {
        stdio: ["ignore", "pipe", "pipe"],
        env: process.env
    });

    // Parses dynamically bound loopback port from stdout
    const boundPort = await readPortFromStdout(child.stdout);
    
    // Automatically restarts Language Server if killed or crashed
    monitorLsCrashInternal(child, boundPort, csrf, options);
    return { child, port: boundPort };
}

function monitorLsCrashInternal(handle, port, csrf, options) {
    handle.on("exit", (code, signal) => {
        console.warn(`[LS] Language Server exited with code ${code}, signal ${signal}. Restarting...`);
        if (!global.__is_quitting__) {
            setTimeout(() => {
                startAndMonitorLanguageServer(port, csrf, options);
            }, 1000);
        }
    });
}
```

---
