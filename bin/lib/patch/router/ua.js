// Multi-Account Router: Authentic Installed User-Agent Resolution Helper
const fs = require('fs');
const path = require('path');

let _cachedUserAgent = null;
let _cachedVersion = null;
let _lastCheck = 0;

function getInstalledVersion() {
    if (_cachedVersion && (Date.now() - _lastCheck < 60000)) {
        return _cachedVersion;
    }

    // 1. Try reading /proc for running language_server
    try {
        if (fs.existsSync('/proc')) {
            const pids = fs.readdirSync('/proc').filter(p => /^\d+$/.test(p));
            for (const pid of pids) {
                try {
                    const cmd = fs.readFileSync('/proc/' + pid + '/cmdline', 'utf8');
                    if (cmd.includes('language_server') && cmd.includes('--override_ide_version')) {
                        const m = cmd.match(/--override_ide_version\x00([^\x00]+)/);
                        if (m && m[1] && m[1].trim()) {
                            _cachedVersion = m[1].trim();
                            _lastCheck = Date.now();
                            return _cachedVersion;
                        }
                    }
                } catch (_) {}
            }
        }
    } catch (_) {}

    // 2. Try reading package.json relative to current directory (in Electron / app.asar)
    try {
        const cands = [
            path.join(__dirname, '..', '..', 'package.json'),
            path.join(__dirname, '..', 'package.json'),
            '/opt/antigravity2/resources/app/package.json',
            '/opt/antigravity/resources/app/package.json',
        ];
        for (const p of cands) {
            if (fs.existsSync(p)) {
                const pkg = JSON.parse(fs.readFileSync(p, 'utf8'));
                if (pkg.version) {
                    _cachedVersion = pkg.version;
                    _lastCheck = Date.now();
                    return _cachedVersion;
                }
            }
        }
    } catch (_) {}

    // 3. Try reading asar header directly without external dependencies
    try {
        const asarPath = '/opt/antigravity2/resources/app.asar';
        if (fs.existsSync(asarPath)) {
            const fd = fs.openSync(asarPath, 'r');
            const buf = Buffer.alloc(16);
            fs.readSync(fd, buf, 0, 16, 0);
            const totalHeaderSize = buf.readUInt32LE(4);
            const jsonLen = buf.readUInt32LE(12);
            const jsonBuf = Buffer.alloc(jsonLen);
            fs.readSync(fd, jsonBuf, 0, jsonLen, 16);
            const header = JSON.parse(jsonBuf.toString('utf8'));
            const pkgEntry = header.files && header.files['package.json'];
            if (pkgEntry) {
                const offset = parseInt(pkgEntry.offset, 10);
                const size = parseInt(pkgEntry.size, 10);
                const payloadStart = 8 + totalHeaderSize;
                const pkgBuf = Buffer.alloc(size);
                fs.readSync(fd, pkgBuf, 0, size, payloadStart + offset);
                fs.closeSync(fd);
                const pkg = JSON.parse(pkgBuf.toString('utf8'));
                if (pkg.version) {
                    _cachedVersion = pkg.version;
                    _lastCheck = Date.now();
                    return _cachedVersion;
                }
            } else {
                fs.closeSync(fd);
            }
        }
    } catch (_) {}

    _cachedVersion = '2.29.1';
    _lastCheck = Date.now();
    return _cachedVersion;
}

function getAuthenticUserAgent() {
    if (_cachedUserAgent && (Date.now() - _lastCheck < 60000)) {
        return _cachedUserAgent;
    }

    const osMap = { win32: 'windows', darwin: 'darwin', linux: 'linux' };
    const osType = osMap[process.platform] || process.platform;
    const archMap = { x64: 'amd64', arm64: 'arm64', ia32: '386', arm: 'arm' };
    const arch = archMap[process.arch] || process.arch;
    const ver = getInstalledVersion();

    _cachedUserAgent = `antigravity/hub/${ver} (os_type=${osType}; arch=${arch})`;
    return _cachedUserAgent;
}

module.exports = {
    getInstalledVersion,
    getAuthenticUserAgent
};
