// ==============================================================================
// Antigravity Multi-Account UI Injector: Prompt Bar Pill & Account Selector
// Flush native styling, clear quota bars, light & dark theme adaptive
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

            /* Flat button matching model selector */
            .agy-acc-pill-btn {
                display: inline-flex;
                align-items: center;
                gap: 6px;
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

            /* Clean capacity indicator */
            .agy-quota-badge {
                display: inline-flex;
                align-items: center;
                gap: 4px;
                font-size: 11px;
                font-weight: 600;
                opacity: 0.9;
            }
            .agy-quota-dot {
                width: 6px;
                height: 6px;
                border-radius: 50%;
                display: inline-block;
            }

            /* Dropdown Menu */
            .agy-acc-dropdown {
                position: absolute;
                bottom: calc(100% + 8px);
                left: 0;
                min-width: 320px;
                background: var(--agy-dropdown-bg);
                border: 1px solid var(--agy-dropdown-border);
                border-radius: 8px;
                box-shadow: var(--agy-dropdown-shadow);
                padding: 6px 0;
                display: none;
                flex-direction: column;
                z-index: 100000;
                color: var(--agy-dropdown-text);
            }
            .agy-acc-dropdown.open {
                display: flex;
            }
            .agy-acc-header {
                padding: 6px 14px 8px;
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
            .agy-acc-list {
                max-height: 380px;
                overflow-y: auto;
            }
            .agy-acc-item {
                display: flex;
                flex-direction: column;
                gap: 6px;
                padding: 10px 14px;
                cursor: pointer;
                transition: background 0.12s ease;
                border-bottom: 1px solid var(--agy-dropdown-border);
            }
            .agy-acc-item:last-child {
                border-bottom: none;
            }
            .agy-acc-item:hover {
                background: var(--agy-dropdown-hover);
            }
            .agy-acc-item.selected {
                background: var(--agy-dropdown-selected);
            }
            .agy-acc-item-top {
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            .agy-acc-item-email {
                font-size: 12px;
                font-weight: 600;
                color: var(--agy-dropdown-text);
                display: flex;
                align-items: center;
                gap: 6px;
            }
            .agy-acc-active-tag {
                font-size: 9px;
                font-weight: 700;
                padding: 1px 5px;
                border-radius: 4px;
                background: rgba(52, 168, 83, 0.15);
                color: #34a853;
                border: 1px solid rgba(52, 168, 83, 0.3);
            }
            .agy-acc-tag-primary {
                font-size: 9px;
                font-weight: 600;
                padding: 1px 5px;
                border-radius: 4px;
                background: rgba(66, 133, 244, 0.12);
                color: #4285f4;
            }

            /* Capacity Progress Bars */
            .agy-capacity-section {
                display: flex;
                flex-direction: column;
                gap: 4px;
                margin-top: 2px;
            }
            .agy-capacity-row {
                display: flex;
                align-items: center;
                justify-content: space-between;
                font-size: 11px;
                color: var(--agy-dropdown-subtext);
            }
            .agy-capacity-bar-track {
                width: 100%;
                height: 4px;
                background: var(--agy-quota-track);
                border-radius: 2px;
                overflow: hidden;
            }
            .agy-capacity-bar-fill {
                height: 100%;
                border-radius: 2px;
                transition: width 0.3s ease;
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
                font-weight: 500;
                cursor: pointer;
                text-align: center;
            }
            .agy-acc-btn-action:hover {
                background: var(--agy-btn-action-hover);
            }

            /* Toast Notification */
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

    function getStatusColor(percent) {
        if (percent >= 50) return '#34a853'; // Green
        if (percent >= 20) return '#fbbc04'; // Amber
        return '#ea4335'; // Red
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

        // Build clean capacity indicator (no "Ready", no crowded text)
        let quotaText = '';
        if (active.quotas && active.quotas.length > 0) {
            const gQ = active.quotas.find(q => q.family === 'gemini');
            const cQ = active.quotas.find(q => q.family === 'claude');
            const lowestQ = [gQ, cQ].filter(Boolean).sort((a, b) => a.fraction - b.fraction)[0];
            const pct = lowestQ ? Math.round(lowestQ.fraction * 100) : 100;
            const color = getStatusColor(pct);
            quotaText = `<span class="agy-quota-badge"><span class="agy-quota-dot" style="background:${color}"></span>${pct}%</span>`;
        }

        const renderKey = `${active.email}|${quotaText}|${currentCascadeId}|${(cachedState.accounts || []).length}|${floating}`;
        if (pillContainer.__renderKey === renderKey) {
            return;
        }
        pillContainer.__renderKey = renderKey;

        pillContainer.className = 'agy-acc-pill-container' + (floating ? ' floating' : '');

        pillContainer.innerHTML = `
            <button class="agy-acc-pill-btn" type="button" id="agy-acc-toggle-btn" title="Antigravity Account Selector: ${active.email}">
                <div class="agy-acc-avatar">${initial}</div>
                <span class="agy-acc-badge">${active.email.split('@')[0]}</span>
                ${quotaText}
                <span style="font-size:8px;opacity:0.6;margin-left:1px;">▼</span>
            </button>
            <div class="agy-acc-dropdown" id="agy-acc-dropdown">
                <div class="agy-acc-header">
                    <span>Google Accounts</span>
                    <span style="font-size:10px;font-weight:600;color:#3b82f6;">${active.tier || ''}</span>
                </div>
                <div class="agy-acc-list">
                    ${(cachedState.accounts || []).map(acc => {
                        const isSel = acc.email && acc.email.toLowerCase() === active.email.toLowerCase();
                        const gQ = (acc.quotas || []).find(q => q.family === 'gemini');
                        const cQ = (acc.quotas || []).find(q => q.family === 'claude');
                        const gPct = gQ ? Math.round(gQ.fraction * 100) : 100;
                        const cPct = cQ ? Math.round(cQ.fraction * 100) : 100;
                        const gCol = getStatusColor(gPct);
                        const cCol = getStatusColor(cPct);

                        return `
                            <div class="agy-acc-item ${isSel ? 'selected' : ''}" data-email="${acc.email}">
                                <div class="agy-acc-item-top">
                                    <div class="agy-acc-item-email">
                                        <span>${acc.email}</span>
                                        ${acc.is_primary ? '<span class="agy-acc-tag-primary">Primary</span>' : ''}
                                    </div>
                                    ${isSel ? '<span class="agy-acc-active-tag">Active in chat</span>' : ''}
                                </div>
                                <div class="agy-capacity-section">
                                    <div class="agy-capacity-row">
                                        <span>Gemini Capacity</span>
                                        <span style="font-weight:600;color:${gCol};">${gPct}% remaining</span>
                                    </div>
                                    <div class="agy-capacity-bar-track">
                                        <div class="agy-capacity-bar-fill" style="width:${gPct}%;background:${gCol};"></div>
                                    </div>
                                    <div class="agy-capacity-row" style="margin-top:2px;">
                                        <span>Claude / 3P Capacity</span>
                                        <span style="font-weight:600;color:${cCol};">${cPct}% remaining</span>
                                    </div>
                                    <div class="agy-capacity-bar-track">
                                        <div class="agy-capacity-bar-fill" style="width:${cPct}%;background:${cCol};"></div>
                                    </div>
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>
                <div class="agy-acc-footer">
                    <button class="agy-acc-btn-action" id="agy-acc-add-btn">+ Add Account</button>
                    <button class="agy-acc-btn-action" id="agy-acc-refresh-btn">Refresh Quotas</button>
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

        // Switch account
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
                showToast('Quotas refreshed');
            };
        }
    }

    // Close on outside click
    document.addEventListener('click', () => {
        const dd = document.getElementById('agy-acc-dropdown');
        if (dd) dd.classList.remove('open');
    });

    // Observer: debounced, ignoring self-mutations
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
