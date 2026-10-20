// Antigravity Multi-Account UI: Flyout Template and Positioning
(function initFlyoutModule() {
    function renderBucket(b) {
        if (!b) return '';
        const pct = typeof b.percent === 'number' ? b.percent : Math.round((b.fraction ?? 1) * 100);
        const color = pct >= 50 ? '#10b981' : (pct >= 20 ? '#f59e0b' : '#ef4444');
        return `
            <div class="agy-bucket-box">
                <div class="agy-bucket-meta"><span>${b.label || 'Limit'}</span><span style="font-weight:600;color:${color}">${pct}%</span></div>
                <div class="agy-bucket-bar-track"><div class="agy-bucket-bar-fill" style="width:${pct}%;background:${color}"></div></div>
                ${b.description ? `<div class="agy-bucket-reset">${b.description}</div>` : ''}
            </div>
        `;
    }

    window.__antigravityBuildFlyout = function(acc) {
        if (!acc) return '<div style="padding:10px;font-size:12px;">No account selected</div>';
        const tier = acc.tier || 'PRO', email = acc.email || 'Account';
        let body = '';

        if (acc.quotas && acc.quotas.length > 0) {
            const gemini = acc.quotas.filter(q => q.family === 'gemini');
            const claude = acc.quotas.filter(q => q.family === 'claude');
            const other = acc.quotas.filter(q => q.family !== 'gemini' && q.family !== 'claude');
            let gh = '';
            if (gemini.length) gh += `<div class="agy-usage-group"><div class="agy-group-title">Gemini Models</div>${gemini.map(renderBucket).join('')}</div>`;
            if (claude.length) gh += `<div class="agy-usage-group" style="margin-top:6px;"><div class="agy-group-title">Claude and GPT models</div>${claude.map(renderBucket).join('')}</div>`;
            if (other.length) gh += `<div class="agy-usage-group" style="margin-top:6px;"><div class="agy-group-title">Other Models</div>${other.map(renderBucket).join('')}</div>`;
            body = gh + `<div class="agy-usage-note">Within each group, models share a weekly limit and a 5-hour limit.</div>`;
        } else if (acc.license_status === 'no_license') {
            body = `<div class="agy-usage-alert alert-warning"><div style="font-weight:600;margin-bottom:2px;">Subscription Required</div><div>This account does not have an active Gemini license.</div></div>`;
        } else if (acc.license_status === 'exhausted') {
            body = `<div class="agy-usage-alert alert-error"><div style="font-weight:600;margin-bottom:2px;">Resource Exhausted</div><div>5-Hour or weekly quota limit reached.</div></div>`;
        } else {
            body = `<div style="font-size:11px;color:var(--agy-dropdown-subtext);padding:8px 0;">Loading usage telemetry...</div>`;
        }

        return `
            <div class="agy-usage-flyout-header">
                <div><div class="agy-usage-title">Usage limits</div><div class="agy-usage-email-sub">${email}</div></div>
                <span class="agy-tier-badge">${tier.split(' ')[0]}</span>
            </div>
            ${body}
        `;
    };

    window.__antigravityShowFlyout = function(flyout, acc, dropdown, triggerEl) {
        if (!flyout) return;
        flyout.innerHTML = window.__antigravityBuildFlyout(acc);
        flyout.classList.add('visible');

        if (dropdown && triggerEl) {
            const ddRect = dropdown.getBoundingClientRect();
            const trRect = triggerEl.getBoundingClientRect();
            const topOffset = Math.max(0, trRect.top - ddRect.top - 20);
            flyout.style.top = `${topOffset}px`;

            if (ddRect.right + 330 > window.innerWidth) {
                flyout.style.left = 'auto'; flyout.style.right = 'calc(100% + 8px)';
            } else {
                flyout.style.left = 'calc(100% + 8px)'; flyout.style.right = 'auto';
            }
        }
    };
})();
