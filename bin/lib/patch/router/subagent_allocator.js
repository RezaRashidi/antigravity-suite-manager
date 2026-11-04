// Multi-Account Router: Subagent Dynamic Account Allocator
const fs = require('fs');
const path = require('path');
const os = require('os');
const { ACCOUNTS_DIR, logTraffic } = require('./bindings.js');

const POLICY_FILE = path.join(ACCOUNTS_DIR, 'subagent_policy.json');
const _subagentCache = new Map();
const _inFlightCounts = new Map();
const _subagentLeases = new Map();
const _lastUsedTimestamps = new Map();

function getBrainRoots() {
    const home = process.env.REAL_HOME || os.homedir();
    return [
        path.join(home, '.gemini', 'antigravity', 'brain'),
        path.join(home, '.gemini', 'jetski', 'brain'),
        path.join(home, '.gemini', 'brain'),
    ].filter(fs.existsSync);
}

function getSubagentPolicy() {
    try {
        if (fs.existsSync(POLICY_FILE)) return JSON.parse(fs.readFileSync(POLICY_FILE, 'utf8'));
    } catch (_) {}
    return { enabled: true, proactive_mode: true };
}

function setSubagentPolicy(policy = {}) {
    try {
        if (!fs.existsSync(ACCOUNTS_DIR)) fs.mkdirSync(ACCOUNTS_DIR, { recursive: true });
        const cur = getSubagentPolicy();
        const next = { ...cur, ...policy, updated_at: new Date().toISOString() };
        fs.writeFileSync(POLICY_FILE, JSON.stringify(next, null, 2), 'utf8');
        return next;
    } catch (e) {
        return { enabled: true, proactive_mode: true, error: e.message };
    }
}

function isSubagent(cascadeId) {
    if (!cascadeId || typeof cascadeId !== 'string' || cascadeId.length < 8) return { isSubagent: false };
    if (_subagentCache.has(cascadeId)) {
        const entry = _subagentCache.get(cascadeId);
        const ttl = entry.isSubagent ? 300000 : 2000;
        if (Date.now() - entry.cachedAt < ttl) return entry;
    }

    for (const root of getBrainRoots()) {
        try {
            const parents = fs.readdirSync(root);
            for (const parent of parents) {
                const subagentJson = path.join(root, parent, '.system_generated', 'subagents', `${cascadeId}.json`);
                if (fs.existsSync(subagentJson)) {
                    let desc = null, state = 'RUNNING';
                    try {
                        const raw = JSON.parse(fs.readFileSync(subagentJson, 'utf8'));
                        desc = raw.subagentDescriptor || null;
                        state = raw.state || 'RUNNING';
                    } catch (_) {}
                    const result = { isSubagent: true, parentId: parent, state, descriptor: desc, cachedAt: Date.now() };
                    _subagentCache.set(cascadeId, result);
                    return result;
                }
            }
        } catch (_) {}
    }

    const notSub = { isSubagent: false, cachedAt: Date.now() };
    _subagentCache.set(cascadeId, notSub);
    return notSub;
}

function trackInFlight(email, delta) {
    if (!email) return;
    const cur = _inFlightCounts.get(email) || 0;
    const next = Math.max(0, cur + delta);
    _inFlightCounts.set(email, next);
    if (delta > 0) _lastUsedTimestamps.set(email, Date.now());
}

function getInFlightCount(email) {
    return _inFlightCounts.get(email) || 0;
}

function allocateAccountForSubagent(subagentId, parentId, accountsMap = {}, bindings = {}, quotas = []) {
    if (!subagentId) return null;
    if (_subagentLeases.has(subagentId)) {
        const lease = _subagentLeases.get(subagentId);
        if (accountsMap[lease.email] && Date.now() - lease.leasedAt < 3600000) return lease.email;
    }

    const emails = Object.keys(accountsMap);
    if (!emails.length) return null;
    if (emails.length === 1) return emails[0];

    const parentEmail = (parentId && bindings[parentId]?.email) || null;
    let candidates = emails.filter(em => em !== parentEmail);
    if (!candidates.length) candidates = emails;

    if (quotas && quotas.length > 0) {
        const withQuota = candidates.filter(em => {
            const q = quotas.find(item => item.email?.toLowerCase() === em.toLowerCase());
            return !q || q.remainingFraction > 0.05;
        });
        if (withQuota.length > 0) candidates = withQuota;
    }

    const idleCandidates = candidates.filter(em => (_inFlightCounts.get(em) || 0) === 0);
    const pool = idleCandidates.length ? idleCandidates : candidates;

    pool.sort((a, b) => {
        const loadA = _inFlightCounts.get(a) || 0;
        const loadB = _inFlightCounts.get(b) || 0;
        if (loadA !== loadB) return loadA - loadB;

        const quotaA = quotas.find(q => q.email === a)?.remainingFraction ?? 1.0;
        const quotaB = quotas.find(q => q.email === b)?.remainingFraction ?? 1.0;
        if (Math.abs(quotaA - quotaB) > 0.05) return quotaB - quotaA;

        const tsA = _lastUsedTimestamps.get(a) || 0;
        const tsB = _lastUsedTimestamps.get(b) || 0;
        return tsA - tsB;
    });

    const chosen = pool[0];
    _subagentLeases.set(subagentId, { email: chosen, leasedAt: Date.now(), parentId });
    _lastUsedTimestamps.set(chosen, Date.now());
    logTraffic(`[SUBAGENT_ALLOC] Subagent: [${subagentId}] (Parent: [${parentId || 'unknown'}]) leased idle account: [${chosen}] (Load: ${_inFlightCounts.get(chosen) || 0})`);
    return chosen;
}

function releaseSubagentLease(subagentId) {
    if (subagentId && _subagentLeases.has(subagentId)) {
        const lease = _subagentLeases.get(subagentId);
        _subagentLeases.delete(subagentId);
        logTraffic(`[SUBAGENT_RELEASE] Subagent: [${subagentId}] released account lease: [${lease.email}]`);
    }
}

module.exports = {
    getSubagentPolicy,
    setSubagentPolicy,
    isSubagent,
    trackInFlight,
    getInFlightCount,
    allocateAccountForSubagent,
    releaseSubagentLease,
    _inFlightCounts,
    _subagentLeases,
};
