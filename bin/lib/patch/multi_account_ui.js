// Antigravity Multi-Account UI Injector: Main Controller
(function initUI() {
    if (window.__antigravityRenderSelector) { window.__antigravityRenderSelector(); return; }
    let state = { accounts: [], bindings: {} }, cascadeId = "default", rTimer = null, lastF = 0;
    const apiH = () => window.__AGY_ROUTER_HOST__ || localStorage.getItem("agy_router_host") || "http://127.0.0.1:41999";
    function toast(msg) {
        let t = document.getElementById("antigravity-account-toast") || Object.assign(document.createElement("div"), { id: "antigravity-account-toast", className: "agy-toast" });
        if (!t.parentElement && document.body) document.body.appendChild(t);
        t.textContent = msg; t.style.opacity = "1"; setTimeout(() => t.style.opacity = "0", 2000);
    }
    async function fetchState(force = false) {
        lastF = Date.now(); let res = null;
        if (window.antigravityMultiAccount?.getState && !force) { try { res = await Promise.race([window.antigravityMultiAccount.getState(), new Promise((_, r) => setTimeout(() => r(0), 300))]); } catch (_) {} }
        if (!res?.accounts?.length || force) { try { const r = await fetch(apiH() + "/api/multi-account/state" + (force ? "?refresh=1" : "")); res = await r.json(); } catch (_) {} }
        if (res?.accounts?.length) { const seen = new Set(); res.accounts = res.accounts.filter(a => a?.email && !seen.has(a.email.toLowerCase()) && seen.add(a.email.toLowerCase())); state = res; render(); }
    }
    function getActive() {
        const b = state.bindings?.[cascadeId], em = (typeof b === "object" ? b?.email : b), d = state.active_default || state.bindings?.__active_account;
        return (em && state.accounts?.find(a => a.email && a.email.toLowerCase() === em.toLowerCase())) || state.accounts?.find(a => a.email && a.email.toLowerCase() === d?.toLowerCase()) || state.accounts?.[0] || { email: "Account" };
    }
    async function doLogout(em) {
        if (!em || !confirm(`Log out and remove ${em}?`)) return;
        try { if (window.antigravityMultiAccount?.removeAccount) await window.antigravityMultiAccount.removeAccount(em); } catch (_) {}
        try { await fetch(apiH() + "/api/multi-account/remove", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: em }) }); } catch (_) {}
        state.accounts = (state.accounts || []).filter(x => x.email !== em);
        document.getElementById("agy-acc-dd")?.classList.remove("open"); document.getElementById("agy-flyout")?.classList.remove("visible");
        render(); toast(`✓ Logged out ${em.split("@")[0]}`);
    }
    function updateDdPos() {
        const btn = document.getElementById("agy-acc-btn"), dd = document.getElementById("agy-acc-dd"), fly = document.getElementById("agy-flyout");
        if (!btn || !dd || !dd.classList.contains("open")) return;
        const b = btn.getBoundingClientRect();
        if (!b.width || !b.height || b.top < 0 || b.bottom > window.innerHeight) { dd.classList.remove("open"); fly?.classList.remove("visible"); return; }
        const w = b.left + 270 > window.innerWidth;
        dd.style.bottom = b.top >= 260 ? (window.innerHeight - b.top + 6) + "px" : "auto";
        dd.style.top = b.top < 260 ? (b.bottom + 6) + "px" : "auto";
        dd.style.left = w ? "auto" : b.left + "px"; dd.style.right = w ? (window.innerWidth - b.right) + "px" : "auto";
    }
    function render() {
        try {
            const targetInfo = window.__antigravityFindTarget ? window.__antigravityFindTarget() : null; if (!targetInfo?.target) return;
            const newCid = window.__antigravityDetectCascadeId ? window.__antigravityDetectCascadeId(targetInfo.target) : "default";
            const isDraftId = (id) => !id || id === "default" || id.startsWith("chat_") || id.startsWith("draft_");
            if (cascadeId && isDraftId(cascadeId) && newCid && !isDraftId(newCid) && state.bindings?.[cascadeId]) {
                const em = typeof state.bindings[cascadeId] === "object" ? state.bindings[cascadeId].email : state.bindings[cascadeId];
                delete state.bindings[cascadeId]; state.bindings[newCid] = em;
                void fetch(apiH() + "/api/multi-account/bind", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ cascadeId: newCid, email: em }) });
            }
            cascadeId = newCid; const { target, insertAfter, floating } = targetInfo, active = getActive();
            let pill = document.getElementById("antigravity-account-pill");
            if (!pill || pill.parentElement !== target) {
                if (pill) pill.remove(); pill = document.createElement("div"); pill.id = "antigravity-account-pill";
                (insertAfter?.nextSibling && insertAfter.parentElement === target) ? target.insertBefore(pill, insertAfter.nextSibling) : target.appendChild(pill);
            }
            pill.className = "agy-acc-pill-container" + (floating ? " floating" : "");
            const handle = active.email ? active.email.split("@")[0] : "Account", ddOld = pill.querySelector("#agy-acc-dd");
            if (ddOld?.classList.contains("open") && pill.dataset.email === active.email && pill.dataset.cid === cascadeId) return;
            pill.dataset.email = active.email; pill.dataset.cid = cascadeId;
            (window.__antigravitySetHtml || ((e, s) => e.innerHTML = s))(pill, `<button class="agy-acc-pill-btn flex cursor-pointer items-center h-7 gap-1 rounded-full pl-2 pr-1.5 text-xs text-secondary-foreground select-none outline-none hover:bg-secondary transition-colors" type="button" id="agy-acc-btn" title="${active.email}"><span class="truncate max-w-[130px] font-medium">${handle}</span><span class="opacity-60 text-[9px] ml-0.5">▼</span></button><div class="agy-acc-dropdown" id="agy-acc-dd"><div class="agy-acc-header">Google Accounts</div><div class="agy-acc-list">${(state.accounts || []).map(a => `<div class="agy-acc-item ${a.email?.toLowerCase() === active.email?.toLowerCase() ? "selected" : ""}" data-email="${a.email}"><div class="agy-acc-item-left" style="display:flex;align-items:center;gap:8px;min-width:0;flex:1;"><div class="agy-acc-avatar-sm">${(a.email || "G")[0].toUpperCase()}</div><div class="agy-acc-text-col" style="display:flex;flex-direction:column;min-width:0;flex:1;"><span class="agy-acc-email-text">${a.email.split("@")[0]}</span><span class="agy-acc-email-sub">${a.email}</span></div></div><div style="display:flex;align-items:center;gap:6px;flex-shrink:0;"><span style="color:#3b82f6;font-size:11px;font-weight:bold;">${a.email?.toLowerCase() === active.email?.toLowerCase() ? "✓" : ""}</span><span class="agy-view-usage-link" data-email="${a.email}">Usage ›</span></div></div>`).join("")}</div><div class="agy-acc-footer"><button class="agy-acc-btn-action" id="agy-acc-add">+ Add Account</button><button class="agy-acc-btn-action" id="agy-acc-ref">Refresh</button></div><div class="agy-usage-flyout" id="agy-flyout"></div></div>`);
            const btn = document.getElementById("agy-acc-btn"), dd = document.getElementById("agy-acc-dd"), fly = document.getElementById("agy-flyout");
            if (btn && dd) btn.onclick = (e) => { e.stopPropagation(); if (!dd.classList.toggle("open")) return fly?.classList.remove("visible"); updateDdPos(); void fetchState(); };
            let hTimer = null;
            if (fly) fly.onclick = (e) => { const lb = e.target.closest(".agy-flyout-logout-btn"); if (lb) { e.stopPropagation(); doLogout(lb.getAttribute("data-email")); } };
            pill.querySelectorAll(".agy-acc-item").forEach(item => {
                const em = item.getAttribute("data-email");
                const showFly = async () => {
                    if (hTimer) clearTimeout(hTimer);
                    let a = state.accounts?.find(x => x.email === em);
                    window.__antigravityShowFlyout?.(fly, a, dd, item);
                    if (!a?.quotas?.length || Date.now() - lastF > 20000) { await fetchState(); a = state.accounts?.find(x => x.email === em); if (fly?.classList.contains("visible")) window.__antigravityShowFlyout?.(fly, a, dd, item); }
                };
                item.onmouseenter = showFly; item.onmouseleave = () => { hTimer = setTimeout(() => fly?.classList.remove("visible"), 350); };
                item.querySelector(".agy-view-usage-link")?.addEventListener("click", (e) => { e.stopPropagation(); if (hTimer) clearTimeout(hTimer); void showFly(); });
                item.onclick = async (e) => {
                    if (e.target.closest(".agy-view-usage-link, .agy-usage-flyout")) return; e.stopPropagation();
                    if (em) {
                        const isDraft = !cascadeId || cascadeId === "default" || cascadeId.startsWith("draft_") || cascadeId.startsWith("chat_");
                        try { if (window.antigravityMultiAccount) await Promise.race([window.antigravityMultiAccount.bindCascade?.(cascadeId, em), new Promise(r => setTimeout(r, 200))]); } catch (_) {}
                        try { await fetch(apiH() + "/api/multi-account/bind", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ cascadeId, email: em, active: isDraft }) }); } catch (_) {}
                        if (!state.bindings) state.bindings = {}; state.bindings[cascadeId] = em;
                        if (isDraft) { state.active_default = em; state.bindings.__active_account = em; }
                        render(); toast(`✓ Switched chat to ${em.split("@")[0]}`);
                    }
                    dd.classList.remove("open"); fly?.classList.remove("visible");
                };
            });
            if (fly) { fly.onmouseenter = () => { if (hTimer) clearTimeout(hTimer); }; fly.onmouseleave = () => { hTimer = setTimeout(() => fly?.classList.remove("visible"), 350); }; }
            document.getElementById("agy-acc-add")?.addEventListener("click", async (e) => {
                e.stopPropagation();
                if (window.antigravityMultiAccount?.startLogin) await window.antigravityMultiAccount.startLogin();
                else {
                    try {
                        await fetch(apiH() + "/api/multi-account/login", { method: "POST" });
                        toast("Browser login launched");
                    } catch (_) {
                        alert("Add account via: manage-antigravity.sh multi-account login");
                    }
                }
                const prevCount = (state.accounts || []).length;
                let attempts = 0;
                const pollId = setInterval(async () => {
                    attempts++;
                    await fetchState(true);
                    if ((state.accounts || []).length > prevCount || attempts >= 30) {
                        clearInterval(pollId);
                        if ((state.accounts || []).length > prevCount) toast("✓ Account added!");
                    }
                }, 2000);
            });
            document.getElementById("agy-acc-ref")?.addEventListener("click", async (e) => { e.stopPropagation(); await fetchState(true); toast("Refreshed limits"); });
        } catch (_) {}
    }
    function scheduleRender() { if (!rTimer) rTimer = setTimeout(() => { rTimer = null; render(); }, 60); } window.__antigravityRenderSelector = scheduleRender;
    document.addEventListener("click", (e) => {
        const dd = document.getElementById("agy-acc-dd"), pill = document.getElementById("antigravity-account-pill");
        if (dd && pill && !pill.contains(e.target)) { dd.classList.remove("open"); document.getElementById("agy-flyout")?.classList.remove("visible"); }
        if (e.target.closest('[data-testid*="conversation"], [class*="sidebar"], [data-testid="new-conversation-button"], [aria-label*="New Chat" i], [title*="New Chat" i]')) {
            if (e.target.closest('[data-testid="new-conversation-button"], [aria-label*="New Chat" i], [title*="New Chat" i]')) {
                const cv = document.querySelector('[data-testid="conversation-view"]');
                if (cv?.dataset?.agyDraftId) delete cv.dataset.agyDraftId;
                if (cv?.dataset?.agySessionId) delete cv.dataset.agySessionId;
            }
            scheduleRender(); setTimeout(() => { scheduleRender(); void fetchState(true); }, 150);
        }
    });
    const hookState = (fn) => function() { const r = fn.apply(this, arguments); scheduleRender(); void fetchState(); return r; };
    if (history.pushState) history.pushState = hookState(history.pushState); if (history.replaceState) history.replaceState = hookState(history.replaceState); ['popstate', 'hashchange', 'focus'].forEach(ev => window.addEventListener(ev, () => { scheduleRender(); void fetchState(true); }));
    window.addEventListener("resize", updateDdPos); window.addEventListener("keydown", (e) => { if (e.key === "F5" && !e.ctrlKey && !e.metaKey && !e.shiftKey) { render(); void fetchState(true); } });
    try { const mo = new MutationObserver(() => { const t = window.__antigravityFindTarget?.(), c = window.__antigravityDetectCascadeId?.(t?.target) || "default", p = document.getElementById("antigravity-account-pill"); if (!p || !document.body?.contains(p) || c !== cascadeId) { scheduleRender(); if (c !== cascadeId) void fetchState(); } }); if (document.body) mo.observe(document.body, { childList: true, subtree: true }); } catch (_) {}
    setInterval(() => { const p = document.getElementById("antigravity-account-pill"), t = window.__antigravityFindTarget?.(), c = window.__antigravityDetectCascadeId?.(t?.target) || "default"; if (!p || !document.body?.contains(p) || (t?.target && p.parentElement !== t.target) || c !== cascadeId) { scheduleRender(); if (c !== cascadeId) void fetchState(); } }, 250);
    render(); fetchState(); setTimeout(() => fetchState(true), 1500); setInterval(fetchState, 30000);
})();
