// Antigravity Multi-Account UI Injector: Main Controller
(function initUI() {
    if (window.__antigravityRenderSelector) { window.__antigravityRenderSelector(); return; }
    let state = { accounts: [], bindings: {} }, cascadeId = "default", rTimer = null;
    const apiH = () => window.__AGY_ROUTER_HOST__ || localStorage.getItem("agy_router_host") || "http://127.0.0.1:41999";

    function toast(msg) {
        let t = document.getElementById("antigravity-account-toast");
        if (!t && document.body) { t = document.createElement("div"); t.id = "antigravity-account-toast"; t.className = "agy-toast"; document.body.appendChild(t); }
        if (t) { t.textContent = msg; t.style.opacity = "1"; setTimeout(() => t.style.opacity = "0", 2000); }
    }
    async function fetchState() {
        let res = null;
        if (window.antigravityMultiAccount?.getState) {
            try { res = await Promise.race([window.antigravityMultiAccount.getState(), new Promise((_, r) => setTimeout(() => r(0), 300))]); } catch (_) {}
        }
        if (!res?.accounts?.length) { try { const r = await fetch(apiH() + "/api/multi-account/state"); res = await r.json(); } catch (_) {} }
        if (res?.accounts?.length) { state = res; render(); }
    }
    function getActive() {
        const b = state.bindings?.[cascadeId], em = (typeof b === "object" ? b?.email : b) || state.active_default || state.bindings?.__active_account;
        return state.accounts?.find(a => a.email && a.email.toLowerCase() === em?.toLowerCase()) || state.accounts?.[0] || { email: "Account" };
    }

    function render() {
        try {
            cascadeId = window.__antigravityDetectCascadeId ? window.__antigravityDetectCascadeId() : "default";
            const targetInfo = window.__antigravityFindTarget ? window.__antigravityFindTarget() : null;
            if (!targetInfo?.target) return;
            const { target, insertAfter, floating } = targetInfo, active = getActive();
            let pill = document.getElementById("antigravity-account-pill");
            if (!pill || pill.parentElement !== target) {
                if (pill) pill.remove();
                pill = document.createElement("div"); pill.id = "antigravity-account-pill";
                if (insertAfter?.nextSibling && insertAfter.parentElement === target) target.insertBefore(pill, insertAfter.nextSibling);
                else target.appendChild(pill);
            }
            pill.className = "agy-acc-pill-container" + (floating ? " floating" : "");
            const handle = active.email ? active.email.split("@")[0] : "Account", ddOld = pill.querySelector("#agy-acc-dd");
            if (ddOld?.classList.contains("open") && pill.dataset.email === active.email && pill.dataset.cid === cascadeId) return;
            pill.dataset.email = active.email; pill.dataset.cid = cascadeId;
            pill.innerHTML = `<button class="flex cursor-pointer items-center h-7 gap-1 rounded-full pl-2 pr-1.5 text-xs text-secondary-foreground select-none outline-none hover:bg-secondary transition-colors" type="button" id="agy-acc-btn" title="${active.email}"><span class="truncate max-w-[130px] font-medium">${handle}</span><span class="opacity-60 text-[9px] ml-0.5">▼</span></button><div class="agy-acc-dropdown" id="agy-acc-dd"><div class="agy-acc-header">Google Accounts</div><div class="agy-acc-list">${(state.accounts || []).map(a => `<div class="agy-acc-item ${a.email?.toLowerCase() === active.email?.toLowerCase() ? "selected" : ""}" data-email="${a.email}"><div class="agy-acc-item-left"><div class="agy-acc-avatar-sm">${(a.email || "G")[0].toUpperCase()}</div><div class="agy-acc-text-col"><span class="agy-acc-email-text">${a.email.split("@")[0]}</span><span class="agy-acc-email-sub">${a.email}</span></div>${a.email?.toLowerCase() === active.email?.toLowerCase() ? "<span style=\"color:#3b82f6;font-size:11px;font-weight:bold;\">✓</span>" : ""}</div><div style="display:flex;align-items:center;gap:6px;"><span class="agy-view-usage-link" data-email="${a.email}">Usage ›</span>${!a.is_primary ? `<button class="agy-acc-del-btn" data-email="${a.email}" title="Log out / Remove" style="background:none;border:none;cursor:pointer;opacity:0.35;font-size:11px;padding:2px 4px;border-radius:4px;color:inherit;" onmouseover="this.style.opacity='1';this.style.color='#ef4444';" onmouseout="this.style.opacity='0.35';this.style.color='';">✕</button>` : ''}</div></div>`).join("")}</div><div class="agy-acc-footer"><button class="agy-acc-btn-action" id="agy-acc-add">+ Add Account</button><button class="agy-acc-btn-action" id="agy-acc-ref">Refresh</button></div><div class="agy-usage-flyout" id="agy-flyout"></div></div>`;

            const btn = document.getElementById("agy-acc-btn"), dd = document.getElementById("agy-acc-dd"), fly = document.getElementById("agy-flyout");
            if (btn && dd) btn.onclick = (e) => { e.stopPropagation(); if (dd.classList.toggle("open")) { const top = pill.getBoundingClientRect().top; dd.classList.toggle("downward", top < 260); dd.classList.toggle("upward", top >= 260); void fetchState(); } else fly?.classList.remove("visible"); };
            let hTimer = null;
            pill.querySelectorAll(".agy-acc-del-btn").forEach(delBtn => {
                delBtn.onclick = async (e) => {
                    e.stopPropagation(); const em = delBtn.getAttribute("data-email");
                    if (!em || !confirm(`Log out and remove ${em}?`)) return;
                    try { if (window.antigravityMultiAccount?.removeAccount) await window.antigravityMultiAccount.removeAccount(em); } catch (_) {}
                    try { await fetch(apiH() + "/api/multi-account/remove", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: em }) }); } catch (_) {}
                    state.accounts = (state.accounts || []).filter(x => x.email !== em); render(); toast(`✓ Logged out ${em.split("@")[0]}`);
                };
            });
            pill.querySelectorAll(".agy-acc-item").forEach(item => {
                const em = item.getAttribute("data-email");
                const showFly = async () => {
                    if (hTimer) clearTimeout(hTimer);
                    let a = state.accounts?.find(x => x.email === em);
                    window.__antigravityShowFlyout?.(fly, a, dd, item);
                    if (!a?.quotas?.length) { await fetchState(); a = state.accounts?.find(x => x.email === em); if (fly?.classList.contains("visible")) window.__antigravityShowFlyout?.(fly, a, dd, item); }
                };
                item.onmouseenter = showFly; item.onmouseleave = () => { hTimer = setTimeout(() => fly?.classList.remove("visible"), 250); };
                item.querySelector(".agy-view-usage-link")?.addEventListener("click", (e) => { e.stopPropagation(); void showFly(); });
                item.onclick = async (e) => {
                    if (e.target.closest(".agy-view-usage-link") || e.target.closest(".agy-usage-flyout") || e.target.closest(".agy-acc-del-btn")) return;
                    e.stopPropagation();
                    if (em) {
                        try { if (window.antigravityMultiAccount) { await Promise.race([window.antigravityMultiAccount.bindCascade?.(cascadeId, em), new Promise(r => setTimeout(r, 200))]); await Promise.race([window.antigravityMultiAccount.setActiveAccount?.(em), new Promise(r => setTimeout(r, 200))]); } } catch (_) {}
                        try { await fetch(apiH() + "/api/multi-account/bind", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ cascadeId, email: em, active: true }) }); } catch (_) {}
                        if (!state.bindings) state.bindings = {};
                        state.bindings[cascadeId] = em; state.active_default = em; render(); toast(`✓ Switched chat to ${em.split("@")[0]}`);
                    }
                    dd.classList.remove("open"); fly?.classList.remove("visible");
                };
            });
            if (fly) { fly.onmouseenter = () => { if (hTimer) clearTimeout(hTimer); }; fly.onmouseleave = () => { hTimer = setTimeout(() => fly?.classList.remove("visible"), 250); }; }
            document.getElementById("agy-acc-add")?.addEventListener("click", async (e) => { e.stopPropagation(); if (window.antigravityMultiAccount?.startLogin) await window.antigravityMultiAccount.startLogin(); else alert("Add account via: manage-antigravity.sh multi-account login"); setTimeout(fetchState, 3000); });
            document.getElementById("agy-acc-ref")?.addEventListener("click", async (e) => { e.stopPropagation(); await fetchState(); toast("Refreshed limits"); });
        } catch (_) {}
    }
    function scheduleRender() { if (!rTimer) rTimer = setTimeout(() => { rTimer = null; render(); }, 60); }
    window.__antigravityRenderSelector = scheduleRender;
    document.addEventListener("click", (e) => {
        const dd = document.getElementById("agy-acc-dd"), pill = document.getElementById("antigravity-account-pill");
        if (dd && pill && !pill.contains(e.target)) { dd.classList.remove("open"); document.getElementById("agy-flyout")?.classList.remove("visible"); }
        if (e.target.closest("[data-testid*=\"conversation\"], [class*=\"sidebar\"], [data-testid=\"new-conversation-button\"]")) { scheduleRender(); setTimeout(scheduleRender, 200); }
    });
    window.addEventListener("keydown", (e) => { if (e.key === "F5" && !e.ctrlKey && !e.metaKey && !e.shiftKey) { render(); void fetchState(); } });
    if (history.pushState) { const op = history.pushState; history.pushState = function() { const r = op.apply(this, arguments); scheduleRender(); return r; }; }
    if (history.replaceState) { const or = history.replaceState; history.replaceState = function() { const r = or.apply(this, arguments); scheduleRender(); return r; }; }
    try { const mo = new MutationObserver(() => { const curCid = window.__antigravityDetectCascadeId?.() || "default", p = document.getElementById("antigravity-account-pill"); if (!p || !document.body?.contains(p) || curCid !== cascadeId) scheduleRender(); }); if (document.body) mo.observe(document.body, { childList: true, subtree: true }); } catch (_) {}
    setInterval(() => { const pill = document.getElementById("antigravity-account-pill"), tInfo = window.__antigravityFindTarget?.(), curCid = window.__antigravityDetectCascadeId?.() || "default"; if (!pill || !document.body?.contains(pill) || (tInfo?.target && pill.parentElement !== tInfo.target) || curCid !== cascadeId) scheduleRender(); }, 250);
    window.addEventListener("popstate", scheduleRender); window.addEventListener("hashchange", scheduleRender);
    render(); fetchState(); setTimeout(fetchState, 1500); setTimeout(fetchState, 4000); setInterval(fetchState, 60000);
})();
