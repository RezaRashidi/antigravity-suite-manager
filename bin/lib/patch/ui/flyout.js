// Antigravity Multi-Account UI: Flyout Template and Positioning
(function initFlyoutModule() {
    function getBarColor(pct) {
        if (pct >= 50) return '#34a853';
        if (pct >= 20) return '#fbbc04';
        return '#ea4335';
    }

    function renderBucket(title, item) {
        const pct = item?.percent ?? 100;
        const color = getBarColor(pct);
        return `
            <div class="agy-bucket-box">
                <div class="agy-bucket-meta"><span>${title}</span><span style="font-weight:600;color:${color}">${pct}%</span></div>
                <div class="agy-bucket-bar-track"><div class="agy-bucket-bar-fill" style="width:${pct}%;background:${color}"></div></div>
                ${item?.description ? `<div class="agy-bucket-reset">${item.description}</div>` : ''}
            </div>
        `;
    }

    window.__antigravityBuildFlyout = function(acc) {
        if (!acc) return '<div style="padding:10px;font-size:12px;">No account selected</div>';
        const tier = acc.tier || 'TEAMS_TIER_PRO';
        const email = acc.email || 'Account';
        let body = '';

        if (acc.quotas && acc.quotas.length > 0) {
            const gW = acc.quotas.find(q => q.family === 'gemini' && q.window === 'weekly');
            const g5 = acc.quotas.find(q => q.family === 'gemini' && q.window === '5h');
            const cW = acc.quotas.find(q => q.family === 'claude' && q.window === 'weekly');
            const c5 = acc.quotas.find(q => q.family === 'claude' && q.window === '5h');
            body = `
                <div class="agy-usage-group"><div class="agy-group-title">Gemini Models</div>
                    ${renderBucket('Weekly Limit Remaining', gW)}
                    <div style="margin-top:4px;">${renderBucket('Five Hour Limit Remaining', g5)}</div>
                </div>
                <div class="agy-usage-group" style="margin-top:6px;"><div class="agy-group-title">Claude and GPT models</div>
                    ${renderBucket('Weekly Limit Remaining', cW)}
                    <div style="margin-top:4px;">${renderBucket('Five Hour Limit Remaining', c5)}</div>
                </div>
                <div class="agy-usage-note">Within each group, models share a weekly limit and a 5-hour limit.</div>
            `;
        } else if (acc.license_status === 'no_license') {
            body = `<div class="agy-usage-alert alert-warning"><div style="font-weight:600;margin-bottom:2px;">Subscription Required</div><div>This account does not have an active Gemini Code Assist license.</div></div>`;
        } else if (acc.license_status === 'exhausted') {
            body = `<div class="agy-usage-alert alert-error"><div style="font-weight:600;margin-bottom:2px;">Resource Exhausted</div><div>Hourly or weekly limits have been reached for this account.</div></div>`;
        } else {
            body = `<div style="font-size:11px;color:var(--agy-dropdown-subtext);padding:8px 0;">Loading live usage limits...</div>`;
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

            if (ddRect.right + 340 > window.innerWidth) {
                flyout.style.left = 'auto';
                flyout.style.right = 'calc(100% + 8px)';
            } else {
                flyout.style.left = 'calc(100% + 8px)';
                flyout.style.right = 'auto';
            }
        }
    };
})();
