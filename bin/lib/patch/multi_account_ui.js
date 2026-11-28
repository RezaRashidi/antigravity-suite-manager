// Antigravity Multi-Account UI Injector: Main Controller
(function initUI() {
    if (window.__antigravityRenderSelector) { window.__antigravityRenderSelector(); return; }
    let state = { accounts: [], bindings: {} }, cascadeId = "default", rTimer = null, lastF = 0, lastActiveEmail = null, lastSavedModels = {}, isRestoring = false, restoreSeq = 0, lastUserModelClickTs = 0, lastUserModelClickCid = null, lastTypingTs = 0, inFlightRefresh = null, inFlightByEmail = {}, lastAccRefresh = {};
    const isDraftId = (id) => !id || id === "default" || id.startsWith("chat_") || id.startsWith("draft_");
    const isTypingEl = (el) => Boolean(el && (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT' || el.isContentEditable || el.closest?.('[contenteditable], .monaco-editor, [data-lexical-editor], [role="textbox"]')));
    function notifyAccountSwitch(em, cid, reason) {
        if (!em || em === "Account") return;
        window.dispatchEvent(new CustomEvent('antigravity:account-switched', { detail: { email: em, cascadeId: cid, reason } }));
    }
    async function handleChatModelRestoration(cid) {
        if (!cid || cid === "default" || isDraftId(cid)) return;
        const mySeq = ++restoreSeq;
        isRestoring = true;
        try {
            if (window.__antigravityActiveRefreshPromise) {
                try {
                    await Promise.race([window.__antigravityActiveRefreshPromise, new Promise(r => setTimeout(r, 2500))]);
                } catch (_) {}
            }
            await new Promise(r => setTimeout(r, 120));
            if (mySeq !== restoreSeq || cascadeId !== cid) return;
            const b = state.bindings?.[cid];
            const savedModel = (typeof b === "object" ? b?.model : null) || lastSavedModels[cid] || null;
            const configs = window.__antigravityAvailableConfigs || [];
            const restored = await window.__antigravitySelectModel?.(savedModel, configs);
            if (mySeq !== restoreSeq || cascadeId !== cid) return;
            if (restored) {
                const norm = (s) => (s || '').toLowerCase().replace(/[^a-z0-9]/g, '');
                const sNorm = norm(savedModel);
                const rNorm = norm(restored);
                const matchesSaved = sNorm && rNorm && (sNorm.includes(rNorm) || rNorm.includes(sNorm));
                const shouldPersist = !savedModel || matchesSaved || (configs.length > 0 && !configs.some(c => norm(c.label).includes(sNorm) || sNorm.includes(norm(c.label))));
                if (shouldPersist) {
                    const boundEm = (typeof b === "object" ? b?.email : b);
                    const curEmail = (boundEm && boundEm !== "Account") ? boundEm : getActive()?.email;
                    if (!state.bindings) state.bindings = {};
                    if (typeof state.bindings[cid] === "object") {
                        state.bindings[cid].model = restored;
                    } else {
                        state.bindings[cid] = { email: state.bindings[cid] || curEmail, model: restored };
                    }
                    lastSavedModels[cid] = restored;
                    void fetch(apiH() + "/api/multi-account/bind", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ cascadeId: cid, email: curEmail, model: restored })
                    });
                }
            }
        } finally {
            setTimeout(() => { if (mySeq === restoreSeq) isRestoring = false; }, 200);
        }
    }
    const apiH = () => window.__AGY_ROUTER_HOST__ || localStorage.getItem("agy_router_host") || "http://127.0.0.1:41999";
    function toast(msg) {
        let t = document.getElementById("antigravity-account-toast") || Object.assign(document.createElement("div"), { id: "antigravity-account-toast", className: "agy-toast" });
        if (!t.parentElement && document.body) document.body.appendChild(t);
        t.textContent = msg; t.style.opacity = "1"; setTimeout(() => t.style.opacity = "0", 2000);
    }
    async function fetchState(force = false, waitRefresh = false, targetEmail = null) {
        const emKey = targetEmail ? String(targetEmail).toLowerCase() : null;
        if (force && emKey && inFlightByEmail[emKey]) return inFlightByEmail[emKey];
        if (force && !emKey && inFlightRefresh) return inFlightRefresh;
        const run = (async () => {
            lastF = Date.now(); let res = null;
            if (!state.accounts?.length && window.__AGY_INITIAL_STATE__?.accounts?.length) {
                state = window.__AGY_INITIAL_STATE__;
                render();
            }
            if (window.antigravityMultiAccount?.getState && !force) { try { res = await Promise.race([window.antigravityMultiAccount.getState(), new Promise((_, r) => setTimeout(() => r(0), 1000))]); } catch (_) {} }
            if (!res?.accounts?.length || force) {
                const hdr = document.querySelector?.('#agy-acc-dd .agy-acc-header');
                if (force && !emKey && hdr) hdr.textContent = 'Google Accounts • Updating...';
                try {
                    const params = [];
                    if (force) params.push('refresh=1');
                    if (force && waitRefresh) params.push('wait=1');
                    if (emKey) params.push('email=' + encodeURIComponent(targetEmail));
                    const qs = params.length ? '?' + params.join('&') : '';
                    const ac = typeof AbortController !== 'undefined' ? new AbortController() : null;
                    const tid = ac ? setTimeout(() => ac.abort(), 6000) : null;
                    const r = await fetch(apiH() + "/api/multi-account/state" + qs, ac ? { signal: ac.signal } : undefined);
                    if (tid) clearTimeout(tid);
                    res = await r.json();
                    if (emKey) lastAccRefresh[emKey] = Date.now();
                } catch (_) {
                } finally {
                    if (force && !emKey && hdr) hdr.textContent = 'Google Accounts';
                }
            }
            if (res?.accounts?.length) {
                const seen = new Set();
                res.accounts = res.accounts.filter(a => a?.email && !seen.has(a.email.toLowerCase()) && seen.add(a.email.toLowerCase()));
                state = res;
                const ddOpen = document.getElementById("agy-acc-dd")?.classList.contains("open");
                if (ddOpen) {
                    updateOpenDropdownUI();
                } else if (Date.now() - lastTypingTs >= 800) {
                    render();
                }
            }
        })();
        if (force && emKey) {
            inFlightByEmail[emKey] = run;
            try { await run; } finally { if (inFlightByEmail[emKey] === run) delete inFlightByEmail[emKey]; }
            return;
        }
        if (force) {
            inFlightRefresh = run;
            try { await run; } finally { if (inFlightRefresh === run) inFlightRefresh = null; }
            return;
        }
        await run;
    }
    function buildTierBadge(a) {
        if (!a) return '';
        const isBad = a.license_status === 'verify_required' || a.license_status === 'no_license' || a.license_status === 'auth_failed';
        if (isBad) return '';
        const tt = String(a.tier_type || a.tier || '');
        if (tt === 'Paid Pro') return '<span class="agy-tier-badge-sm paid">PAID PRO</span>';
        if (tt === 'Free Pro') return '<span class="agy-tier-badge-sm free">FREE PRO</span>';
        if (tt === 'PRO' || tt === 'TEAMS_TIER_PRO') return '<span class="agy-tier-badge-sm free">PRO</span>';
        if (tt === 'Free' || tt === 'FREE') return '<span class="agy-tier-badge-sm free">FREE</span>';
        return '';
    }
    function buildStatusBadge(a) {
        if (!a) return '';
        const tip = String(a.license_message || a.refresh_error || '').replace(/"/g, '&quot;');
        if (a.license_status === 'verify_required') return `<span style="font-size:9px;color:#ef4444;border:1px solid rgba(239,68,68,0.4);padding:0 4px;border-radius:3px;font-weight:600;" title="${tip || 'Verification Required'}">VERIFY</span>`;
        if (a.license_status === 'auth_failed') return `<span style="font-size:9px;color:#ef4444;border:1px solid rgba(239,68,68,0.4);padding:0 4px;border-radius:3px;font-weight:600;" title="${tip || 'Logged Out / Session Expired'}">LOGGED OUT</span>`;
        if (a.license_status === 'no_license') return `<span style="font-size:9px;color:#f59e0b;border:1px solid rgba(245,158,11,0.4);padding:0 4px;border-radius:3px;font-weight:600;" title="${tip || 'No License'}">NO LIC</span>`;
        if (a.license_status === 'exhausted') return `<span style="font-size:9px;color:#f59e0b;border:1px solid rgba(245,158,11,0.4);padding:0 4px;border-radius:3px;font-weight:600;" title="${tip || 'Resource Exhausted'}">LIMIT</span>`;
        if (a.license_status === 'refresh_failed' || a.license_status === 'network_error' || a.license_status === 'forbidden_transient' || a.refresh_error) {
            return `<span style="font-size:9px;color:#f97316;border:1px solid rgba(249,115,22,0.4);padding:0 4px;border-radius:3px;font-weight:600;" title="${tip || 'Refresh Failed'}">ERR</span>`;
        }
        return '';
    }
    function updateOpenDropdownUI() {
        try {
            const pill = document.getElementById("antigravity-account-pill");
            const dd = document.getElementById("agy-acc-dd");
            const fly = document.getElementById("agy-flyout");
            if (!pill || !dd || !dd.classList.contains("open")) return;
            const setH = window.__antigravitySetHtml || ((e, s) => e.innerHTML = s);
            pill.querySelectorAll(".agy-acc-item").forEach(item => {
                const em = item.getAttribute("data-email");
                const a = state.accounts?.find(x => x.email?.toLowerCase() === em?.toLowerCase());
                if (!a) return;
                const badgeSlot = item.querySelector(".agy-tier-slot");
                if (badgeSlot) {
                    const nextHtml = buildTierBadge(a);
                    if (badgeSlot.innerHTML !== nextHtml) setH(badgeSlot, nextHtml);
                }
                const statusSlot = item.querySelector(".agy-status-slot");
                if (statusSlot) {
                    const nextSt = buildStatusBadge(a);
                    if (statusSlot.innerHTML !== nextSt) setH(statusSlot, nextSt);
                }
            });
            if (fly && fly.classList.contains("visible") && fly.dataset.email) {
                const fa = state.accounts?.find(x => x.email?.toLowerCase() === fly.dataset.email.toLowerCase());
                if (fa) window.__antigravityShowFlyout?.(fly, fa, dd, null);
            }
        } catch (_) {}
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
            let switchedChatAccount = false;
            if (cascadeId !== newCid) {
                isRestoring = true;
                const prevCid = cascadeId;
                cascadeId = newCid;
                if (prevCid && isDraftId(prevCid) && newCid && !isDraftId(newCid) && state.bindings?.[prevCid]) {
                    const em = typeof state.bindings[prevCid] === "object" ? state.bindings[prevCid].email : state.bindings[prevCid];
                    const mod = (typeof state.bindings[prevCid] === "object" ? state.bindings[prevCid].model : null) || lastSavedModels[prevCid] || '';
                    delete state.bindings[prevCid];
                    state.bindings[newCid] = { email: em, model: mod };
                    if (mod) lastSavedModels[newCid] = mod;
                    if (em && em !== "Account") lastActiveEmail = em;
                    void fetch(apiH() + "/api/multi-account/bind", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ cascadeId: newCid, email: em, model: mod }) });
                    void handleChatModelRestoration(newCid);
                } else {
                    const b = state.bindings?.[newCid];
                    const em = (typeof b === "object" ? b?.email : b) || getActive()?.email;
                    const mod = (typeof b === "object" ? b?.model : null) || lastSavedModels[newCid] || '';
                    if (em && em !== "Account") {
                        const accountChanged = Boolean(lastActiveEmail && em.toLowerCase() !== lastActiveEmail.toLowerCase());
                        lastActiveEmail = em;
                        switchedChatAccount = true;
                        fetch(apiH() + "/api/multi-account/set-active", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ cascadeId: newCid, email: em, model: mod }) })
                            .then(() => {
                                if (accountChanged) notifyAccountSwitch(em, newCid, 'chat-switch');
                                void handleChatModelRestoration(newCid);
                            })
                            .catch(() => {
                                void handleChatModelRestoration(newCid);
                            });
                    } else {
                        void handleChatModelRestoration(newCid);
                    }
                }
            }
            const { target, insertAfter, floating } = targetInfo, active = getActive();
            const isWinFocused = typeof document.hasFocus !== "function" || document.hasFocus();
            if (!switchedChatAccount && isWinFocused && active?.email && active.email !== "Account") {
                if (!lastActiveEmail) {
                    lastActiveEmail = active.email;
                } else if (active.email.toLowerCase() !== lastActiveEmail.toLowerCase()) {
                    const em = active.email;
                    lastActiveEmail = em;
                    fetch(apiH() + "/api/multi-account/set-active", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ cascadeId, email: em }) })
                        .then(() => notifyAccountSwitch(em, cascadeId, 'binding-sync'))
                        .catch(() => {});
                }
            }
            let pill = document.getElementById("antigravity-account-pill");
            if (!pill || pill.parentElement !== target) {
                if (pill) pill.remove(); pill = document.createElement("div"); pill.id = "antigravity-account-pill";
                (insertAfter?.nextSibling && insertAfter.parentElement === target) ? target.insertBefore(pill, insertAfter.nextSibling) : target.appendChild(pill);
            }
            pill.className = "agy-acc-pill-container" + (floating ? " floating" : "");
            const handle = active.email ? active.email.split("@")[0] : "Account", ddOld = pill.querySelector("#agy-acc-dd");
            if (ddOld?.classList.contains("open") && pill.dataset.email === active.email && pill.dataset.cid === cascadeId) return;
            const accountsSig = (state.accounts || []).map(a => `${a.email || ''}:${a.is_primary ? 1 : 0}:${a.license_status || ''}:${a.tier_type || a.tier || ''}`).join('|');
            const renderSig = `${active.email || ''}|${cascadeId}|${floating ? 1 : 0}|${accountsSig}`;
            if (pill.dataset.renderSig === renderSig && pill.innerHTML) return;
            pill.dataset.email = active.email; pill.dataset.cid = cascadeId; pill.dataset.renderSig = renderSig;
            (window.__antigravitySetHtml || ((e, s) => e.innerHTML = s))(pill, `<button class="agy-acc-pill-btn flex cursor-pointer items-center h-7 gap-1 rounded-full pl-2 pr-1 text-xs text-secondary-foreground select-none outline-none hover:bg-secondary transition-colors" type="button" id="agy-acc-btn" title="${active.email}"><span class="truncate max-w-[130px] font-medium">${handle}</span><svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 -960 960 960" fill="currentColor" class="shrink-0" aria-hidden="true"><path d="M480-357.85L253.85-584L296-626.15l184,184l184-184L706.15-584L480-357.85Z"/></svg></button><div class="agy-acc-dropdown" id="agy-acc-dd"><div class="agy-acc-header">Google Accounts</div><div class="agy-acc-list">${(state.accounts || []).map(a => {
                const isSel = a.email?.toLowerCase() === active.email?.toLowerCase(), isPrim = !!a.is_primary;
                const isBad = a.license_status === 'verify_required' || a.license_status === 'no_license' || a.license_status === 'auth_failed';
                const statusTag = `<span class="agy-status-slot">${buildStatusBadge(a)}</span>`;
                const star = isPrim ? '<span style="color:#eab308;font-size:11px;" title="Primary Account">★</span>' : '';
                const tierTag = `<span class="agy-tier-slot">${buildTierBadge(a)}</span>`;
                return `<div class="agy-acc-item ${isSel ? "selected" : ""}" data-email="${a.email}" style="${isBad ? 'opacity:0.65;' : ''}"><div class="agy-acc-item-left" style="display:flex;align-items:center;gap:8px;min-width:0;flex:1;"><div class="agy-acc-avatar-sm">${(a.email || "G")[0].toUpperCase()}</div><div class="agy-acc-text-col" style="display:flex;flex-direction:column;min-width:0;flex:1;"><div style="display:flex;align-items:center;gap:4px;overflow:hidden;"><span class="agy-acc-email-text">${a.email.split("@")[0]}</span>${star}${tierTag}${statusTag}</div><span class="agy-acc-email-sub">${a.email}</span></div></div><div style="display:flex;align-items:center;gap:6px;flex-shrink:0;">${isSel ? '<span style="color:#3b82f6;font-size:12px;font-weight:bold;">✓</span>' : ''}<span class="agy-view-usage-link" data-email="${a.email}" title="View details and usage">›</span></div></div>`;
            }).join("")}</div><div class="agy-acc-footer"><button class="agy-acc-btn-action" id="agy-acc-add">+ Add Account</button><button class="agy-acc-btn-action" id="agy-acc-ref">Refresh</button></div><div class="agy-usage-flyout" id="agy-flyout"></div></div>`);
            const btn = document.getElementById("agy-acc-btn"), dd = document.getElementById("agy-acc-dd"), fly = document.getElementById("agy-flyout");
            if (btn && dd) btn.onclick = (e) => { e.stopPropagation(); if (!dd.classList.toggle("open")) return fly?.classList.remove("visible"); updateDdPos(); };
            let hTimer = null;
            if (fly) fly.onclick = async (e) => {
                const cp = e.target.closest(".agy-flyout-copy-url");
                if (cp) {
                    e.stopPropagation();
                    const u = cp.getAttribute("data-url");
                    if (u) {
                        try { await navigator.clipboard?.writeText(u); toast("✓ Verification link copied"); } catch (_) { toast(u); }
                    }
                    return;
                }
                const vl = e.target.closest(".agy-flyout-verify-link");
                if (vl) {
                    e.stopPropagation();
                    const u = vl.getAttribute("data-url") || vl.getAttribute("href");
                    if (u) { try { window.open(u, "_blank", "noopener,noreferrer"); } catch (_) {} }
                    return;
                }
                const lb = e.target.closest(".agy-flyout-logout-btn");
                if (lb) { e.stopPropagation(); doLogout(lb.getAttribute("data-email")); return; }
                const pb = e.target.closest(".agy-flyout-primary-btn");
                if (pb) {
                    e.stopPropagation();
                    const pem = pb.getAttribute("data-email");
                    if (pem) {
                        try {
                            if (window.antigravityMultiAccount?.setPrimary) await window.antigravityMultiAccount.setPrimary(pem);
                            else await fetch(apiH() + "/api/multi-account/set-primary", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: pem }) });
                        } catch (_) {}
                        window.dispatchEvent(new CustomEvent('antigravity:account-switched', { detail: { email: pem } }));
                        try { if (window.__antigravityRefreshModels) void window.__antigravityRefreshModels(); } catch (_) {}
                        toast(`✓ Set ${pem.split("@")[0]} as Primary!`);
                        await fetchState(true);
                    }
                }
            };
            pill.querySelectorAll(".agy-acc-item").forEach(item => {
                const em = item.getAttribute("data-email");
                const showFly = () => {
                    if (hTimer) clearTimeout(hTimer);
                    if (fly) fly.dataset.email = em || '';
                    const a = state.accounts?.find(x => x.email === em);
                    window.__antigravityShowFlyout?.(fly, a, dd, item);
                    const emKey = (em || '').toLowerCase();
                    if (emKey && (!lastAccRefresh[emKey] || Date.now() - lastAccRefresh[emKey] > 15000)) {
                        void fetchState(true, true, em);
                    }
                };
                item.onmouseenter = showFly; item.onmouseleave = () => { hTimer = setTimeout(() => fly?.classList.remove("visible"), 350); };
                item.querySelector(".agy-view-usage-link")?.addEventListener("click", (e) => { e.stopPropagation(); if (hTimer) clearTimeout(hTimer); if (em) delete lastAccRefresh[em.toLowerCase()]; showFly(); });
                item.onclick = async (e) => {
                    if (e.target.closest(".agy-view-usage-link, .agy-usage-flyout")) return; e.stopPropagation();
                    if (em) {
                        let bindRes = null;
                        const b = state.bindings?.[cascadeId];
                        const curMod = (typeof b === "object" ? b?.model : null) || lastSavedModels[cascadeId] || '';
                        try {
                            const r = await fetch(apiH() + "/api/multi-account/bind", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ cascadeId, email: em, model: curMod, active: true }) });
                            bindRes = await r.json();
                        } catch (_) {}
                        if (bindRes && bindRes.skipped && bindRes.unhealthy) {
                            toast(`⚠ ${em.split("@")[0]}: ${bindRes.reason || 'unhealthy'} (auto-routing kept)`);
                            await fetchState();
                        } else {
                            try { if (window.antigravityMultiAccount) await Promise.race([window.antigravityMultiAccount.bindCascade?.(cascadeId, em), new Promise(r => setTimeout(r, 200))]); } catch (_) {}
                            if (!state.bindings) state.bindings = {};
                            state.bindings[cascadeId] = { email: em, model: curMod };
                            state.active_default = em; state.bindings.__active_account = em;
                            lastActiveEmail = em;
                            window.dispatchEvent(new CustomEvent('antigravity:account-switched', { detail: { email: em, cascadeId } }));
                            try { if (window.__antigravityRefreshModels) void window.__antigravityRefreshModels(); } catch (_) {}
                            render(); toast(`✓ Switched chat to ${em.split("@")[0]}`);
                            setTimeout(() => {
                                void handleChatModelRestoration(cascadeId);
                            }, 250);
                        }
                    }
                    dd.classList.remove("open"); fly?.classList.remove("visible");
                };
            });
            if (fly) { fly.onmouseenter = () => { if (hTimer) clearTimeout(hTimer); }; fly.onmouseleave = () => { hTimer = setTimeout(() => fly?.classList.remove("visible"), 350); }; }
            document.getElementById("agy-acc-add")?.addEventListener("click", async (e) => {
                e.stopPropagation();
                toast("Opening browser sign-in...");
                let launched = false;
                if (window.antigravityMultiAccount?.startLogin) {
                    try {
                        const res = await window.antigravityMultiAccount.startLogin();
                        if (res) launched = true;
                    } catch (_) {}
                }
                if (!launched) {
                    try {
                        const res = await fetch(apiH() + "/api/multi-account/login", { method: "POST" });
                        if (res.ok) launched = true;
                    } catch (_) {}
                }
                if (!launched) {
                    alert("Could not start login automatically. Please run:\nmanage-antigravity.sh multi-account login");
                    return;
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
            document.getElementById("agy-acc-ref")?.addEventListener("click", async (e) => { e.stopPropagation(); lastAccRefresh = {}; await fetchState(true, true); toast("Refreshed limits"); });
        } catch (_) {}
    }
    function persistChatModel(cid, curModel) {
        if (!cid || isDraftId(cid) || !curModel) return;
        const b = state.bindings?.[cid];
        const saved = typeof b === "object" ? b?.model : null;
        if (curModel === saved) return;
        lastSavedModels[cid] = curModel;
        const boundEmail = typeof b === "object" ? b?.email : b;
        const curEmail = (boundEmail && boundEmail !== "Account") ? boundEmail : getActive()?.email;
        if (!state.bindings) state.bindings = {};
        if (typeof state.bindings[cid] === "object") {
            state.bindings[cid].model = curModel;
        } else {
            state.bindings[cid] = { email: state.bindings[cid] || curEmail, model: curModel };
        }
        void fetch(apiH() + "/api/multi-account/bind", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ cascadeId: cid, email: curEmail, model: curModel })
        });
    }
    document.addEventListener("pointerdown", (e) => {
        if (e.target?.closest?.('[data-testid="model-selector-trigger"], [role="menuitem"], [role="option"], [data-radix-collection-item], [data-radix-menu-content], [data-radix-popper-content-wrapper]')) {
            lastUserModelClickTs = Date.now();
            lastUserModelClickCid = cascadeId;
        }
    }, true);
    function scheduleRender() { if (!rTimer) rTimer = setTimeout(() => { rTimer = null; render(); }, 60); } window.__antigravityRenderSelector = scheduleRender;
    document.addEventListener("click", (e) => {
        const dd = document.getElementById("agy-acc-dd"), pill = document.getElementById("antigravity-account-pill");
        if (dd && pill && !pill.contains(e.target)) { dd.classList.remove("open"); document.getElementById("agy-flyout")?.classList.remove("visible"); }
        const isNavClick = Boolean(e.target?.closest?.('[data-testid*="conversation"], [class*="sidebar"], [data-testid="new-conversation-button"], [aria-label*="New Chat" i], [title*="New Chat" i]'));
        if (isNavClick) {
            if (e.target.closest('[data-testid="new-conversation-button"], [aria-label*="New Chat" i], [title*="New Chat" i]')) {
                const cv = document.querySelector('[data-testid="conversation-view"]');
                if (cv?.dataset?.agyDraftId) delete cv.dataset.agyDraftId;
                if (cv?.dataset?.agySessionId) delete cv.dataset.agySessionId;
            }
            scheduleRender(); setTimeout(() => { scheduleRender(); void fetchState(false); }, 150);
            return;
        }
        if (pill?.contains?.(e.target) || isTypingEl(e.target)) return;
        const cidAtClick = cascadeId;
        setTimeout(() => {
            if (isRestoring || cascadeId !== cidAtClick) return;
            const curModel = window.__antigravityGetSelectedModel?.();
            persistChatModel(cidAtClick, curModel);
        }, 350);
    });
    const hookState = (fn) => function() { const r = fn.apply(this, arguments); scheduleRender(); void fetchState(false); return r; };
    if (history.pushState) history.pushState = hookState(history.pushState); if (history.replaceState) history.replaceState = hookState(history.replaceState);
    ['popstate', 'hashchange'].forEach(ev => window.addEventListener(ev, () => { scheduleRender(); void fetchState(false); }));
    window.addEventListener('focus', async () => {
        scheduleRender();
        await fetchState(false);
        if (typeof document.hasFocus === "function" && !document.hasFocus()) return;
        const active = getActive();
        if (active?.email && active.email !== "Account" && state.active_default && active.email.toLowerCase() !== state.active_default.toLowerCase()) {
            lastActiveEmail = active.email;
            fetch(apiH() + "/api/multi-account/set-active", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ cascadeId, email: active.email }) })
                .then(() => notifyAccountSwitch(active.email, cascadeId, 'window-focus'))
                .catch(() => {});
        }
    });
    window.addEventListener("resize", updateDdPos);
    document.addEventListener("keydown", (e) => {
        if (e.key === "F5" && !e.ctrlKey && !e.metaKey && !e.shiftKey) { render(); void fetchState(true); return; }
        if (!e.ctrlKey && !e.metaKey && !e.altKey) lastTypingTs = Date.now();
    }, { passive: true, capture: true });
    document.addEventListener("input", () => { lastTypingTs = Date.now(); }, { passive: true, capture: true });

    let moTimer = null;
    function checkPillAndCascade() {
        const p = document.getElementById("antigravity-account-pill");
        if (Date.now() - lastTypingTs < 600 && p && p.isConnected !== false) return;
        const t = window.__antigravityFindTarget?.();
        const c = window.__antigravityDetectCascadeId?.(t?.target) || "default";
        if (!p || !document.body?.contains(p) || (t?.target && p.parentElement !== t.target) || c !== cascadeId) {
            scheduleRender();
            if (c !== cascadeId) void fetchState();
        } else if (!isRestoring && c && !isDraftId(c)) {
            const curModel = window.__antigravityGetSelectedModel?.();
            const b = state.bindings?.[c];
            const saved = typeof b === "object" ? b?.model : null;
            const userSelectedModelRecently = (lastUserModelClickCid === c) && (Date.now() - lastUserModelClickTs < 3000);
            if (curModel && curModel !== saved && userSelectedModelRecently) {
                persistChatModel(c, curModel);
            }
        }
    }

    try {
        const mo = new MutationObserver((mutations) => {
            if (Date.now() - lastTypingTs < 700) {
                const p = document.getElementById("antigravity-account-pill");
                if (p && p.isConnected !== false) return;
            }
            let isRelevant = false;
            for (let i = 0; i < mutations.length; i++) {
                const target = mutations[i].target;
                if (!target) continue;
                const el = target.nodeType === 1 ? target : target.parentElement;
                if (el?.closest?.('textarea, input, [contenteditable], .monaco-editor, [data-lexical-editor], [data-testid*="input"], [role="textbox"], .agy-toast, .agy-usage-flyout, #antigravity-account-pill')) {
                    continue;
                }
                isRelevant = true;
                break;
            }
            if (!isRelevant) return;

            if (moTimer) clearTimeout(moTimer);
            moTimer = setTimeout(() => {
                moTimer = null;
                checkPillAndCascade();
            }, 300);
        });
        if (document.body) mo.observe(document.body, { childList: true, subtree: true });
    } catch (_) {}

    setInterval(() => {
        if (Date.now() - lastTypingTs < 1000 || isTypingEl(document.activeElement)) {
            return;
        }
        checkPillAndCascade();
    }, 2500);

    render(); fetchState(false);
})();
