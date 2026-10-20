// Antigravity Multi-Account UI Injector: Main Controller
(function initUI() {
    if (window.__agyMultiAccountReady) return;
    window.__agyMultiAccountReady = true;
    let state = { accounts: [], bindings: {} }, cascadeId = 'default', rTimer = null;

    function toast(msg) {
        let t = document.getElementById('antigravity-account-toast');
        if (!t && document.body) {
            t = document.createElement('div');
            t.id = 'antigravity-account-toast'; t.className = 'agy-toast'; document.body.appendChild(t);
        }
        if (t) { t.textContent = msg; t.style.opacity = '1'; setTimeout(() => t.style.opacity = '0', 2200); }
    }

    async function fetchState() {
        if (window.antigravityMultiAccount?.getState) {
            try { state = await window.antigravityMultiAccount.getState(); render(); } catch (_) {}
        }
    }
    function getActive() {
        const e = state.bindings?.[cascadeId] || state.active_default || state.bindings?.__active_account;
        return state.accounts?.find(a => a.email && a.email.toLowerCase() === e?.toLowerCase()) || state.accounts?.[0] || { email: 'Account' };
    }

    function render() {
        try {
            cascadeId = window.__antigravityDetectCascadeId ? window.__antigravityDetectCascadeId() : 'default';
            const targetInfo = window.__antigravityFindTarget ? window.__antigravityFindTarget() : null;
            if (!targetInfo?.target) return;
            const { target, insertAfter, floating } = targetInfo, active = getActive();
            let pill = document.getElementById('antigravity-account-pill');
            if (!pill || pill.parentElement !== target) {
                if (pill) pill.remove();
                pill = document.createElement('div');
                pill.id = 'antigravity-account-pill';
                if (insertAfter?.nextSibling && insertAfter.parentElement === target) target.insertBefore(pill, insertAfter.nextSibling);
                else target.appendChild(pill);
            }
            pill.className = 'agy-acc-pill-container' + (floating ? ' floating' : '');
            const handle = active.email ? active.email.split('@')[0] : 'Account';
            const ddOld = pill.querySelector('#agy-acc-dd');
            if (ddOld?.classList.contains('open') && pill.dataset.email === active.email) return;
            pill.dataset.email = active.email;

            pill.innerHTML = `<button class="agy-acc-pill-btn" type="button" id="agy-acc-btn" title="${active.email}"><span class="agy-acc-badge">${handle}</span><span style="font-size:8px;opacity:0.6;margin-left:1px;">▼</span></button><div class="agy-acc-dropdown" id="agy-acc-dd"><div class="agy-acc-header">Google Accounts</div><div class="agy-acc-list">${(state.accounts || []).map(a => `<div class="agy-acc-item ${a.email?.toLowerCase() === active.email?.toLowerCase() ? 'selected' : ''}" data-email="${a.email}"><div class="agy-acc-item-left"><div class="agy-acc-avatar-sm">${(a.email || 'G')[0].toUpperCase()}</div><div class="agy-acc-text-col"><span class="agy-acc-email-text">${a.email.split('@')[0]}</span><span class="agy-acc-email-sub">${a.email}</span></div>${a.email?.toLowerCase() === active.email?.toLowerCase() ? '<span style="color:#3b82f6;font-size:11px;font-weight:bold;">✓</span>' : ''}</div><span class="agy-view-usage-link" data-email="${a.email}">View usage ›</span></div>`).join('')}</div><div class="agy-acc-footer"><button class="agy-acc-btn-action" id="agy-acc-add">+ Add Account</button><button class="agy-acc-btn-action" id="agy-acc-ref">Refresh Limits</button></div><div class="agy-usage-flyout" id="agy-flyout"></div></div>`;

            const btn = document.getElementById('agy-acc-btn'), dd = document.getElementById('agy-acc-dd'), fly = document.getElementById('agy-flyout');
            if (btn && dd) btn.onclick = (e) => {
                e.stopPropagation();
                if (dd.classList.toggle('open')) {
                    const top = pill.getBoundingClientRect().top;
                    dd.classList.toggle('downward', top < 260); dd.classList.toggle('upward', top >= 260);
                } else fly?.classList.remove('visible');
            };

            let hTimer = null;
            pill.querySelectorAll('.agy-acc-item').forEach(item => {
                const em = item.getAttribute('data-email'), acc = state.accounts?.find(a => a.email === em);
                item.onmouseenter = () => { if (hTimer) clearTimeout(hTimer); window.__antigravityShowFlyout?.(fly, acc, dd, item); };
                item.onmouseleave = () => { hTimer = setTimeout(() => fly?.classList.remove('visible'), 250); };
                item.querySelector('.agy-view-usage-link')?.addEventListener('click', (e) => { e.stopPropagation(); window.__antigravityShowFlyout?.(fly, acc, dd, item); });
                item.onclick = async (e) => {
                    if (e.target.closest('.agy-view-usage-link') || e.target.closest('.agy-usage-flyout')) return;
                    e.stopPropagation();
                    if (em && window.antigravityMultiAccount) {
                        await window.antigravityMultiAccount.bindCascade?.(cascadeId, em);
                        await window.antigravityMultiAccount.setActiveAccount?.(em);
                        if (!state.bindings) state.bindings = {};
                        state.bindings[cascadeId] = em; state.active_default = em;
                        render(); toast(`✓ Switched chat to ${em.split('@')[0]}`);
                    }
                    dd.classList.remove('open'); fly?.classList.remove('visible');
                };
            });
            if (fly) {
                fly.onmouseenter = () => { if (hTimer) clearTimeout(hTimer); };
                fly.onmouseleave = () => { hTimer = setTimeout(() => fly?.classList.remove('visible'), 250); };
            }
            document.getElementById('agy-acc-add')?.addEventListener('click', async (e) => { e.stopPropagation(); await window.antigravityMultiAccount?.startLogin?.(); await fetchState(); });
            document.getElementById('agy-acc-ref')?.addEventListener('click', async (e) => { e.stopPropagation(); await fetchState(); toast('Usage limits refreshed'); });
        } catch (_) {}
    }
    function scheduleRender() { if (!rTimer) rTimer = setTimeout(() => { rTimer = null; render(); }, 150); }
    document.addEventListener('click', (e) => {
        const dd = document.getElementById('agy-acc-dd'), pill = document.getElementById('antigravity-account-pill');
        if (dd && pill && !pill.contains(e.target)) { dd.classList.remove('open'); document.getElementById('agy-flyout')?.classList.remove('visible'); }
    });
    setInterval(() => {
        const pill = document.getElementById('antigravity-account-pill'), tInfo = window.__antigravityFindTarget?.();
        if (!pill || !document.body?.contains(pill) || (tInfo?.target && pill.parentElement !== tInfo.target)) scheduleRender();
    }, 450);
    window.addEventListener('popstate', scheduleRender); window.addEventListener('hashchange', scheduleRender);
    if (document.documentElement) new MutationObserver((muts) => {
        for (const m of muts) { if (!m.target.closest || !m.target.closest('#antigravity-account-pill')) { scheduleRender(); break; } }
    }).observe(document.documentElement, { childList: true, subtree: true });
    fetchState(); setInterval(fetchState, 30000);
})();
