// ==============================================================================
// Antigravity Multi-Account UI Injector: Prompt Bar Pill & Account Selector
// ==============================================================================

(function initMultiAccountUI() {
    if (window.__antigravityMultiAccountUIInitialized) return;
    window.__antigravityMultiAccountUIInitialized = true;

    console.log('[MultiAccountUI] Initializing prompt bar account selector...');

    let cachedState = { accounts: [], bindings: {} };
    let currentCascadeId = 'default';

    // Inject CSS styles for pill and dropdown
    const styleEl = document.createElement('style');
    styleEl.id = 'antigravity-multi-account-styles';
    styleEl.textContent = `
        .agy-acc-pill-container {
            display: inline-flex;
            align-items: center;
            position: relative;
            margin-left: 6px;
            margin-right: 6px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            z-index: 9999;
        }
        .agy-acc-pill-btn {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(255, 255, 255, 0.07);
            border: 1px solid rgba(255, 255, 255, 0.14);
            border-radius: 14px;
            padding: 3px 10px;
            color: #e0e0e0;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.15s ease;
            user-select: none;
            outline: none;
        }
        .agy-acc-pill-btn:hover {
            background: rgba(255, 255, 255, 0.13);
            border-color: rgba(255, 255, 255, 0.28);
            color: #ffffff;
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
            max-width: 110px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .agy-quota-badge {
            background: rgba(0, 0, 0, 0.35);
            padding: 1px 5px;
            border-radius: 8px;
            font-size: 10px;
            font-weight: 600;
        }
        .agy-quota-gemini { color: #8ab4f8; }
        .agy-quota-claude { color: #f28b82; }

        .agy-acc-dropdown {
            position: absolute;
            bottom: calc(100% + 8px);
            left: 0;
            min-width: 310px;
            background: #1e1f22;
            border: 1px solid rgba(255, 255, 255, 0.16);
            border-radius: 10px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.65);
            padding: 8px 0;
            display: none;
            flex-direction: column;
            z-index: 100000;
            color: #e0e0e0;
        }
        .agy-acc-dropdown.open {
            display: flex;
        }
        .agy-acc-header {
            padding: 6px 14px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #9aa0a6;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
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
            background: rgba(255, 255, 255, 0.08);
        }
        .agy-acc-item.selected {
            background: rgba(66, 133, 244, 0.15);
        }
        .agy-acc-item-left {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }
        .agy-acc-item-email {
            font-size: 12px;
            font-weight: 500;
            color: #fff;
        }
        .agy-acc-item-sub {
            font-size: 10px;
            color: #9aa0a6;
        }
        .agy-acc-item-right {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: 2px;
        }
        .agy-acc-footer {
            padding: 6px 10px 2px 10px;
            border-top: 1px solid rgba(255, 255, 255, 0.08);
            display: flex;
            gap: 6px;
        }
        .agy-acc-btn-action {
            flex: 1;
            padding: 5px 8px;
            background: rgba(255, 255, 255, 0.07);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 6px;
            color: #e0e0e0;
            font-size: 11px;
            cursor: pointer;
            text-align: center;
        }
        .agy-acc-btn-action:hover {
            background: rgba(255, 255, 255, 0.14);
            color: #fff;
        }
    `;
    document.head.appendChild(styleEl);

    function detectCurrentCascadeId() {
        // Attempt detection from URL or hash
        const hashMatch = window.location.hash.match(/[a-f0-9-]{16,}/i);
        if (hashMatch) return hashMatch[0];
        const pathMatch = window.location.pathname.match(/[a-f0-9-]{16,}/i);
        if (pathMatch) return pathMatch[0];
        return 'default';
    }

    async function fetchState() {
        if (window.antigravityMultiAccount && window.antigravityMultiAccount.getState) {
            try {
                cachedState = await window.antigravityMultiAccount.getState();
                renderPill();
            } catch (err) {
                console.error('[MultiAccountUI] State fetch error:', err);
            }
        }
    }

    function getActiveAccount() {
        const email = cachedState.bindings[currentCascadeId] || cachedState.active_default;
        if (email && cachedState.accounts) {
            const found = cachedState.accounts.find(a => a.email.toLowerCase() === email.toLowerCase());
            if (found) return found;
        }
        return (cachedState.accounts && cachedState.accounts[0]) || { email: 'Default Account', quotas: [] };
    }

    function renderPill() {
        currentCascadeId = detectCurrentCascadeId();
        const active = getActiveAccount();

        let pillContainer = document.getElementById('antigravity-account-pill');
        if (!pillContainer) {
            // Find insertion point near model selector or toolbar
            const toolbar = document.querySelector('[data-testid="model-selector"]')?.parentElement ||
                            document.querySelector('.Fkc')?.parentElement ||
                            document.querySelector('.a4b')?.parentElement ||
                            document.querySelector('form div[role="toolbar"]') ||
                            document.querySelector('.chat-input-toolbar');

            if (!toolbar) return; // Wait for toolbar to mount

            pillContainer = document.createElement('div');
            pillContainer.id = 'antigravity-account-pill';
            pillContainer.className = 'agy-acc-pill-container';
            toolbar.appendChild(pillContainer);
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
                    <span style="font-size:9px;color:#8ab4f8;">${active.tier || ''}</span>
                </div>
                <div class="agy-acc-list">
                    ${(cachedState.accounts || []).map(acc => {
                        const isSel = acc.email.toLowerCase() === active.email.toLowerCase();
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

        // Toggle dropdown
        const btn = document.getElementById('agy-acc-toggle-btn');
        const dropdown = document.getElementById('agy-acc-dropdown');
        if (btn && dropdown) {
            btn.onclick = (e) => {
                e.stopPropagation();
                dropdown.classList.toggle('open');
            };
        }

        // Account click items
        pillContainer.querySelectorAll('.agy-acc-item').forEach(item => {
            item.onclick = async (e) => {
                e.stopPropagation();
                const email = item.getAttribute('data-email');
                if (email && window.antigravityMultiAccount?.bindCascade) {
                    await window.antigravityMultiAccount.bindCascade(currentCascadeId, email);
                    cachedState.bindings[currentCascadeId] = email;
                    renderPill();
                }
                dropdown.classList.remove('open');
            };
        });

        // Add Account Button
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

        // Refresh Button
        const refBtn = document.getElementById('agy-acc-refresh-btn');
        if (refBtn) {
            refBtn.onclick = async (e) => {
                e.stopPropagation();
                await fetchState();
            };
        }
    }

    // Close on outside click
    document.addEventListener('click', () => {
        const dd = document.getElementById('agy-acc-dropdown');
        if (dd) dd.classList.remove('open');
    });

    // Observer to re-render if toolbar re-mounts
    const observer = new MutationObserver(() => {
        if (!document.getElementById('antigravity-account-pill')) {
            renderPill();
        }
    });
    observer.observe(document.body, { childList: true, subtree: true });

    // Initial load
    fetchState();
    setInterval(fetchState, 15000);
})();
