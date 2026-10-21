// Multi-Account Router: Web API and In-Chat Remote Control Interceptor
const { getBindings, setBinding, setActiveAccount, getActiveAccountEmail, logTraffic } = require('./bindings');
const { loadAllAccounts } = require('./accounts');

function handleApiRequest(req, res, bodyStr) {
    if (!req.url.startsWith('/api/multi-account') && req.url !== '/ui_bundle.js') return false;
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', '*');
    if (req.method === 'OPTIONS') { res.writeHead(200); res.end(); return true; }

    if (req.url === '/ui_bundle.js' || req.url === '/api/multi-account/bundle.js') {
        try {
            const fs = require('fs'), path = require('path'), b = path.join(__dirname, '..');
            const css = fs.readFileSync(path.join(b, 'ui', 'styles.css'), 'utf8');
            const fly = fs.readFileSync(path.join(b, 'ui', 'flyout.js'), 'utf8');
            const mnt = fs.readFileSync(path.join(b, 'ui', 'mount.js'), 'utf8');
            const ui = fs.readFileSync(path.join(b, 'multi_account_ui.js'), 'utf8');
            const out = `(()=>{const s=document.createElement('style');s.textContent=${JSON.stringify(css)};document.head.appendChild(s);})();\n${fly}\n${mnt}\n${ui}`;
            res.writeHead(200, { 'Content-Type': 'application/javascript; charset=utf-8' });
            res.end(out);
        } catch (e) { res.writeHead(500); res.end('// Bundle error'); }
        return true;
    }
    if (req.url === '/api/multi-account/state') {
        const { _quotaCache } = require('./telemetry'), raw = Object.values(loadAllAccounts());
        const accounts = (_quotaCache.accounts && _quotaCache.accounts.length) ? _quotaCache.accounts : raw;
        const bindings = getBindings();
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ accounts, bindings, active_default: getActiveAccountEmail(raw) }));
        return true;
    }
    if (req.url === '/api/multi-account/bind' && req.method === 'POST') {
        try {
            const data = JSON.parse(bodyStr);
            if (data.cascadeId && data.email) {
                setBinding(data.cascadeId, data.email, data.model || '');
                if (data.active) setActiveAccount(data.email);
            }
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ ok: true }));
        } catch (_) { res.writeHead(400); res.end(JSON.stringify({ error: 'bad json' })); }
        return true;
    }
    if (req.url === '/api/multi-account/remove' && req.method === 'POST') {
        try {
            const data = JSON.parse(bodyStr);
            if (data.email) {
                const { removeAccount } = require('../multi_account_router');
                if (removeAccount) removeAccount(data.email);
            }
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ ok: true }));
        } catch (_) { res.writeHead(400); res.end(JSON.stringify({ error: 'bad json' })); }
        return true;
    }
    return false;
}

function tryInterceptCommand(req, res, bodyStr, cascadeId) {
    if (!req.url.includes('streamGenerateContent')) return false;
    let text = '';
    try {
        const parsed = JSON.parse(bodyStr);
        for (const p of parsed?.contents?.[0]?.parts || []) if (p.text) text += p.text;
    } catch (_) {}
    const cmd = text.trim();
    if (!cmd.startsWith('/accounts') && !cmd.startsWith('/switch') && !cmd.startsWith('/whoami')) return false;

    const accounts = Object.values(loadAllAccounts()), bindings = getBindings();
    const curEmail = (cascadeId && bindings[cascadeId]?.email) || getActiveAccountEmail(accounts) || 'Primary (Native)';
    let reply = '';

    if (cmd.startsWith('/switch')) {
        const arg = cmd.replace('/switch', '').trim();
        const target = accounts.find((a, i) => String(i + 1) === arg || (a.email && a.email.toLowerCase().includes(arg.toLowerCase())));
        if (target) {
            setBinding(cascadeId, target.email); setActiveAccount(target.email);
            reply = `✓ **Switched conversation to:** \`${target.email}\`\n\nAll subsequent messages in this session will use this account.`;
            logTraffic(`[REMOTE_CMD] Switched cascade [${cascadeId}] to [${target.email}]`);
        } else { reply = `❌ Account not found for: \`${arg}\`\n\nType \`/accounts\` to view available accounts.`; }
    } else {
        reply = `### 👤 Antigravity Accounts (Remote Control)\n\n**Current Chat Bound To:** \`${curEmail}\`\n\n**Available Accounts:**\n` +
            accounts.map((a, i) => `${i + 1}. **${a.email.split('@')[0]}** (\`${a.email}\`)${a.email.toLowerCase() === curEmail.toLowerCase() ? ' *(Current)*' : ''}`).join('\n') +
            `\n\n*To switch account, send:* \`/switch <number or email>\``;
    }

    const sse = `data: ${JSON.stringify({ candidates: [{ content: { parts: [{ text: reply }] }, finishReason: 'STOP' }] })}\n\ndata: [DONE]\n\n`;
    res.writeHead(200, { 'Content-Type': 'text/event-stream; charset=utf-8', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive' });
    res.end(sse);
    return true;
}

module.exports = { handleApiRequest, tryInterceptCommand };
