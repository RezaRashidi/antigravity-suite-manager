// Antigravity Multi-Account UI: Flyout Template and Positioning
(function initFlyoutModule() {
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

    window.__antigravityBuildFlyout = function(acc) {
        if (!acc) return '<div style="padding:10px;font-size:12px;">No account selected</div>';
        const tier = acc.tier || 'PRO', email = acc.email || 'Account';
        let body = '';

        if (acc.quotas && acc.quotas.length > 0) {
            const seen = new Set(), uq = acc.quotas.filter(q => {
                const k = `${q.family}:${q.window}`;
                if (seen.has(k)) return false;
                seen.add(k); return true;
            });
            const gemini = uq.filter(q => q.family === 'gemini');
            const claude = uq.filter(q => q.family === 'claude');
            const other = uq.filter(q => q.family !== 'gemini' && q.family !== 'claude');
            const claudeExhausted = claude.some(q => q.fraction === 0);
            let gh = '';
            if (gemini.length) gh += `<div class="agy-usage-group"><div class="agy-group-title">Gemini Models</div>${gemini.map(renderBucket).join('')}</div>`;
            if (claude.length) gh += `<div class="agy-usage-group" style="margin-top:6px;"><div class="agy-group-title">Claude and GPT models</div>${claude.map(renderBucket).join('')}</div>`;
            if (claudeExhausted) gh += `<div style="font-size:11px;color:#f59e0b;background:rgba(245,158,11,0.12);padding:5px 8px;border-radius:5px;margin-top:6px;border:1px solid rgba(245,158,11,0.25);line-height:1.3;">Claude 5-hour limit reached. Switch prompt bar dropdown to Gemini models.</div>`;
            if (other.length) gh += `<div class="agy-usage-group" style="margin-top:6px;"><div class="agy-group-title">Other Models</div>${other.map(renderBucket).join('')}</div>`;
            body = gh;
        } else if (acc.license_status === 'no_license') {
            body = `<div class="agy-usage-alert alert-warning"><div style="font-weight:600;margin-bottom:2px;">Subscription Required</div><div>This account does not have an active Gemini license.</div></div>`;
        } else if (acc.license_status === 'exhausted') {
            body = `<div class="agy-usage-alert alert-error"><div style="font-weight:600;margin-bottom:2px;">Resource Exhausted</div><div>5-Hour or weekly quota limit reached.</div></div>`;
        } else {
            body = `<div style="font-size:11px;color:var(--agy-dropdown-subtext);padding:8px 0;">Loading usage telemetry...</div>`;
        }

        let badgeText = 'PRO';
        if (acc.tier) {
            if (acc.tier === 'No License' || acc.license_status === 'no_license') badgeText = 'NO LICENSE';
            else if (acc.tier === 'Resource Exhausted' || acc.license_status === 'exhausted') badgeText = 'EXHAUSTED';
            else if (acc.tier.toLowerCase().includes('free') || acc.tier === 'UNKNOWN_TIER') badgeText = 'FREE';
            else badgeText = acc.tier.split(' ')[0].toUpperCase();
        }

        const footer = `<div class="agy-usage-footer"><button class="agy-flyout-logout-btn" data-email="${email}">Log Out (${email})</button></div>`;

        return `
            <div class="agy-usage-flyout-header">
                <div><div class="agy-usage-title">Usage limits</div><div class="agy-usage-email-sub">${email}</div></div>
                <span class="agy-tier-badge">${badgeText}</span>
            </div>
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
