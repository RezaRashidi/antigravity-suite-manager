'use strict';

/**
 * Race-free Electron relaunch for Linux single-instance apps.
 * Avoids Electron app.relaunch() + app.exit() colliding with requestSingleInstanceLock()
 * by waiting for the exiting PID to terminate before spawning the fresh instance.
 */

const { spawn } = require('child_process');

function scheduleCleanRelaunch(app, opts = {}) {
    if (!app) return false;
    const delayMs = Number(opts.delayMs || 60);
    const killTimeoutMs = Number(opts.killTimeoutMs || 2000);
    const args = process.argv.slice(1).filter((a) => typeof a === 'string' && !a.startsWith('--type='));
    const script = [
        'pid="$1"; bin="$2"; shift 2;',
        'i=0; while kill -0 "$pid" 2>/dev/null && [ "$i" -lt 60 ]; do sleep 0.1; i=$((i+1)); done;',
        'sleep 0.25;',
        'exec "$bin" "$@" >/dev/null 2>&1',
    ].join(' ');

    try {
        const child = spawn('bash', ['-c', script, 'suite-relaunch', String(process.pid), process.execPath, ...args], {
            detached: true,
            stdio: 'ignore',
            env: { ...process.env },
        });
        child.unref();
    } catch (_) {
        try { app.relaunch(); } catch (_) {}
    }

    try {
        if (typeof app.releaseSingleInstanceLock === 'function') {
            app.releaseSingleInstanceLock();
        }
    } catch (_) {}

    setTimeout(() => {
        try { app.quit(); } catch (_) {}
        setTimeout(() => {
            try { app.exit(0); } catch (_) {}
        }, killTimeoutMs).unref?.();
    }, delayMs);
    return true;
}

module.exports = { scheduleCleanRelaunch };
