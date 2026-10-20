// ==============================================================================
// Antigravity Multi-Account UI Injector: Native Prompt Bar Account Selector
// Ultra-compact dropdown, hover "View Usage" flyout, accurate live quotas
// ==============================================================================

(function initMultiAccountUI() {
    if (window.__antigravityMultiAccountUIInitialized) return;
    window.__antigravityMultiAccountUIInitialized = true;

    console.log('[MultiAccountUI] Initializing native prompt bar account selector...');

    let cachedState = { accounts: [], bindings: {} };
    let currentCascadeId = 'default';
    let isRenderScheduled = false;

    // Inject styles matching Antigravity native input-footer model selector
    let styleEl = document.getElementById('antigravity-multi-account-styles');
    if (!styleEl) {
        styleEl = document.createElement('style');
        styleEl.id = 'antigravity-multi-account-styles';
        styleEl.textContent = `
            :root {
                --agy-pill-text: #4b5563;
                --agy-pill-text-hover: #111827;
                --agy-pill-hover-bg: rgba(0, 0, 0, 0.05);
                --agy-dropdown-bg: #ffffff;
                --agy-dropdown-border: #e5e7eb;
                --agy-dropdown-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
                --agy-dropdown-text: #1f2937;
                --agy-dropdown-subtext: #6b7280;
                --agy-dropdown-hover: #f3f4f6;
                --agy-dropdown-header: #4b5563;
                --agy-dropdown-selected: rgba(59, 130, 246, 0.08);
                --agy-quota-track: #e5e7eb;
                --agy-btn-action-bg: #f9fafb;
                --agy-btn-action-border: #d1d5db;
                --agy-btn-action-hover: #f3f4f6;
                --agy-btn-action-text: #374151;
            }
            html.dark, body.dark, [data-theme="dark"], .dark {
                --agy-pill-text: #9ca3af;
                --agy-pill-text-hover: #f3f4f6;
                --agy-pill-hover-bg: rgba(255, 255, 255, 0.08);
                --agy-dropdown-bg: #1e1f22;
                --agy-dropdown-border: rgba(255, 255, 255, 0.12);
                --agy-dropdown-shadow: 0 12px 30px rgba(0, 0, 0, 0.7);
                --agy-dropdown-text: #f3f4f6;
                --agy-dropdown-subtext: #9ca3af;
                --agy-dropdown-hover: rgba(255, 255, 255, 0.06);
                --agy-dropdown-header: #9ca3af;
                --agy-dropdown-selected: rgba(59, 130, 246, 0.18);
                --agy-quota-track: rgba(255, 255, 255, 0.12);
                --agy-btn-action-bg: rgba(255, 255, 255, 0.05);
                --agy-btn-action-border: rgba(255, 255, 255, 0.12);
                --agy-btn-action-hover: rgba(255, 255, 255, 0.1);
                --agy-btn-action-text: #e5e7eb;
            }
            @media (prefers-color-scheme: dark) {
                :root:not(.light) {
                    --agy-pill-text: #9ca3af;
                    --agy-pill-text-hover: #f3f4f6;
                    --agy-pill-hover-bg: rgba(255, 255, 255, 0.08);
                    --agy-dropdown-bg: #1e1f22;
                    --agy-dropdown-border: rgba(255, 255, 255, 0.12);
                    --agy-dropdown-shadow: 0 12px 30px rgba(0, 0, 0, 0.7);
                    --agy-dropdown-text: #f3f4f6;
                    --agy-dropdown-subtext: #9ca3af;
                    --agy-dropdown-hover: rgba(255, 255, 255, 0.06);
                    --agy-dropdown-header: #9ca3af;
                    --agy-dropdown-selected: rgba(59, 130, 246, 0.18);
                    --agy-quota-track: rgba(255, 255, 255, 0.12);
                    --agy-btn-action-bg: rgba(255, 255, 255, 0.05);
                    --agy-btn-action-border: rgba(255, 255, 255, 0.12);
                    --agy-btn-action-hover: rgba(255, 255, 255, 0.1);
                    --agy-btn-action-text: #e5e7eb;
                }
            }

            .agy-acc-pill-container {
                display: inline-flex;
                align-items: center;
                position: relative;
                margin-left: 2px;
                margin-right: 4px;
                font-family: inherit;
                z-index: 9999;
            }
            .agy-acc-pill-container.floating {
                position: fixed;
                bottom: 20px;
                right: 24px;
                z-index: 999999;
            }

            /* Flat compact button matching model selector */
            .agy-acc-pill-btn {
                display: inline-flex;
                align-items: center;
                gap: 5px;
                background: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 4px 8px;
                color: var(--agy-pill-text);
                font-size: 12px;
                font-weight: 500;
                cursor: pointer;
                transition: background 0.12s ease, color 0.12s ease;
                user-select: none;
                outline: none;
                height: 28px;
            }
            .agy-acc-pill-btn:hover {
                background: var(--agy-pill-hover-bg);
                color: var(--agy-pill-text-hover);
            }

            .agy-acc-avatar {
                width: 15px;
                height: 15px;
                border-radius: 50%;
                background: linear-gradient(135deg, #4285f4, #34a853);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 9px;
                font-weight: 700;
                color: #ffffff;
                flex-shrink: 0;
            }
            .agy-acc-badge {
                font-size: 12px;
                font-weight: 500;
                max-width: 130px;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
                color: inherit;
            }

            /* Compact Main Dropdown Menu */
            .agy-acc-dropdown {
                position: absolute;
                bottom: calc(100% + 6px);
                left: 0;
                width: 270px;
                background: var(--agy-dropdown-bg);
                border: 1px solid var(--agy-dropdown-border);
                border-radius: 8px;
                box-shadow: var(--agy-dropdown-shadow);
                padding: 4px 0;
                display: none;
                flex-direction: column;
                z-index: 100000;
                color: var(--agy-dropdown-text);
            }
            .agy-acc-dropdown.open {
                display: flex;
            }
            .agy-acc-header {
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                color: var(--agy-dropdown-header);
                border-bottom: 1px solid var(--agy-dropdown-border);
            }
            .agy-acc-list {
                max-height: 220px;
                overflow-y: auto;
            }
            .agy-acc-item {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 7px 12px;
                cursor: pointer;
                transition: background 0.12s ease;
                position: relative;
            }
            .agy-acc-item:hover {
                background: var(--agy-dropdown-hover);
            }
            .agy-acc-item.selected {
                background: var(--agy-dropdown-selected);
            }
            .agy-acc-item-left {
                display: flex;
                align-items: center;
                gap: 8px;
                min-width: 0;
                flex: 1;
            }
            .agy-acc-avatar-sm {
                width: 20px;
                height: 20px;
                border-radius: 50%;
                background: linear-gradient(135deg, #4285f4, #34a853);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 10px;
                font-weight: 700;
                color: #ffffff;
                flex-shrink: 0;
            }
            .agy-acc-text-col {
                display: flex;
                flex-direction: column;
                min-width: 0;
            }
            .agy-acc-email-text {
                font-size: 12px;
                font-weight: 500;
                color: var(--agy-dropdown-text);
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            .agy-acc-email-sub {
                font-size: 10px;
                color: var(--agy-dropdown-subtext);
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }

            .agy-view-usage-link {
                font-size: 11px;
                color: #3b82f6;
                padding: 2px 6px;
                border-radius: 4px;
                display: inline-flex;
                align-items: center;
                gap: 2px;
                opacity: 0.85;
                cursor: pointer;
                white-space: nowrap;
                flex-shrink: 0;
            }
            .agy-view-usage-link:hover {
                opacity: 1;
                background: rgba(59, 130, 246, 0.1);
            }

            /* "View Usage" Sub-Menu Flyout (Native Antigravity Usage Style) */
            .agy-usage-flyout {
                position: absolute;
                left: calc(100% + 6px);
                bottom: 0;
                width: 320px;
                background: var(--agy-dropdown-bg);
                border: 1px solid var(--agy-dropdown-border);
                border-radius: 8px;
                box-shadow: var(--agy-dropdown-shadow);
                padding: 12px 14px;
                display: none;
                flex-direction: column;
                gap: 10px;
                z-index: 100005;
                color: var(--agy-dropdown-text);
            }
            .agy-acc-item:hover .agy-usage-flyout,
            .agy-usage-flyout.visible {
                display: flex;
            }

            .agy-usage-flyout-header {
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                border-bottom: 1px solid var(--agy-dropdown-border);
                padding-bottom: 8px;
            }
            .agy-usage-title {
                font-size: 13px;
                font-weight: 600;
                color: var(--agy-dropdown-text);
            }
            .agy-usage-email-sub {
                font-size: 11px;
                color: var(--agy-dropdown-subtext);
            }
            .agy-tier-badge {
                font-size: 10px;
                font-weight: 600;
                padding: 2px 6px;
                border-radius: 4px;
                background: rgba(59, 130, 246, 0.12);
                color: #3b82f6;
                white-space: nowrap;
            }

            .agy-usage-group {
                display: flex;
                flex-direction: column;
                gap: 6px;
            }
            .agy-group-title {
                font-size: 11px;
                font-weight: 600;
                color: var(--agy-dropdown-header);
                text-transform: uppercase;
                letter-spacing: 0.4px;
            }
            .agy-bucket-box {
                display: flex;
                flex-direction: column;
                gap: 3px;
            }
            .agy-bucket-meta {
                display: flex;
                justify-content: space-between;
                font-size: 11px;
                color: var(--agy-dropdown-text);
            }
            .agy-bucket-bar-track {
                width: 100%;
                height: 4px;
                background: var(--agy-quota-track);
                border-radius: 2px;
                overflow: hidden;
            }
            .agy-bucket-bar-fill {
                height: 100%;
                border-radius: 2px;
                transition: width 0.3s ease;
            }
            .agy-bucket-reset {
                font-size: 10px;
                color: var(--agy-dropdown-subtext);
            }

            .agy-usage-alert {
                padding: 8px 10px;
                border-radius: 6px;
                font-size: 11px;
                line-height: 1.4;
            }
            .agy-usage-alert.alert-warning {
                background: rgba(245, 158, 11, 0.1);
                border: 1px solid rgba(245, 158, 11, 0.25);
                color: #d97706;
            }
            .agy-usage-alert.alert-error {
                background: rgba(239, 68, 68, 0.1);
                border: 1px solid rgba(239, 68, 68, 0.25);
                color: #dc2626;
            }

            .agy-usage-note {
                font-size: 10px;
                color: var(--agy-dropdown-subtext);
                border-top: 1px solid var(--agy-dropdown-border);
                padding-top: 6px;
                line-height: 1.3;
            }

            .agy-acc-footer {
                padding: 6px 10px;
                border-top: 1px solid var(--agy-dropdown-border);
                display: flex;
                gap: 6px;
            }
            .agy-acc-btn-action {
                flex: 1;
                padding: 4px 8px;
                background: var(--agy-btn-action-bg);
                border: 1px solid var(--agy-btn-action-border);
                border-radius: 6px;
                color: var(--agy-btn-action-text);
                font-size: 11px;
                font-weight: 500;
                cursor: pointer;
                text-align: center;
            }
            .agy-acc-btn-action:hover {
                background: var(--agy-btn-action-hover);
            }

            .agy-toast {
                position: fixed;
                bottom: 68px;
                right: 24px;
                background: rgba(24, 24, 27, 0.92);
                color: #ffffff;
                font-size: 12px;
                padding: 6px 14px;
                border-radius: 6px;
                border: 1px solid rgba(255, 255, 255, 0.15);
                box-shadow: 0 4px 14px rgba(0, 0, 0, 0.3);
                z-index: 9999999;
                pointer-events: none;
                transition: opacity 0.25s ease;
            }
        `;
        document.head.appendChild(styleEl);
    }

    function showToast(msg) {
        let t = document.getElementById('antigravity-account-toast');
        if (!t) {
            t = document.createElement('div');
            t.id = 'antigravity-account-toast';
            t.className = 'agy-toast';
            document.body.appendChild(t);
        }
        t.textContent = msg;
        t.style.opacity = '1';
        setTimeout(() => { if (t) t.style.opacity = '0'; }, 2400);
    }

    function detectCurrentCascadeId() {
        const hashMatch = window.location.hash.match(/[a-f0-9-]{16,}/i);
        if (hashMatch) return hashMatch[0];
        const pathMatch = window.location.pathname.match(/[a-f0-9-]{16,}/i);
        if (pathMatch) return pathMatch[0];
        return 'default';
    }

    async function fetchState() {
        if (window.antigravityMultiAccount?.getState) {
            try {
                cachedState = await window.antigravityMultiAccount.getState();
                scheduleRender();
            } catch (err) {
                console.error('[MultiAccountUI] State fetch error:', err);
            }
        }
    }

    function getActiveAccount() {
        const email = cachedState.bindings?.[currentCascadeId] || cachedState.active_default;
        if (email && cachedState.accounts) {
            const found = cachedState.accounts.find(a => a.email && a.email.toLowerCase() === email.toLowerCase());
            if (found) return found;
        }
        return (cachedState.accounts && cachedState.accounts[0]) || { email: 'Default Account', quotas: [] };
    }

    function findAttachmentTarget() {
        // Priority 1: Inside input-footer container
        const footers = document.querySelectorAll('div[class*="input-footer"]');
        for (const footer of footers) {
            const group = footer.querySelector('div[class*="items-center"][class*="min-w-0"]') ||
                          footer.querySelector('div[class*="flex-1"]') ||
                          footer;
            if (group) return { target: group, floating: false };
        }
        // Priority 2: Next to model selector button
        const buttons = document.querySelectorAll('button');
        for (const btn of buttons) {
            const txt = btn.textContent || '';
            if (txt.includes('Flash') || txt.includes('Pro') || txt.includes('Claude') || txt.includes('Gemini') || txt.includes('Sonnet')) {
                if (btn.parentElement) return { target: btn.parentElement, floating: false };
            }
        }
        return { target: document.body, floating: true };
    }

    function scheduleRender() {
        if (isRenderScheduled) return;
        isRenderScheduled = true;
        requestAnimationFrame(() => {
            isRenderScheduled = false;
            renderPill();
        });
    }

    function getBarColor(pct) {
        if (pct >= 50) return '#34a853';
        if (pct >= 20) return '#fbbc04';
        return '#ea4335';
    }

    function buildUsageFlyout(acc) {
        const tier = acc.tier || 'TEAMS_TIER_PRO';
        let contentHtml = '';

        if (acc.license_status === 'no_license') {
            contentHtml = `
                <div class="agy-usage-alert alert-warning">
                    <div style="font-weight:600;margin-bottom:2px;">Subscription Required</div>
                    <div>This account does not have an active Gemini Code Assist license.</div>
                </div>
            `;
        } else if (acc.license_status === 'exhausted') {
            contentHtml = `
                <div class="agy-usage-alert alert-error">
                    <div style="font-weight:600;margin-bottom:2px;">Resource Exhausted</div>
                    <div>Hourly or weekly limits have been reached for this account.</div>
                </div>
            `;
        } else if (acc.quotas && acc.quotas.length > 0) {
            const gWeekly = acc.quotas.find(q => q.family === 'gemini' && q.window === 'weekly') || { percent: 100 };
            const g5h = acc.quotas.find(q => q.family === 'gemini' && q.window === '5h') || { percent: 100 };
            const cWeekly = acc.quotas.find(q => q.family === 'claude' && q.window === 'weekly') || { percent: 100 };
            const c5h = acc.quotas.find(q => q.family === 'claude' && q.window === '5h') || { percent: 100 };

            contentHtml = `
                <div class="agy-usage-group">
                    <div class="agy-group-title">Gemini Models</div>
                    <div class="agy-bucket-box">
                        <div class="agy-bucket-meta">
                            <span>Weekly Limit Remaining</span>
                            <span style="font-weight:600;color:${getBarColor(gWeekly.percent)}">${gWeekly.percent}%</span>
                        </div>
                        <div class="agy-bucket-bar-track">
                            <div class="agy-bucket-bar-fill" style="width:${gWeekly.percent}%;background:${getBarColor(gWeekly.percent)}"></div>
                        </div>
                        ${gWeekly.description ? `<div class="agy-bucket-reset">${gWeekly.description}</div>` : ''}
                    </div>
                    <div class="agy-bucket-box" style="margin-top:4px;">
                        <div class="agy-bucket-meta">
                            <span>Five Hour Limit Remaining</span>
                            <span style="font-weight:600;color:${getBarColor(g5h.percent)}">${g5h.percent}%</span>
                        </div>
                        <div class="agy-bucket-bar-track">
                            <div class="agy-bucket-bar-fill" style="width:${g5h.percent}%;background:${getBarColor(g5h.percent)}"></div>
                        </div>
                    </div>
                </div>
                <div class="agy-usage-group" style="margin-top:6px;">
                    <div class="agy-group-title">Claude and GPT models</div>
                    <div class="agy-bucket-box">
                        <div class="agy-bucket-meta">
                            <span>Weekly Limit Remaining</span>
                            <span style="font-weight:600;color:${getBarColor(cWeekly.percent)}">${cWeekly.percent}%</span>
                        </div>
                        <div class="agy-bucket-bar-track">
                            <div class="agy-bucket-bar-fill" style="width:${cWeekly.percent}%;background:${getBarColor(cWeekly.percent)}"></div>
                        </div>
                    </div>
                    <div class="agy-bucket-box" style="margin-top:4px;">
                        <div class="agy-bucket-meta">
                            <span>Five Hour Limit Remaining</span>
                            <span style="font-weight:600;color:${getBarColor(c5h.percent)}">${c5h.percent}%</span>
                        </div>
                        <div class="agy-bucket-bar-track">
                            <div class="agy-bucket-bar-fill" style="width:${c5h.percent}%;background:${getBarColor(c5h.percent)}"></div>
                        </div>
                    </div>
                </div>
                <div class="agy-usage-note">
                    Within each group, models share a weekly limit and a 5-hour limit.
                </div>
            `;
        } else {
            contentHtml = `
                <div style="font-size:11px;color:var(--agy-dropdown-subtext);padding:8px 0;">
                    Loading live usage limits...
                </div>
            `;
        }

        return `
            <div class="agy-usage-flyout" id="flyout-${acc.email.replace(/[^a-zA-Z0-9]/g, '')}">
                <div class="agy-usage-flyout-header">
                    <div>
                        <div class="agy-usage-title">Usage limits</div>
                        <div class="agy-usage-email-sub">${acc.email}</div>
                    </div>
                    <span class="agy-tier-badge">${tier.split(' ')[0]}</span>
                </div>
                ${contentHtml}
            </div>
        `;
    }

    function renderPill() {
        currentCascadeId = detectCurrentCascadeId();
        const active = getActiveAccount();
        const { target, floating } = findAttachmentTarget();
        if (!target) return;

        let pillContainer = document.getElementById('antigravity-account-pill');
        if (!pillContainer) {
            pillContainer = document.createElement('div');
            pillContainer.id = 'antigravity-account-pill';
            target.appendChild(pillContainer);
        } else if (pillContainer.parentElement !== target) {
            target.appendChild(pillContainer);
        }

        const initial = (active.name || active.email || 'G')[0].toUpperCase();
        const renderKey = `${active.email}|${currentCascadeId}|${(cachedState.accounts || []).length}|${floating}`;
        if (pillContainer.__renderKey === renderKey) {
            return;
        }
        pillContainer.__renderKey = renderKey;

        pillContainer.className = 'agy-acc-pill-container' + (floating ? ' floating' : '');

        // Flat button: avatar + handle + chevron (no bulky badges, perfectly flush)
        pillContainer.innerHTML = `
            <button class="agy-acc-pill-btn" type="button" id="agy-acc-toggle-btn" title="Account: ${active.email}">
                <div class="agy-acc-avatar">${initial}</div>
                <span class="agy-acc-badge">${active.email.split('@')[0]}</span>
                <span style="font-size:8px;opacity:0.6;margin-left:1px;">▼</span>
            </button>
            <div class="agy-acc-dropdown" id="agy-acc-dropdown">
                <div class="agy-acc-header">Google Accounts</div>
                <div class="agy-acc-list">
                    ${(cachedState.accounts || []).map(acc => {
                        const isSel = acc.email && acc.email.toLowerCase() === active.email.toLowerCase();
                        const accInitial = (acc.name || acc.email || 'G')[0].toUpperCase();
                        return `
                            <div class="agy-acc-item ${isSel ? 'selected' : ''}" data-email="${acc.email}">
                                <div class="agy-acc-item-left">
                                    <div class="agy-acc-avatar-sm">${accInitial}</div>
                                    <div class="agy-acc-text-col">
                                        <span class="agy-acc-email-text">${acc.email.split('@')[0]}</span>
                                        <span class="agy-acc-email-sub">${acc.email}</span>
                                    </div>
                                    ${isSel ? '<span style="color:#3b82f6;font-size:11px;font-weight:bold;margin-left:2px;">✓</span>' : ''}
                                </div>
                                <span class="agy-view-usage-link">View usage ›</span>
                                ${buildUsageFlyout(acc)}
                            </div>
                        `;
                    }).join('')}
                </div>
                <div class="agy-acc-footer">
                    <button class="agy-acc-btn-action" id="agy-acc-add-btn">+ Add Account</button>
                    <button class="agy-acc-btn-action" id="agy-acc-refresh-btn">Refresh Limits</button>
                </div>
            </div>
        `;

        // Toggle dropdown
        const btn = document.getElementById('agy-acc-toggle-btn');
        const dropdown = document.getElementById('agy-acc-dropdown');
        if (btn && dropdown) {
            btn.onclick = (e) => {
                e.stopPropagation();
                dropdown.classList.toggle('open');
            };
        }

        // Account selection
        pillContainer.querySelectorAll('.agy-acc-item').forEach(item => {
            item.onclick = async (e) => {
                if (e.target.closest('.agy-usage-flyout') || e.target.closest('.agy-view-usage-link')) {
                    return; // Don't switch if clicking the flyout itself
                }
                e.stopPropagation();
                const email = item.getAttribute('data-email');
                if (email && window.antigravityMultiAccount?.bindCascade) {
                    await window.antigravityMultiAccount.bindCascade(currentCascadeId, email);
                    if (!cachedState.bindings) cachedState.bindings = {};
                    cachedState.bindings[currentCascadeId] = email;
                    pillContainer.__renderKey = null;
                    scheduleRender();
                    showToast(`✓ Switched chat to ${email}`);
                }
                dropdown.classList.remove('open');
            };
        });

        // Add Account
        const addBtn = document.getElementById('agy-acc-add-btn');
        if (addBtn) {
            addBtn.onclick = async (e) => {
                e.stopPropagation();
                if (window.antigravityMultiAccount?.startLogin) {
                    await window.antigravityMultiAccount.startLogin();
                    await fetchState();
                }
            };
        }

        // Refresh
        const refBtn = document.getElementById('agy-acc-refresh-btn');
        if (refBtn) {
            refBtn.onclick = async (e) => {
                e.stopPropagation();
                await fetchState();
                showToast('Usage limits refreshed');
            };
        }
    }

    // Close on outside click
    document.addEventListener('click', () => {
        const dd = document.getElementById('agy-acc-dropdown');
        if (dd) dd.classList.remove('open');
    });

    // Debounced observer
    let debounceTimer = null;
    const observer = new MutationObserver((mutations) => {
        let shouldCheck = false;
        for (const m of mutations) {
            if (m.target && m.target.closest && m.target.closest('#antigravity-account-pill')) {
                continue;
            }
            if (m.type === 'childList') {
                shouldCheck = true;
                break;
            }
        }
        if (shouldCheck) {
            if (debounceTimer) clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                scheduleRender();
            }, 150);
        }
    });

    observer.observe(document.body, { childList: true, subtree: true });

    fetchState();
    setInterval(fetchState, 30000);
})();
