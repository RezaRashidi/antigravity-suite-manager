// Antigravity Multi-Account UI: Flyout Template and Positioning
(function initFlyoutModule() {
    if (window.__antigravityFlyoutInit) return;
    window.__antigravityFlyoutInit = true;
    function formatReset(b) {
        if (!b) return '';
        const desc = b.description || '';
        const m = desc.match(/refresh in ([^.]+)/i);
        if (m) {
            let s = m[1].trim();
            s = s.replace(/(\d+)\s*days?/gi, '$1d').replace(/(\d+)\s*hours?/gi, '$1h').replace(/(\d+)\s*minutes?/gi, '$1m').replace(/,\s*/g, ' ');
            return `Resets in ${s}`;
        }
        if (b.reset_time) {
            const ms = new Date(b.reset_time).getTime() - Date.now();
            if (ms > 0) {
                const h = Math.floor(ms / 3600000), min = Math.floor((ms % 3600000) / 60000);
                return h > 24 ? `Resets in ${Math.floor(h / 24)}d ${h % 24}h` : `Resets in ${h}h ${min}m`;
            }
        }
        return '';
    }

    function renderBucket(b) {
        if (!b) return '';
        const pct = typeof b.percent === 'number' ? b.percent : Math.round((b.fraction ?? 1) * 100);
        const color = pct >= 50 ? '#10b981' : (pct >= 20 ? '#f59e0b' : '#ef4444');
        const rst = formatReset(b);
        return `
            <div class="agy-bucket-box">
                <div class="agy-bucket-meta"><span>${b.label || 'Limit'}</span><span style="font-weight:600;color:${color}">${pct}%</span></div>
                <div class="agy-bucket-bar-track"><div class="agy-bucket-bar-fill" style="width:${pct}%;background:${color}"></div></div>
                ${rst ? `<div class="agy-bucket-reset">${rst}</div>` : ''}
            </div>
        `;
    }

    function escHtml(s) {
        return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    window.__antigravityBuildFlyout = function(acc) {
        if (!acc) return '<div style="padding:10px;font-size:12px;">No account selected</div>';
        const tier = acc.tier || 'PRO', rawEmail = acc.email || 'Account', email = escHtml(rawEmail);
        let body = '';

        const errDetail = escHtml(acc.license_message || acc.refresh_error || '');
        if (acc.license_status === 'verify_required' || acc.tier === 'Verify Required') {
            const vUrl = acc.verify_url || 'https://accounts.google.com/ServiceLogin';
            const safeUrl = escHtml(vUrl);
            body = `<div class="agy-usage-alert alert-error"><div style="font-weight:600;margin-bottom:3px;">Verification Required</div><div>${errDetail || 'Google requires account verification (HTTP 403). Excluded from automatic routing until verified.'}</div><div style="margin-top:6px;display:flex;gap:6px;flex-wrap:wrap;"><a class="agy-flyout-verify-link" href="${safeUrl}" target="_blank" rel="noopener noreferrer" data-url="${safeUrl}" style="display:inline-block;background:#ef4444;color:#fff;text-decoration:none;padding:3px 8px;border-radius:4px;font-size:10px;font-weight:600;cursor:pointer;">Verify Account ↗</a><button type="button" class="agy-flyout-copy-url" data-url="${safeUrl}" style="background:rgba(255,255,255,0.08);color:var(--agy-dropdown-text);border:1px solid var(--agy-dropdown-border);padding:3px 8px;border-radius:4px;font-size:10px;cursor:pointer;">Copy Link</button></div></div>`;
        } else if (acc.license_status === 'auth_failed' || acc.tier === 'Auth Required') {
            body = `<div class="agy-usage-alert alert-error"><div style="font-weight:600;margin-bottom:2px;">Logged Out / Session Expired</div><div>${errDetail || 'Token refresh failed or account was signed out. Click "+ Add Account" to sign in again.'}</div></div>`;
        } else if (acc.license_status === 'no_license' || acc.tier === 'No License') {
            body = `<div class="agy-usage-alert alert-warning"><div style="font-weight:600;margin-bottom:2px;">Subscription Required</div><div>${errDetail || 'This account does not have an active Gemini license.'}</div></div>`;
        } else if (acc.quotas && acc.quotas.length > 0) {
            const seen = new Set(), uq = acc.quotas.filter(q => {
                const k = `${q.family}:${q.window}`;
                if (seen.has(k)) return false;
                seen.add(k); return true;
            });
            const gemini = uq.filter(q => q.family === 'gemini');
            const argon = uq.filter(q => q.family === 'argon');
            const claude = uq.filter(q => q.family === 'claude');
            const other = uq.filter(q => q.family !== 'gemini' && q.family !== 'argon' && q.family !== 'claude');
            const claudeExhausted = claude.some(q => q.fraction === 0);
            let gh = '';
            if (acc.refresh_error) gh += `<div class="agy-usage-alert alert-warning" style="margin-bottom:6px;"><div style="font-weight:600;margin-bottom:1px;">Not Refreshed (Cached)</div><div>${escHtml(acc.refresh_error)}</div></div>`;
            if (gemini.length) gh += `<div class="agy-usage-group"><div class="agy-group-title">Gemini Models</div>${gemini.map(renderBucket).join('')}</div>`;
            if (argon.length) gh += `<div class="agy-usage-group" style="margin-top:6px;"><div class="agy-group-title">Gemini 4 Argon</div>${argon.map(renderBucket).join('')}</div>`;
            if (claude.length) gh += `<div class="agy-usage-group" style="margin-top:6px;"><div class="agy-group-title">Claude and GPT models</div>${claude.map(renderBucket).join('')}</div>`;
            if (claudeExhausted) gh += `<div style="font-size:11px;color:#f59e0b;background:rgba(245,158,11,0.12);padding:5px 8px;border-radius:5px;margin-top:6px;border:1px solid rgba(245,158,11,0.25);line-height:1.3;">Claude 5-hour limit reached. Switch prompt bar dropdown to Gemini models.</div>`;
            if (other.length) gh += `<div class="agy-usage-group" style="margin-top:6px;"><div class="agy-group-title">Other Models</div>${other.map(renderBucket).join('')}</div>`;
            body = gh;
        } else if (acc.license_status === 'exhausted' || acc.tier === 'Resource Exhausted') {
            body = `<div class="agy-usage-alert alert-error"><div style="font-weight:600;margin-bottom:2px;">Resource Exhausted</div><div>${errDetail || '5-Hour or weekly quota limit reached.'}</div></div>`;
        } else if (acc.license_status === 'refresh_failed' || acc.license_status === 'network_error' || acc.license_status === 'forbidden_transient' || acc.refresh_error) {
            body = `<div class="agy-usage-alert alert-warning"><div style="font-weight:600;margin-bottom:2px;">Refresh Failed</div><div>${errDetail || 'Could not fetch live quota/models from Google. Check proxy/network and click Refresh.'}</div></div>`;
        } else {
            body = `<div style="font-size:11px;color:var(--agy-dropdown-subtext);padding:8px 0;">Loading usage telemetry...</div>`;
        }

        const rawPlanName = acc.plan || (acc.userTier?.name) || (acc.tier === 'PRO' ? 'Google AI Pro' : (acc.tier || 'Google AI Pro'));
        const planName = escHtml(rawPlanName);
        let badgeText = 'PRO';
        if (acc.tier === 'Verify Required' || acc.license_status === 'verify_required') badgeText = 'VERIFY';
        else if (acc.tier === 'Auth Required' || acc.license_status === 'auth_failed') badgeText = 'LOGGED OUT';
        else if (acc.tier === 'No License' || acc.license_status === 'no_license') badgeText = 'NO LICENSE';
        else if (acc.tier === 'Resource Exhausted' || acc.license_status === 'exhausted') badgeText = 'EXHAUSTED';
        else if (acc.license_status === 'refresh_failed' || acc.license_status === 'network_error') badgeText = 'REFRESH ERR';
        else if (acc.tier_type === 'Paid Pro' || acc.tier === 'Paid Pro') badgeText = 'PAID PRO';
        else if (acc.tier_type === 'Free Pro' || acc.tier === 'Free Pro') badgeText = 'FREE PRO';
        else if (rawPlanName.toLowerCase().includes('pro') || acc.tier === 'PRO' || acc.tier === 'TEAMS_TIER_PRO') badgeText = 'PRO';
        else if (acc.tier && (acc.tier.toLowerCase().includes('free') || acc.tier === 'UNKNOWN_TIER')) badgeText = 'FREE';
        else badgeText = 'PRO';

        const primBadge = acc.is_primary ? '<div style="font-size:11px;color:#eab308;font-weight:600;margin-top:2px;">★ Primary Account (Native Session)</div>' : '<div style="font-size:11px;opacity:0.6;margin-top:2px;">Secondary Account</div>';
        const bypassBadge = acc.is_bypassed ? '<div class="agy-bypass-badge" style="display:inline-block;font-size:10px;color:#10b981;background:rgba(16,185,129,0.15);border:1px solid rgba(16,185,129,0.3);padding:1px 6px;border-radius:3px;font-weight:600;margin-top:3px;">Region Bypass</div>' : '';
        const modelCount = (acc.available_models && acc.available_models.length) || acc.model_count || 0;
        const modelsSummary = modelCount ? `<div style="font-size:11px;color:var(--agy-dropdown-text);background:var(--agy-dropdown-hover);border:1px solid var(--agy-dropdown-border);padding:6px 10px;border-radius:6px;margin-bottom:8px;display:flex;align-items:center;justify-content:space-between;"><strong style="color:var(--agy-dropdown-text);font-weight:600;">Models:</strong><span style="font-weight:600;color:var(--agy-dropdown-text);">${modelCount}</span></div>` : '';

        const footer = `<div class="agy-usage-footer" style="display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end;">${!acc.is_primary ? `<button class="agy-flyout-primary-btn" data-email="${email}" style="background:#3b82f6;color:#fff;border:none;padding:3px 8px;border-radius:4px;font-size:10px;cursor:pointer;font-weight:600;">⭐ Make Primary</button>` : ''}<button class="agy-flyout-logout-btn" data-email="${email}">Log Out (${email})</button></div>`;

        return `
            <div class="agy-usage-flyout-header">
                <div>
                    <div class="agy-usage-title">Usage limits</div>
                    <div class="agy-usage-email-sub">${email} • <span style="color:var(--agy-accent,#38bdf8);font-weight:600;">${planName}</span></div>
                    ${primBadge}
                    ${bypassBadge}
                </div>
                <span class="agy-tier-badge" style="${badgeText === 'PAID PRO' ? 'background:rgba(168,85,247,0.2);color:#c084fc;border:1px solid rgba(168,85,247,0.4);' : (badgeText === 'FREE PRO' ? 'background:rgba(59,130,246,0.2);color:#60a5fa;border:1px solid rgba(59,130,246,0.4);' : '')}">${badgeText}</span>
            </div>
            ${modelsSummary}
            ${body}
            ${footer}
        `;
    };
    function setHtml(el, str) {
        try {
            if (!window.__agyPolicy && window.trustedTypes?.createPolicy) { for (const p of ['renderCodeBlock', 'tokenizeToString', 'google#safe', 'dompurify']) { try { window.__agyPolicy = window.trustedTypes.createPolicy(p, { createHTML: s => s }); break; } catch (_) {} } }
            if (window.__agyPolicy?.createHTML) { el.innerHTML = window.__agyPolicy.createHTML(str); return; }
        } catch (_) {}
        el.innerHTML = str;
    }
    window.__antigravitySetHtml = setHtml;
    window.__antigravityShowFlyout = function(flyout, acc, dropdown, triggerEl) {
        if (!flyout) return;
        setHtml(flyout, window.__antigravityBuildFlyout(acc));
        flyout.classList.add('visible');
        if (dropdown) {
            const ddRect = dropdown.getBoundingClientRect(), bOffset = Math.max(10, window.innerHeight - ddRect.bottom);
            flyout.style.bottom = bOffset + 'px'; flyout.style.top = 'auto';
            if (ddRect.right + 330 > window.innerWidth) { flyout.style.left = 'auto'; flyout.style.right = (window.innerWidth - ddRect.left + 6) + 'px'; }
            else { flyout.style.left = (ddRect.right + 6) + 'px'; flyout.style.right = 'auto'; }
        }
    };
})();
