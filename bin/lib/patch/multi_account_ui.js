// ==============================================================================
// Antigravity Multi-Account UI Injector: Prompt Bar Pill & Account Selector
// High-performance, debounced, light & dark theme adaptive
// ==============================================================================

(function initMultiAccountUI() {
    if (window.__antigravityMultiAccountUIInitialized) return;
    window.__antigravityMultiAccountUIInitialized = true;

    console.log('[MultiAccountUI] Initializing prompt bar account selector...');

    let cachedState = { accounts: [], bindings: {} };
    let currentCascadeId = 'default';
    let isRenderScheduled = false;

    // Inject styles
    let styleEl = document.getElementById('antigravity-multi-account-styles');
    if (!styleEl) {
        styleEl = document.createElement('style');
        styleEl.id = 'antigravity-multi-account-styles';
        styleEl.textContent = `
            :root {
                --agy-pill-bg: rgba(0, 0, 0, 0.05);
                --agy-pill-border: rgba(0, 0, 0, 0.14);
                --agy-pill-text: #202124;
                --agy-pill-hover: rgba(0, 0, 0, 0.09);
                --agy-dropdown-bg: #ffffff;
                --agy-dropdown-border: rgba(0, 0, 0, 0.14);
                --agy-dropdown-shadow: 0 10px 28px rgba(0, 0, 0, 0.15);
                --agy-dropdown-text: #202124;
                --agy-dropdown-subtext: #5f6368;
                --agy-dropdown-hover: rgba(0, 0, 0, 0.05);
                --agy-dropdown-header: #5f6368;
                --agy-dropdown-selected: rgba(66, 133, 244, 0.12);
                --agy-quota-badge-bg: rgba(0, 0, 0, 0.06);
                --agy-quota-gemini: #1a73e8;
                --agy-quota-claude: #d93025;
                --agy-btn-action-bg: rgba(0, 0, 0, 0.04);
                --agy-btn-action-border: rgba(0, 0, 0, 0.12);
                --agy-btn-action-hover: rgba(0, 0, 0, 0.08);
                --agy-btn-action-text: #3c4043;
            }
            html.dark, body.dark, [data-theme="dark"], .dark {
                --agy-pill-bg: rgba(255, 255, 255, 0.08);
                --agy-pill-border: rgba(255, 255, 255, 0.16);
                --agy-pill-text: #e0e0e0;
                --agy-pill-hover: rgba(255, 255, 255, 0.15);
                --agy-dropdown-bg: #1e1f22;
                --agy-dropdown-border: rgba(255, 255, 255, 0.18);
                --agy-dropdown-shadow: 0 10px 28px rgba(0, 0, 0, 0.75);
                --agy-dropdown-text: #e0e0e0;
                --agy-dropdown-subtext: #9aa0a6;
                --agy-dropdown-hover: rgba(255, 255, 255, 0.08);
                --agy-dropdown-header: #9aa0a6;
                --agy-dropdown-selected: rgba(66, 133, 244, 0.22);
                --agy-quota-badge-bg: rgba(0, 0, 0, 0.4);
                --agy-quota-gemini: #8ab4f8;
                --agy-quota-claude: #f28b82;
                --agy-btn-action-bg: rgba(255, 255, 255, 0.07);
                --agy-btn-action-border: rgba(255, 255, 255, 0.14);
                --agy-btn-action-hover: rgba(255, 255, 255, 0.15);
                --agy-btn-action-text: #e0e0e0;
            }
            @media (prefers-color-scheme: dark) {
                :root:not(.light) {
                    --agy-pill-bg: rgba(255, 255, 255, 0.08);
                    --agy-pill-border: rgba(255, 255, 255, 0.16);
                    --agy-pill-text: #e0e0e0;
                    --agy-pill-hover: rgba(255, 255, 255, 0.15);
                    --agy-dropdown-bg: #1e1f22;
                    --agy-dropdown-border: rgba(255, 255, 255, 0.18);
                    --agy-dropdown-shadow: 0 10px 28px rgba(0, 0, 0, 0.75);
                    --agy-dropdown-text: #e0e0e0;
                    --agy-dropdown-subtext: #9aa0a6;
                    --agy-dropdown-hover: rgba(255, 255, 255, 0.08);
                    --agy-dropdown-header: #9aa0a6;
                    --agy-dropdown-selected: rgba(66, 133, 244, 0.22);
                    --agy-quota-badge-bg: rgba(0, 0, 0, 0.4);
                    --agy-quota-gemini: #8ab4f8;
                    --agy-quota-claude: #f28b82;
                    --agy-btn-action-bg: rgba(255, 255, 255, 0.07);
                    --agy-btn-action-border: rgba(255, 255, 255, 0.14);
                    --agy-btn-action-hover: rgba(255, 255, 255, 0.15);
                    --agy-btn-action-text: #e0e0e0;
                }
            }

            .agy-acc-pill-container {
                display: inline-flex;
                align-items: center;
                position: relative;
                margin-left: 4px;
                margin-right: 4px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                z-index: 9999;
            }
            .agy-acc-pill-container.floating {
                position: fixed;
                bottom: 20px;
                right: 24px;
                z-index: 999999;
                box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
            }
            .agy-acc-pill-btn {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                background: var(--agy-pill-bg);
                border: 1px solid var(--agy-pill-border);
                border-radius: 14px;
                padding: 3px 10px;
                color: var(--agy-pill-text);
                font-size: 12px;
                cursor: pointer;
                transition: all 0.15s ease;
                user-select: none;
                outline: none;
                backdrop-filter: blur(8px);
            }
            .agy-acc-pill-btn:hover {
                background: var(--agy-pill-hover);
                color: var(--agy-pill-text);
            }
            .agy-acc-avatar {
                width: 16px;
                height: 16px;
                border-radius: 50%;
                background: linear-gradient(135deg, #4285f4, #34a853);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 10px;
                font-weight: bold;
                color: #ffffff;
            }
            .agy-acc-badge {
                font-size: 11px;
                font-weight: 500;
                max-width: 120px;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
                color: var(--agy-pill-text);
            }
            .agy-quota-badge {
                background: var(--agy-quota-badge-bg);
                padding: 1px 6px;
                border-radius: 8px;
                font-size: 10px;
                font-weight: 600;
            }
            .agy-quota-gemini { color: var(--agy-quota-gemini); }
            .agy-quota-claude { color: var(--agy-quota-claude); }

            .agy-acc-dropdown {
                position: absolute;
                bottom: calc(100% + 8px);
                left: 0;
                min-width: 310px;
                background: var(--agy-dropdown-bg);
                border: 1px solid var(--agy-dropdown-border);
                border-radius: 10px;
                box-shadow: var(--agy-dropdown-shadow);
                padding: 8px 0;
                display: none;
                flex-direction: column;
                z-index: 100000;
                color: var(--agy-dropdown-text);
            }
            .agy-acc-dropdown.open {
                display: flex;
            }
            .agy-acc-header {
                padding: 8px 14px 6px;
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                color: var(--agy-dropdown-header);
                border-bottom: 1px solid var(--agy-dropdown-border);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .agy-acc-item {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 8px 14px;
                cursor: pointer;
                transition: background 0.15s ease;
            }
            .agy-acc-item:hover {
                background: var(--agy-dropdown-hover);
            }
            .agy-acc-item.selected {
                background: var(--agy-dropdown-selected);
                border-left: 3px solid #4285f4;
            }
            .agy-acc-item-left {
                display: flex;
                flex-direction: column;
                gap: 2px;
            }
            .agy-acc-item-email {
                font-size: 12px;
                font-weight: 500;
                color: var(--agy-dropdown-text);
            }
            .agy-acc-item-sub {
                font-size: 10px;
                color: var(--agy-dropdown-subtext);
            }
            .agy-acc-item-right {
                display: flex;
                flex-direction: column;
                align-items: flex-end;
                gap: 2px;
            }
            .agy-acc-footer {
                padding: 8px 10px 4px;
                border-top: 1px solid var(--agy-dropdown-border);
                display: flex;
                gap: 6px;
            }
            .agy-acc-btn-action {
                flex: 1;
                padding: 5px 8px;
                background: var(--agy-btn-action-bg);
                border: 1px solid var(--agy-btn-action-border);
                border-radius: 6px;
                color: var(--agy-btn-action-text);
                font-size: 11px;
                cursor: pointer;
                text-align: center;
            }
            .agy-acc-btn-action:hover {
                background: var(--agy-btn-action-hover);
            }
        `;
        document.head.appendChild(styleEl);
    }

    function isDarkTheme() {
        if (document.documentElement.classList.contains('dark') || document.body.classList.contains('dark')) return true;
        if (document.documentElement.getAttribute('data-theme') === 'dark') return true;
        try {
            const bg = window.getComputedStyle(document.body).backgroundColor;
            const rgb = bg.match(/\d+/g);
            if (rgb && rgb.length >= 3) {
                const brightness = (Number(rgb[0]) * 299 + Number(rgb[1]) * 587 + Number(rgb[2]) * 114) / 1000;
                return brightness < 128;
            }
        } catch (_) {}
        return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
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
        // Fallback: floating container
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
        let quotaText = '';
        if (active.quotas && active.quotas.length > 0) {
            const gQ = active.quotas.find(q => q.family === 'gemini');
            const cQ = active.quotas.find(q => q.family === 'claude');
            const gVal = gQ ? `${Math.round(gQ.fraction * 100)}%` : '100%';
            const cVal = cQ ? `${Math.round(cQ.fraction * 100)}%` : '100%';
            quotaText = `<span class="agy-quota-badge agy-quota-gemini">G:${gVal}</span><span class="agy-quota-badge agy-quota-claude">3P:${cVal}</span>`;
        } else {
            quotaText = `<span class="agy-quota-badge agy-quota-gemini">Ready</span>`;
        }

        const dark = isDarkTheme();
        const renderKey = `${active.email}|${active.tier}|${quotaText}|${currentCascadeId}|${(cachedState.accounts || []).length}|${floating}|${dark}`;
        if (pillContainer.__renderKey === renderKey) {
            return;
        }
        pillContainer.__renderKey = renderKey;

        pillContainer.className = 'agy-acc-pill-container' + (floating ? ' floating' : '') + (dark ? ' dark' : '');

        pillContainer.innerHTML = `
            <button class="agy-acc-pill-btn" type="button" id="agy-acc-toggle-btn" title="Antigravity Account Selector & Quota Telemetry">
                <div class="agy-acc-avatar">${initial}</div>
                <span class="agy-acc-badge">${active.email.split('@')[0]}</span>
                ${quotaText}
                <span style="font-size:9px;opacity:0.7;">▼</span>
            </button>
            <div class="agy-acc-dropdown" id="agy-acc-dropdown">
                <div class="agy-acc-header">
                    <span>Google Accounts</span>
                    <span style="font-size:9px;color:var(--agy-quota-gemini);">${active.tier || ''}</span>
                </div>
                <div class="agy-acc-list">
                    ${(cachedState.accounts || []).map(acc => {
                        const isSel = acc.email && acc.email.toLowerCase() === active.email.toLowerCase();
                        const gQ = (acc.quotas || []).find(q => q.family === 'gemini');
                        const cQ = (acc.quotas || []).find(q => q.family === 'claude');
                        const gStr = gQ ? `G: ${Math.round(gQ.fraction * 100)}%` : 'G: 100%';
                        const cStr = cQ ? `3P: ${Math.round(cQ.fraction * 100)}%` : '3P: 100%';
                        return `
                            <div class="agy-acc-item ${isSel ? 'selected' : ''}" data-email="${acc.email}">
                                <div class="agy-acc-item-left">
                                    <div class="agy-acc-item-email">${acc.email} ${acc.is_primary ? '(Primary)' : ''}</div>
                                    <div class="agy-acc-item-sub">${acc.name || ''}</div>
                                </div>
                                <div class="agy-acc-item-right">
                                    <span class="agy-quota-gemini" style="font-size:10px;font-weight:bold;">${gStr}</span>
                                    <span class="agy-quota-claude" style="font-size:10px;font-weight:bold;">${cStr}</span>
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>
                <div class="agy-acc-footer">
                    <button class="agy-acc-btn-action" id="agy-acc-add-btn">+ Add Account</button>
                    <button class="agy-acc-btn-action" id="agy-acc-refresh-btn">Refresh</button>
                </div>
            </div>
        `;

        // Dropdown toggle
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
                e.stopPropagation();
                const email = item.getAttribute('data-email');
                if (email && window.antigravityMultiAccount?.bindCascade) {
                    await window.antigravityMultiAccount.bindCascade(currentCascadeId, email);
                    if (!cachedState.bindings) cachedState.bindings = {};
                    cachedState.bindings[currentCascadeId] = email;
                    pillContainer.__renderKey = null;
                    scheduleRender();
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
            };
        }
    }

    // Close dropdown on outside click
    document.addEventListener('click', () => {
        const dd = document.getElementById('agy-acc-dropdown');
        if (dd) dd.classList.remove('open');
    });

    // Observer: only trigger when target area or root classes change, debounced
    let debounceTimer = null;
    const observer = new MutationObserver((mutations) => {
        let shouldCheck = false;
        for (const m of mutations) {
            // Ignore mutations within the pill itself to eliminate infinite loops!
            if (m.target && m.target.closest && m.target.closest('#antigravity-account-pill')) {
                continue;
            }
            if (m.type === 'attributes' && (m.attributeName === 'class' || m.attributeName === 'data-theme')) {
                shouldCheck = true;
                break;
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

    observer.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['class', 'data-theme'] });

    // Initial state fetch
    fetchState();
    setInterval(fetchState, 30000);
})();
