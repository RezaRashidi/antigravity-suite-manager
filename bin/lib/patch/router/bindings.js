// Multi-Account Router: Cascade & Active Account Bindings Repository
const fs = require('fs');
const path = require('path');
const os = require('os');

const ACCOUNTS_DIR = process.env.ANTIGRAVITY_ACCOUNTS_DIR ||
    path.join(process.env.REAL_HOME || os.homedir(), '.config', 'antigravity', 'accounts');
const BINDINGS_FILE = path.join(ACCOUNTS_DIR, 'bindings.json');
const TRAFFIC_LOG = path.join(ACCOUNTS_DIR, 'traffic.log');

let _activeAccountEmail = null;

function ensureAccountsDir() {
    try {
        if (!fs.existsSync(ACCOUNTS_DIR)) fs.mkdirSync(ACCOUNTS_DIR, { recursive: true });
    } catch (_) {}
}

function logTraffic(message) {
    try {
        ensureAccountsDir();
        fs.appendFileSync(TRAFFIC_LOG, `[${new Date().toISOString()}] ${message}\n`, 'utf8');
    } catch (_) {}
}

function getBindings() {
    try {
        if (fs.existsSync(BINDINGS_FILE)) {
            return JSON.parse(fs.readFileSync(BINDINGS_FILE, 'utf8'));
        }
    } catch (_) {}
    return {};
}

function setActiveAccount(email) {
    if (!email) return;
    _activeAccountEmail = email;
    ensureAccountsDir();
    const b = getBindings();
    b.__active_account = email;
    try {
        const tmp = BINDINGS_FILE + '.tmp';
        fs.writeFileSync(tmp, JSON.stringify(b, null, 2), 'utf8');
        fs.renameSync(tmp, BINDINGS_FILE);
        logTraffic(`[ACTIVE] Active account set to: ${email}`);
    } catch (_) {}
}

function getActiveAccountEmail(accountsMap = {}) {
    if (_activeAccountEmail) return _activeAccountEmail;
    const b = getBindings();
    if (b.__active_account) {
        _activeAccountEmail = b.__active_account;
        return _activeAccountEmail;
    }
    const accounts = Object.keys(accountsMap);
    return accounts[0] || null;
}

function setBinding(cascadeId, email, model = '') {
    ensureAccountsDir();
    const b = getBindings();
    b[cascadeId] = { cascade_id: cascadeId, email, model, updated_at: new Date().toISOString() };
    if (cascadeId === '__default__' || cascadeId === 'default') { b.__active_account = email; _activeAccountEmail = email; }
    try {
        const tmp = BINDINGS_FILE + '.tmp';
        fs.writeFileSync(tmp, JSON.stringify(b, null, 2), 'utf8');
        fs.renameSync(tmp, BINDINGS_FILE);
        logTraffic(`[BIND] Chat: ${cascadeId} bound to account: ${email}`);
    } catch (e) {
        console.error('[MultiAccountRouter] Failed to write bindings:', e.message);
    }
}

module.exports = {
    ACCOUNTS_DIR,
    BINDINGS_FILE,
    TRAFFIC_LOG,
    ensureAccountsDir,
    logTraffic,
    getBindings,
    setBinding,
    setActiveAccount,
    getActiveAccountEmail,
};
