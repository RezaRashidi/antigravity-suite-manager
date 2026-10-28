"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
/** Custom-model UI, appended to the vendor preload. Sandboxed preloads require Electron only. */
const electron_1 = require("electron");
const storageAPI = {
    getCustomModels: () => electron_1.ipcRenderer.invoke('storage:get-custom-models'),
    saveCustomModel: (model) => electron_1.ipcRenderer.invoke('storage:save-custom-model', model),
    deleteCustomModel: (name) => electron_1.ipcRenderer.invoke('storage:delete-custom-model', name),
    testModelConnection: (model) => electron_1.ipcRenderer.invoke('storage:test-model-connection', model),
    getPresets: () => electron_1.ipcRenderer.invoke('storage:get-provider-presets'),
    discoverModels: (params) => electron_1.ipcRenderer.invoke('storage:discover-models', params),
};
window.addEventListener('DOMContentLoaded', () => {
    let modelList = [];
    let renderVersion = 0;
    let searchTerm = '';
    let cancelModalOperation;
    const requireSuccess = (result) => {
        if (!result?.success)
            throw new Error(result?.error || 'The operation could not be completed.');
        return result;
    };
    function element(tag, className = '', text = '') {
        const node = document.createElement(tag);
        node.className = className;
        if (text)
            node.textContent = text;
        return node;
    }
    function setStatus(target, text, error = false) {
        target.textContent = text;
        target.className = `agy-status${error ? ' agy-error' : ''}`;
    }
    function statusNode() {
        const node = element('div', 'agy-status');
        node.setAttribute('role', 'status');
        node.setAttribute('aria-live', 'polite');
        return node;
    }
    function button(label, action, status, primary = false) {
        const node = element('button', `agy-btn${primary ? ' agy-primary' : ''}`, label);
        node.type = 'button';
        node.addEventListener('click', async () => {
            if (node.disabled)
                return;
            node.disabled = true;
            try {
                await action();
            }
            catch (error) {
                const target = status || document.getElementById('agy-main-status');
                if (target)
                    setStatus(target, error instanceof Error ? error.message : String(error), true);
            }
            finally {
                node.disabled = false;
            }
        });
        return node;
    }
    function field(parent, title, id, value = '', type = 'text') {
        const label = element('label', 'agy-field');
        label.htmlFor = id;
        label.append(element('span', '', title));
        const input = element('input');
        input.id = id;
        input.type = type;
        input.value = value;
        input.autocomplete = 'off';
        label.append(input);
        parent.append(label);
        return input;
    }
    function selectField(parent, title, id, options, value) {
        const label = element('label', 'agy-field');
        label.htmlFor = id;
        label.append(element('span', '', title));
        const select = element('select');
        select.id = id;
        for (const [key, caption] of options) {
            const option = element('option', '', caption);
            option.value = key;
            select.append(option);
        }
        select.value = value;
        label.append(select);
        parent.append(label);
        return select;
    }
    function jsonField(parent, title, id, value) {
        const label = element('label', 'agy-field');
        label.htmlFor = id;
        label.append(element('span', '', title));
        const input = element('textarea');
        input.id = id;
        input.rows = 3;
        input.spellcheck = false;
        input.value = value ? JSON.stringify(value, null, 2) : '';
        input.placeholder = '{}';
        label.append(input);
        parent.append(label);
        return input;
    }
    function readJson(input, title) {
        if (!input.value.trim())
            return undefined;
        try {
            const value = JSON.parse(input.value);
            if (!value || Array.isArray(value) || typeof value !== 'object')
                throw new Error();
            return value;
        }
        catch {
            throw new Error(`${title} must be a JSON object.`);
        }
    }
    function readNumber(input, title, minimum = 0) {
        if (!input.value.trim())
            return undefined;
        const value = Number(input.value);
        if (!Number.isSafeInteger(value) || value < minimum)
            throw new Error(`${title} must be a whole number of at least ${minimum}.`);
        return value;
    }
    function validUrl(value) {
        let url;
        try {
            url = new URL(value.trim());
        }
        catch {
            throw new Error('Enter a complete http:// or https:// API URL.');
        }
        if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password)
            throw new Error('Use an HTTP or HTTPS URL. Enter credentials in the API key field.');
        return value.trim();
    }
    function installStyles() {
        if (document.getElementById('agy-manager-style'))
            return;
        const style = element('style');
        style.id = 'agy-manager-style';
        style.textContent = `
      #agy-custom-models-section,#agy-modal-overlay{font:13px/1.5 'Vazirmatn',-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#e4e4e7;box-sizing:border-box}
      #agy-custom-models-section *,#agy-modal-overlay *{box-sizing:border-box}
      #agy-custom-models-section [hidden],#agy-modal-overlay [hidden]{display:none!important}
      #agy-custom-models-section{margin:24px 0;padding:20px;border:1px solid #303036;border-radius:12px;background:#18181b;min-width:0}
      #agy-custom-models-section h2,#agy-modal-overlay h2{font-size:18px;margin:0;color:#fafafa;font-weight:600;unicode-bidi:plaintext;text-align:start}
      #agy-custom-models-section h3{font-size:13px;margin:0;color:#f4f4f5;unicode-bidi:plaintext;text-align:start}
      .agy-toolbar,.agy-actions,.agy-group-heading,.agy-row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
      .agy-toolbar{justify-content:space-between;margin-bottom:12px}.agy-actions{margin:10px 0}
      .agy-muted{color:#a1a1aa;font-size:12px;overflow-wrap:anywhere;unicode-bidi:plaintext;text-align:start}.agy-group{margin-top:16px;border-top:1px solid #303036;padding-top:14px}
      .agy-group-heading{justify-content:space-between}.agy-row{justify-content:space-between;border:1px solid #303036;border-radius:8px;padding:12px;margin-top:8px;background:#202024}
      .agy-row-info{flex:1;min-width:150px;overflow-wrap:anywhere;unicode-bidi:plaintext;text-align:start}.agy-row[data-enabled="false"] .agy-row-info{opacity:.55}
      #agy-custom-models-section .agy-btn,#agy-modal-overlay .agy-btn{appearance:none;font:inherit;color:#e4e4e7;background:#27272c;border:1px solid #414149;border-radius:6px;padding:6px 10px;cursor:pointer;white-space:nowrap}
      #agy-custom-models-section .agy-primary,#agy-modal-overlay .agy-primary{background:#e4e4e7;color:#18181b;border-color:#e4e4e7;font-weight:600}
      #agy-custom-models-section .agy-btn:hover,#agy-modal-overlay .agy-btn:hover{filter:brightness(1.12)}
      #agy-custom-models-section .agy-btn:disabled,#agy-modal-overlay .agy-btn:disabled{opacity:.5;cursor:wait}
      #agy-custom-models-section :focus-visible,#agy-modal-overlay :focus-visible{outline:2px solid #a78bfa;outline-offset:3px}
      .agy-status{color:#86efac;font-size:12px;margin-top:8px;white-space:pre-wrap;overflow-wrap:anywhere;unicode-bidi:plaintext;text-align:start}.agy-status:empty{display:none}.agy-error{color:#fca5a5}
      .agy-field{display:flex;flex-direction:column;gap:5px;margin-bottom:12px;min-width:0;color:#a1a1aa;unicode-bidi:plaintext;text-align:start}
      #agy-custom-models-section input,#agy-modal-overlay input,#agy-modal-overlay select,#agy-modal-overlay textarea{font:inherit;width:100%;background:#25252a;border:1px solid #414149;border-radius:6px;color:#fafafa;padding:8px 10px;min-width:0;unicode-bidi:plaintext;text-align:start}
      #agy-modal-overlay textarea{font-family:ui-monospace,Menlo,Monaco,monospace;resize:vertical;direction:ltr}#agy-modal-overlay input[type=checkbox]{width:auto;accent-color:#a78bfa}
      #agy-modal-overlay{position:fixed;inset:0;z-index:999999;background:#000a;display:flex;align-items:center;justify-content:center;padding:20px}
      #agy-modal-card{width:680px;max-width:100%;max-height:90vh;overflow:auto;background:#18181b;border:1px solid #414149;border-radius:12px;padding:24px;box-shadow:0 24px 80px #0008}
      .agy-grid{display:grid;grid-template-columns:1fr 1fr;gap:0 14px}.agy-discovery{max-height:240px;overflow:auto;margin:12px 0}
      .agy-choice{display:flex;gap:10px;align-items:center;padding:7px 0;overflow-wrap:anywhere;unicode-bidi:plaintext;text-align:start}.agy-choice span{min-width:0}
      #agy-modal-overlay details{border:1px solid #303036;border-radius:8px;margin:12px 0;padding:12px}#agy-modal-overlay summary{cursor:pointer;margin-bottom:10px;font-weight:500;unicode-bidi:plaintext;text-align:start}
      .agy-proxy-pill{display:inline-flex;align-items:center;gap:6px;padding:3px 9px;border-radius:12px;font-size:11px;font-weight:500;border:1px solid #303036;background:#202024;user-select:none}
      .agy-proxy-pill.active{border-color:#22c55e55;color:#86efac;background:#052e1666}
      .agy-proxy-pill.direct{border-color:#71717a55;color:#a1a1aa;background:#27272a55}
      .agy-dot{width:6px;height:6px;border-radius:50%;background:currentColor;display:inline-block}
      @media(max-width:600px){.agy-grid{grid-template-columns:1fr}#agy-modal-card{padding:16px}.agy-row .agy-actions{width:100%}}
    `;
        document.head.append(style);
    }
    function openModal(title) {
        cancelModalOperation?.();
        cancelModalOperation = undefined;
        document.getElementById('agy-modal-overlay')?.remove();
        const previousFocus = document.activeElement;
        const overlay = element('div');
        overlay.id = 'agy-modal-overlay';
        const card = element('div');
        card.id = 'agy-modal-card';
        card.setAttribute('role', 'dialog');
        card.setAttribute('aria-modal', 'true');
        card.setAttribute('aria-labelledby', 'agy-modal-title');
        const header = element('div', 'agy-toolbar');
        const heading = element('h2', '', title);
        heading.id = 'agy-modal-title';
        const close = () => {
            cancelModalOperation?.();
            cancelModalOperation = undefined;
            overlay.remove();
            if (previousFocus?.isConnected)
                previousFocus.focus();
        };
        header.append(heading, button('Close', close));
        const body = element('div');
        const status = statusNode();
        card.append(header, body, status);
        overlay.append(card);
        overlay.addEventListener('click', (event) => {
            if (event.target === overlay)
                close();
        });
        overlay.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                event.preventDefault();
                close();
            }
            if (event.key !== 'Tab')
                return;
            const controls = Array.from(card.querySelectorAll('button:not(:disabled),input:not(:disabled),select,textarea,summary'));
            const first = controls[0], last = controls[controls.length - 1];
            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last?.focus();
            }
            else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first?.focus();
            }
        });
        document.body.append(overlay);
        header.querySelector('button')?.focus();
        return { body, status, close };
    }
    function createGoogleAccountPanel(parent, initialAccounts, modelName) {
        let accounts = initialAccounts.map((account) => ({ ...account }));
        const locallyEdited = new Set();
        const panel = element('details');
        panel.open = true;
        panel.append(element('summary', '', 'Google accounts'));
        panel.append(element('p', 'agy-muted', 'Add accounts you own using your Desktop OAuth client or a credential file. Save the model to retain changes. Existing secrets stay masked.'));
        const list = element('div');
        list.id = 'agy-google-accounts-list';
        const editor = element('div');
        const status = statusNode();
        const randomId = () => `account-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
        const addAccount = (account) => {
            if (!account.id || (!account.refreshToken && !account.accessToken))
                throw new Error('An account needs an ID and a refresh token or access token.');
            if (account.refreshToken && !account.clientId)
                throw new Error('An OAuth client ID is required with a refresh token.');
            const index = accounts.findIndex((value) => value.id === account.id);
            if (index < 0) {
                if (accounts.length >= 50)
                    throw new Error('A model can contain at most 50 Google accounts.');
                accounts.push(account);
            }
            else
                accounts[index] = account;
            locallyEdited.add(account.id);
            renderAccounts();
        };
        function editAccount(account) {
            editor.replaceChildren();
            editor.append(element('h3', '', account ? 'Edit account' : 'Add account credentials'));
            const accountGrid = element('div', 'agy-grid');
            const id = field(accountGrid, 'Account ID', 'agy-account-id', account?.id || randomId());
            const label = field(accountGrid, 'Label', 'agy-account-label', account?.label || '');
            const clientId = field(accountGrid, 'Desktop OAuth client ID', 'agy-account-client-id', account?.clientId || '');
            const clientSecret = field(accountGrid, 'OAuth client secret (if required)', 'agy-account-client-secret', account?.clientSecret || '', 'password');
            const refresh = field(accountGrid, 'Refresh token', 'agy-account-refresh-token', account?.refreshToken || '', 'password');
            const access = field(accountGrid, 'Access token (optional with refresh token)', 'agy-account-access-token', account?.accessToken || '', 'password');
            const expires = field(accountGrid, 'Access token expiry (Unix milliseconds)', 'agy-account-expires-at', account?.expiresAt != null ? String(account.expiresAt) : '', 'number');
            const project = field(accountGrid, 'Cloud project (optional)', 'agy-account-project', account?.project || '');
            editor.append(accountGrid);
            const actions = element('div', 'agy-actions');
            actions.append(button('Apply account', () => {
                const accountId = id.value.trim();
                if (account && accountId !== account.id && accounts.some((value) => value.id === accountId))
                    throw new Error('That account ID already exists.');
                const updated = {
                    id: accountId,
                    label: label.value.trim(),
                    clientId: clientId.value.trim(),
                    clientSecret: clientSecret.value.trim(),
                    refreshToken: refresh.value.trim(),
                    accessToken: access.value.trim(),
                    expiresAt: readNumber(expires, 'Token expiry', 1),
                    project: project.value.trim(),
                    enabled: account?.enabled !== false,
                };
                // IDs bind masked secrets to their stored record, so changing an existing ID requires fresh credentials.
                if (account &&
                    accountId !== account.id &&
                    [updated.refreshToken, updated.accessToken, updated.clientSecret].some((value) => value?.includes('***')))
                    throw new Error('Keep the account ID unchanged when using masked credentials.');
                addAccount(updated);
                if (account && accountId !== account.id)
                    accounts = accounts.filter((value) => value.id !== account.id);
                editor.replaceChildren();
                renderAccounts();
                setStatus(status, 'Account updated. Save the model to keep these changes.');
            }, status), button('Cancel account edit', () => editor.replaceChildren(), status));
            editor.append(actions);
        }
        function renderAccounts() {
            list.replaceChildren();
            if (!accounts.length)
                list.append(element('p', 'agy-muted', 'No Google accounts configured.'));
            for (const account of accounts) {
                const row = element('div', 'agy-row');
                const info = element('div', 'agy-row-info');
                info.append(element('strong', '', account.label || account.id), element('div', 'agy-muted', `${account.id} · ${account.enabled === false ? 'Disabled' : 'Enabled'}${account.project ? ` · ${account.project}` : ''}`));
                const actions = element('div', 'agy-actions');
                actions.append(button('Edit account', () => editAccount(account), status), button(account.enabled === false ? 'Enable account' : 'Disable account', () => {
                    account.enabled = account.enabled === false;
                    renderAccounts();
                }, status), button('Test account', async () => {
                    setStatus(status, 'Checking account access and quota…');
                    const result = await electron_1.ipcRenderer.invoke('storage:google-test-account', modelName && !locallyEdited.has(account.id)
                        ? { modelName, accountId: account.id }
                        : { account, ...(modelName ? { modelName } : {}) });
                    requireSuccess(result);
                    setStatus(status, result.message ||
                        (result.quota
                            ? `Account verified. Quota: ${JSON.stringify(result.quota)}`
                            : 'Account verified. Generation was not tested.'));
                }, status), button('Remove account', () => {
                    accounts = accounts.filter((value) => value.id !== account.id);
                    locallyEdited.delete(account.id);
                    renderAccounts();
                }, status));
                row.append(info, actions);
                list.append(row);
            }
        }
        const actions = element('div', 'agy-actions');
        actions.append(button('Add account', () => editAccount(), status), button('Pool status', async () => {
            const result = await electron_1.ipcRenderer.invoke('storage:google-pool-status');
            if (result?.success === false)
                requireSuccess(result);
            setStatus(status, JSON.stringify(result, null, 2));
        }, status));
        const login = element('details');
        login.append(element('summary', '', 'Sign in with your OAuth client'));
        login.append(element('p', 'agy-muted', 'Enter a Desktop OAuth client from your Google Cloud project. The browser opens only when you choose Sign in. Your project and account must be eligible for Cloud Code.'));
        const loginLabel = field(login, 'Account label', 'agy-google-login-label');
        const loginClient = field(login, 'Desktop OAuth client ID', 'agy-google-login-client-id');
        const loginSecret = field(login, 'OAuth client secret (if required)', 'agy-google-login-client-secret', '', 'password');
        const loginActions = element('div', 'agy-actions');
        loginActions.append(button('Sign in with Google', async () => {
            if (!loginClient.value.trim())
                throw new Error('Enter your Desktop OAuth client ID.');
            const cancel = () => {
                void electron_1.ipcRenderer.invoke('storage:google-login-cancel').catch(() => { });
            };
            cancelModalOperation = cancel;
            setStatus(status, 'Complete consent in your browser. This login expires after two minutes.');
            try {
                const result = await electron_1.ipcRenderer.invoke('storage:google-login', {
                    clientId: loginClient.value.trim(),
                    clientSecret: loginSecret.value.trim() || undefined,
                    label: loginLabel.value.trim() || undefined,
                });
                requireSuccess(result);
                if (!panel.isConnected)
                    return;
                if (!result.account)
                    throw new Error('Google login did not return an account.');
                addAccount(result.account);
                loginSecret.value = '';
                setStatus(status, 'Account authorized. Save the model within 10 minutes to retain it; otherwise sign in again.');
            }
            finally {
                if (cancelModalOperation === cancel)
                    cancelModalOperation = undefined;
            }
        }, status), button('Cancel Google login', async () => {
            requireSuccess(await electron_1.ipcRenderer.invoke('storage:google-login-cancel'));
            cancelModalOperation = undefined;
            setStatus(status, 'Google login cancelled.');
        }, status));
        login.append(loginActions);
        const importer = element('details');
        importer.append(element('summary', '', 'Import account credentials'));
        importer.append(element('p', 'agy-muted', 'Import your own authorized_user JSON, an account object, or an accounts array. Importing does not open a browser or make network requests.'));
        const accountJson = jsonField(importer, 'Account JSON', 'agy-google-account-json', undefined);
        const file = field(importer, 'Credential JSON file', 'agy-google-account-file', '', 'file');
        file.accept = '.json,application/json';
        file.addEventListener('change', async () => {
            try {
                const selected = file.files?.[0];
                if (!selected)
                    return;
                if (selected.size > 512 * 1024)
                    throw new Error('Account files must be smaller than 512 KB.');
                accountJson.value = await selected.text();
            }
            catch (error) {
                setStatus(status, String(error), true);
            }
        });
        importer.append(button('Import accounts', () => {
            let data;
            try {
                data = JSON.parse(accountJson.value);
            }
            catch {
                throw new Error('Account credentials must be valid JSON.');
            }
            const root = data;
            const values = Array.isArray(data) ? data : root?.accounts || root?.googleAccounts || [data];
            if (!Array.isArray(values) || !values.length || values.length + accounts.length > 50)
                throw new Error('Import between 1 and 50 accounts.');
            const incoming = values.map((value) => {
                if (!value || typeof value !== 'object' || Array.isArray(value))
                    throw new Error('Each account must be a JSON object.');
                const entry = value;
                const text = (key, alternate = key) => String(entry[key] || entry[alternate] || '');
                const account = {
                    id: text('id') || randomId(),
                    label: text('label', 'accountEmail') || 'Imported account',
                    refreshToken: text('refreshToken', 'refresh_token'),
                    accessToken: text('accessToken', 'access_token'),
                    clientId: text('clientId', 'client_id'),
                    clientSecret: text('clientSecret', 'client_secret'),
                    project: text('project', 'quota_project_id'),
                    enabled: entry.enabled !== false,
                    ...(entry.expiresAt != null ? { expiresAt: Number(entry.expiresAt) } : {}),
                };
                if (!account.refreshToken && !account.accessToken)
                    throw new Error('An imported account must contain a refresh token or access token.');
                if (account.refreshToken && !account.clientId)
                    throw new Error('An imported refresh token requires its OAuth client ID.');
                return account;
            });
            for (const account of incoming)
                addAccount(account);
            accountJson.value = '';
            file.value = '';
            setStatus(status, `Imported ${incoming.length} accounts. Save the model to encrypt and retain them.`);
        }, status));
        panel.append(list, actions, editor, login, importer, status);
        parent.append(panel);
        renderAccounts();
        return () => accounts.map((account) => ({ ...account }));
    }
    function findRefreshButton() {
        return (Array.from(document.querySelectorAll('button')).find((node) => !node.closest('#agy-custom-models-section') &&
            (node.textContent?.trim() === 'Refresh' ||
                /refresh quota/i.test(`${node.getAttribute('aria-label') || ''} ${node.title || ''}`))) || null);
    }
    async function modelsChanged() {
        customModelsCache.ts = 0;
        await renderCustomModelsList();
        findRefreshButton()?.click();
    }
    function uniqueName(base) {
        let name = base, index = 2;
        while (modelList.some((model) => model.name === name))
            name = `${base}-${index++}`;
        return name;
    }
    async function renderCustomModelsList() {
        const target = document.getElementById('agy-custom-models-content');
        if (!target)
            return;
        const version = ++renderVersion;
        try {
            const models = await storageAPI.getCustomModels();
            if (version !== renderVersion || !target.isConnected)
                return;
            modelList = models;
            target.replaceChildren();
            const groups = new Map();
            for (const model of models) {
                if (searchTerm &&
                    !`${model.displayName} ${model.name} ${model.externalModelName} ${model.provider}`
                        .toLowerCase()
                        .includes(searchTerm))
                    continue;
                const key = `${model.provider}\n${model.apiUrl}`;
                groups.set(key, [...(groups.get(key) || []), model]);
            }
            if (!groups.size)
                target.append(element('p', 'agy-muted', models.length
                    ? 'No models match this search.'
                    : 'Add a provider model, discover a local server, or import a configuration to get started.'));
            for (const models of groups.values()) {
                const first = models[0];
                const group = element('section', 'agy-group');
                const header = element('div', 'agy-group-heading');
                const heading = element('div');
                heading.append(element('h3', '', `${first.provider} · ${models.filter((model) => model.enabled !== false).length}/${models.length} enabled`), element('div', 'agy-muted', first.apiUrl));
                const groupStatus = statusNode();
                const actions = element('div', 'agy-actions');
                actions.append(button('Discover models', () => openModelModal(first, 'discover'), groupStatus));
                const allEnabled = models.every((model) => model.enabled !== false);
                actions.append(button(allEnabled ? 'Disable group' : 'Enable group', async () => {
                    for (const model of models)
                        requireSuccess(await storageAPI.saveCustomModel({ ...model, enabled: !allEnabled }));
                    await modelsChanged();
                }, groupStatus));
                header.append(heading, actions);
                group.append(header, groupStatus);
                for (const model of models) {
                    const row = element('div', 'agy-row');
                    row.dataset.enabled = String(model.enabled !== false);
                    const info = element('div', 'agy-row-info');
                    info.append(element('strong', '', model.displayName || model.name), element('div', 'agy-muted', model.externalModelName));
                    const rowStatus = statusNode();
                    info.append(rowStatus);
                    const actions = element('div', 'agy-actions');
                    actions.append(button(model.enabled === false ? 'Enable' : 'Disable', async () => {
                        requireSuccess(await storageAPI.saveCustomModel({ ...model, enabled: model.enabled === false }));
                        await modelsChanged();
                    }, rowStatus), button('Test', async () => {
                        setStatus(rowStatus, 'Testing…');
                        const result = requireSuccess(await storageAPI.testModelConnection(model));
                        setStatus(rowStatus, result.message || 'Connection successful.');
                    }, rowStatus), button('Edit', () => openModelModal(model, 'edit'), rowStatus), button('Duplicate', () => openModelModal(model, 'duplicate'), rowStatus), button('Delete', async () => {
                        if (!window.confirm(`Delete “${model.displayName || model.name}”?`))
                            return;
                        requireSuccess(await storageAPI.deleteCustomModel(model.name));
                        await modelsChanged();
                    }, rowStatus));
                    row.append(info, actions);
                    group.append(row);
                }
                target.append(group);
            }
        }
        catch (error) {
            setStatus(target, error instanceof Error ? error.message : 'Could not load custom models.', true);
        }
    }
    async function openModelModal(existing, mode = 'edit') {
        const { body, status, close } = openModal(mode === 'duplicate'
            ? 'Duplicate model'
            : mode === 'discover'
                ? 'Discover provider models'
                : existing
                    ? 'Edit model'
                    : 'Add custom model');
        try {
            const presets = await storageAPI.getPresets();
            if (!body.isConnected)
                return;
            const providers = [...presets];
            if (existing && !providers.some((preset) => preset.id === existing.provider))
                providers.push({
                    id: existing.provider,
                    label: existing.provider,
                    defaultUrl: existing.apiUrl,
                    apiFormat: existing.apiFormat || 'openai',
                    keyRequired: false,
                });
            if (!providers.length)
                throw new Error('Provider presets are unavailable. Close this dialog and try again.');
            const provider = selectField(body, 'Provider', 'agy-provider', providers.map((preset) => [preset.id, preset.label]), existing?.provider || providers[0].id);
            const preset = () => providers.find((value) => value.id === provider.value) || providers[0];
            const apiUrl = field(body, 'API URL', 'agy-api-url', existing?.apiUrl || preset().defaultUrl, 'url');
            const apiKey = field(body, 'API key', 'agy-api-key', existing?.apiKey === 'none' ? '' : existing?.apiKey || '', 'password');
            apiKey.placeholder = preset().keyRequired ? 'Enter provider API key' : 'Optional for local servers';
            const apiFormat = selectField(body, 'API format', 'agy-api-format', [
                ['openai', 'OpenAI compatible'],
                ['anthropic', 'Anthropic Messages'],
                ['google', 'Google Gemini'],
            ], existing?.apiFormat || preset().apiFormat);
            const grid = element('div', 'agy-grid');
            const modelId = field(grid, 'Provider model ID', 'agy-model-id', mode === 'discover' ? '' : existing?.externalModelName || '');
            const displayName = field(grid, 'Display name', 'agy-display-name', mode === 'duplicate'
                ? `${existing?.displayName || existing?.externalModelName || ''} copy`
                : mode === 'discover'
                    ? ''
                    : existing?.displayName || '');
            body.append(grid);
            const name = field(body, 'Configuration name (unique)', 'agy-model-name', mode === 'duplicate' ? uniqueName(`${existing?.name}-copy`) : mode === 'discover' ? '' : existing?.name || '');
            name.placeholder = 'Generated from provider and model ID when left blank';
            const description = field(body, 'Description', 'agy-description', String(existing?.description || ''));
            const googleConfig = element('div');
            googleConfig.id = 'agy-google-account-config';
            const googleProject = field(googleConfig, 'Default Cloud Code project (optional)', 'agy-google-project', String(existing?.googleProject || ''));
            const initialPool = existing?.googlePool;
            const poolGrid = element('div', 'agy-grid');
            const poolStrategy = selectField(poolGrid, 'Account selection', 'agy-google-pool-strategy', [
                ['round-robin', 'Round robin'],
                ['least-loaded', 'Least loaded'],
                ['quota', 'Remaining quota'],
            ], initialPool?.strategy || 'least-loaded');
            const poolConcurrency = field(poolGrid, 'Maximum requests per account', 'agy-google-pool-concurrency', String(initialPool?.maxConcurrency || 2), 'number');
            const poolCooldown = field(poolGrid, 'Account cooldown (milliseconds)', 'agy-google-pool-cooldown', String(initialPool?.cooldownMs || 60000), 'number');
            googleConfig.append(poolGrid);
            const readAccounts = createGoogleAccountPanel(googleConfig, Array.isArray(existing?.googleAccounts) ? existing.googleAccounts : [], existing?.name);
            const updateGoogleVisibility = () => {
                const isGoogle = provider.value === 'google-cloudcode';
                googleConfig.hidden = !isGoogle;
                apiKey.closest('label').hidden = isGoogle;
                apiFormat.closest('label').hidden = isGoogle;
            };
            updateGoogleVisibility();
            body.append(googleConfig);
            const advanced = element('details');
            advanced.append(element('summary', '', 'Advanced settings'));
            const advancedGrid = element('div', 'agy-grid');
            const effort = selectField(advancedGrid, 'Reasoning effort', 'agy-reasoning-effort', ['', 'none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max'].map((value) => [
                value,
                value || 'Provider default',
            ]), String(existing?.reasoningEffort || ''));
            const thinking = field(advancedGrid, 'Thinking budget (tokens)', 'agy-thinking-budget', existing?.thinkingBudget != null ? String(existing.thinkingBudget) : '', 'number');
            const maxOutput = field(advancedGrid, 'Maximum output tokens', 'agy-max-output', existing?.maxOutputTokens != null ? String(existing.maxOutputTokens) : '', 'number');
            const context = field(advancedGrid, 'Context window (tokens)', 'agy-context-window', existing?.contextWindow != null ? String(existing.contextWindow) : '', 'number');
            const timeout = field(advancedGrid, 'Request timeout (milliseconds)', 'agy-timeout', existing?.timeout != null ? String(existing.timeout) : '', 'number');
            const retries = field(advancedGrid, 'Maximum retries (0–5)', 'agy-max-retries', existing?.maxRetries != null ? String(existing.maxRetries) : '', 'number');
            retries.max = '5';
            const vision = selectField(advancedGrid, 'Image input', 'agy-vision', [
                ['', 'Auto detect'],
                ['true', 'Supported'],
                ['false', 'Unsupported'],
            ], existing?.supportsVision == null ? '' : String(existing.supportsVision));
            const rawUrl = selectField(advancedGrid, 'Endpoint path', 'agy-raw-url', [
                ['false', 'Normalize for provider'],
                ['true', 'Use exactly as entered'],
            ], String(existing?.rawUrl === true));
            const tls = selectField(advancedGrid, 'TLS certificates', 'agy-tls', [
                ['false', 'Verify certificates'],
                ['true', 'Allow self-signed certificates'],
            ], String(existing?.allowUnauthorized === true));
            const enabled = selectField(advancedGrid, 'Model state', 'agy-enabled', [
                ['true', 'Enabled'],
                ['false', 'Disabled'],
            ], String(existing?.enabled !== false));
            advanced.append(advancedGrid);
            const fallbacks = field(advanced, 'Fallback model configuration names (comma separated)', 'agy-fallback-models', Array.isArray(existing?.fallbackModels) ? existing.fallbackModels.join(', ') : '');
            const headers = jsonField(advanced, 'Custom headers (JSON)', 'agy-custom-headers', existing?.customHeaders);
            const extraBody = jsonField(advanced, 'Additional request fields (JSON)', 'agy-extra-body', existing?.extraBody);
            const breaker = existing?.circuitBreaker;
            const breakerGrid = element('div', 'agy-grid');
            const breakerEnabled = selectField(breakerGrid, 'Circuit breaker', 'agy-breaker-enabled', [
                ['', 'Default'],
                ['true', 'Enabled'],
                ['false', 'Disabled'],
            ], breaker?.enabled == null ? '' : String(breaker.enabled));
            const breakerThreshold = field(breakerGrid, 'Failures before cooldown', 'agy-breaker-threshold', breaker?.failureThreshold != null ? String(breaker.failureThreshold) : '', 'number');
            const breakerCooldown = field(breakerGrid, 'Cooldown (milliseconds)', 'agy-breaker-cooldown', breaker?.cooldownMs != null ? String(breaker.cooldownMs) : '', 'number');
            advanced.append(breakerGrid);
            body.append(advanced);
            const discovery = element('div', 'agy-discovery');
            const discoveryFilter = element('div');
            discoveryFilter.hidden = true;
            const discoverySearch = field(discoveryFilter, 'Search provider models', 'agy-discovery-search', '', 'search');
            discoverySearch.placeholder = 'Filter by model name or ID';
            discoverySearch.addEventListener('input', () => showChoices());
            let choices = [];
            const selected = new Set();
            function connection() {
                return {
                    provider: provider.value,
                    apiUrl: validUrl(apiUrl.value),
                    apiKey: apiKey.value.trim() || 'none',
                    apiFormat: apiFormat.value,
                    name: existing?.name,
                    allowUnauthorized: tls.value === 'true',
                    externalModelName: modelId.value.trim(),
                    customHeaders: readJson(headers, 'Custom headers'),
                    rawUrl: rawUrl.value === 'true',
                    ...(provider.value === 'google-cloudcode'
                        ? {
                            googleAccounts: readAccounts(),
                            googleProject: googleProject.value.trim(),
                            googlePool: {
                                strategy: poolStrategy.value,
                                maxConcurrency: readNumber(poolConcurrency, 'Account concurrency', 1),
                                cooldownMs: readNumber(poolCooldown, 'Account cooldown', 1),
                            },
                        }
                        : {}),
                };
            }
            function modelConfig(id, title, localName) {
                if (!id.trim() || /\s/.test(id.trim()))
                    throw new Error('Enter a model ID without spaces.');
                if (preset().keyRequired && !apiKey.value.trim())
                    throw new Error('Enter an API key for this provider.');
                if (provider.value === 'google-cloudcode' && !readAccounts().some((account) => account.enabled !== false))
                    throw new Error('Add and enable at least one Google account.');
                const maxRetries = readNumber(retries, 'Maximum retries');
                if (maxRetries != null && maxRetries > 5)
                    throw new Error('Maximum retries cannot exceed 5.');
                const customHeaders = readJson(headers, 'Custom headers');
                if (customHeaders && Object.values(customHeaders).some((value) => typeof value !== 'string'))
                    throw new Error('Custom header values must be strings.');
                return {
                    ...(mode === 'edit' && existing ? existing : {}),
                    ...connection(),
                    name: localName || name.value.trim() || uniqueName(`models/${provider.value}/${id}`),
                    provider: provider.value,
                    apiUrl: apiUrl.value.trim(),
                    apiKey: apiKey.value.trim() || 'none',
                    externalModelName: id.trim(),
                    displayName: title || id.trim(),
                    description: description.value.trim(),
                    enabled: enabled.value === 'true',
                    apiFormat: apiFormat.value,
                    googleAccounts: provider.value === 'google-cloudcode' ? readAccounts() : undefined,
                    googleProject: provider.value === 'google-cloudcode' ? googleProject.value.trim() || undefined : undefined,
                    googlePool: provider.value === 'google-cloudcode'
                        ? {
                            strategy: poolStrategy.value,
                            maxConcurrency: readNumber(poolConcurrency, 'Account concurrency', 1),
                            cooldownMs: readNumber(poolCooldown, 'Account cooldown', 1),
                        }
                        : undefined,
                    reasoningEffort: effort.value || undefined,
                    thinkingBudget: readNumber(thinking, 'Thinking budget'),
                    maxOutputTokens: readNumber(maxOutput, 'Maximum output tokens', 1),
                    contextWindow: readNumber(context, 'Context window', 1),
                    timeout: readNumber(timeout, 'Timeout', 1),
                    maxRetries,
                    fallbackModels: fallbacks.value
                        .split(',')
                        .map((value) => value.trim())
                        .filter(Boolean),
                    customHeaders,
                    extraBody: readJson(extraBody, 'Additional request fields'),
                    supportsVision: vision.value === '' ? undefined : vision.value === 'true',
                    rawUrl: rawUrl.value === 'true',
                    allowUnauthorized: tls.value === 'true',
                    circuitBreaker: breakerEnabled.value || breakerThreshold.value || breakerCooldown.value
                        ? {
                            enabled: breakerEnabled.value !== 'false',
                            failureThreshold: readNumber(breakerThreshold, 'Failure threshold', 1),
                            cooldownMs: readNumber(breakerCooldown, 'Cooldown', 1),
                        }
                        : undefined,
                    ...(existing?.name && mode === 'edit'
                        ? { originalName: existing.name }
                        : existing?.name
                            ? { copyFrom: existing.name }
                            : {}),
                };
            }
            function showChoices() {
                discovery.replaceChildren();
                discoveryFilter.hidden = !choices.length;
                if (!choices.length)
                    return;
                const query = discoverySearch.value.trim().toLowerCase();
                const visible = choices.filter((model) => `${model.displayName || ''} ${model.id}`.toLowerCase().includes(query));
                const toolbar = element('div', 'agy-actions');
                const count = element('span', 'agy-muted', `${visible.length} of ${choices.length} models · ${selected.size} selected`);
                toolbar.append(count, button(query ? 'Select filtered' : 'Select all', () => {
                    for (const model of visible)
                        selected.add(model.id);
                    showChoices();
                }, status), button('Clear selection', () => {
                    selected.clear();
                    showChoices();
                }, status));
                discovery.append(toolbar);
                if (!visible.length)
                    discovery.append(element('p', 'agy-muted', 'No provider models match this search.'));
                for (const model of visible) {
                    const label = element('label', 'agy-choice');
                    const checkbox = element('input');
                    checkbox.type = 'checkbox';
                    checkbox.checked = selected.has(model.id);
                    checkbox.addEventListener('change', () => {
                        if (checkbox.checked)
                            selected.add(model.id);
                        else
                            selected.delete(model.id);
                        count.textContent = `${visible.length} of ${choices.length} models · ${selected.size} selected`;
                    });
                    label.append(checkbox, element('span', '', model.displayName && model.displayName !== model.id ? `${model.displayName} · ${model.id}` : model.id));
                    discovery.append(label);
                }
            }
            const actions = element('div', 'agy-actions');
            actions.append(button('Test connection', async () => {
                setStatus(status, 'Testing…');
                const result = requireSuccess(await storageAPI.testModelConnection(connection()));
                setStatus(status, result.message || 'Connection successful.');
            }, status), button('Fetch provider models', async () => {
                setStatus(status, 'Fetching models…');
                const result = await storageAPI.discoverModels(connection());
                requireSuccess(result);
                choices = result.models || [];
                discoverySearch.value = '';
                selected.clear();
                showChoices();
                setStatus(status, choices.length
                    ? 'Select models below, then choose Add selected.'
                    : 'This provider returned no models. You can enter a model ID manually.');
            }, status), button('Save model', async () => {
                requireSuccess(await storageAPI.saveCustomModel(modelConfig(modelId.value, displayName.value.trim())));
                await modelsChanged();
                close();
            }, status, true));
            body.append(actions, discoveryFilter, discovery);
            body.append(button('Add selected', async () => {
                if (!selected.size)
                    throw new Error('Select at least one model from the fetched list.');
                let saved = 0;
                for (const choice of choices.filter((model) => selected.has(model.id))) {
                    const prior = modelList.find((model) => model.provider === provider.value &&
                        model.apiUrl === apiUrl.value.trim() &&
                        model.externalModelName === choice.id);
                    const config = modelConfig(choice.id, choice.displayName || choice.id, prior?.name || uniqueName(`models/${provider.value}/${choice.id}`));
                    // Prefer explicit form overrides; otherwise retain the catalog's advertised limits/capabilities.
                    for (const key of ['contextWindow', 'maxOutputTokens', 'supportsVision', 'supportsThinking']) {
                        if (config[key] === undefined && choice[key] !== undefined)
                            config[key] = choice[key];
                    }
                    if (typeof config.contextWindow === 'number' &&
                        typeof config.maxOutputTokens === 'number' &&
                        config.maxOutputTokens >= config.contextWindow &&
                        !maxOutput.value.trim()) {
                        config.maxOutputTokens = config.contextWindow > 1 ? config.contextWindow - 1 : undefined;
                    }
                    delete config.originalName;
                    if (prior)
                        config.originalName = prior.name;
                    else if (existing?.name)
                        config.copyFrom = existing.name;
                    requireSuccess(await storageAPI.saveCustomModel(config));
                    saved++;
                }
                await modelsChanged();
                setStatus(status, `Saved ${saved} models.`);
            }, status));
            provider.addEventListener('change', () => {
                apiUrl.value = preset().defaultUrl;
                apiFormat.value = preset().apiFormat;
                apiKey.value = '';
                choices = [];
                selected.clear();
                discoverySearch.value = '';
                showChoices();
                updateGoogleVisibility();
            });
        }
        catch (error) {
            setStatus(status, error instanceof Error ? error.message : 'Could not open model settings.', true);
        }
    }
    async function openImportExport(kind) {
        const { body, status } = openModal(kind === 'export' ? 'Export models' : 'Import models');
        body.append(element('p', 'agy-muted', kind === 'export'
            ? 'Credentials are removed from this export. Add API keys on the destination device.'
            : 'Paste a model configuration as JSON or an exported base64 string. Existing configurations are merged by name.'));
        const input = jsonField(body, 'Configuration', 'agy-config-json', undefined);
        input.rows = 14;
        if (kind === 'export') {
            input.readOnly = true;
            try {
                input.value = JSON.stringify(await electron_1.ipcRenderer.invoke('storage:export-custom-models'), null, 2);
            }
            catch (error) {
                setStatus(status, String(error), true);
            }
            const actions = element('div', 'agy-actions');
            actions.append(button('Select all', () => {
                input.focus();
                input.select();
            }, status), button('Copy JSON', async () => {
                await navigator.clipboard.writeText(input.value);
                setStatus(status, 'Configuration copied.');
            }, status));
            body.append(actions);
        }
        else {
            const file = field(body, 'Or choose a JSON file', 'agy-import-file', '', 'file');
            file.accept = '.json,application/json';
            file.addEventListener('change', async () => {
                try {
                    const selected = file.files?.[0];
                    if (!selected)
                        return;
                    if (selected.size > 2 * 1024 * 1024)
                        throw new Error('Configuration files must be smaller than 2 MB.');
                    input.value = await selected.text();
                }
                catch (error) {
                    setStatus(status, String(error), true);
                }
            });
            body.append(button('Import configuration', async () => {
                if (!input.value.trim())
                    throw new Error('Paste a configuration or choose a file first.');
                const result = requireSuccess(await electron_1.ipcRenderer.invoke('storage:import-custom-models', input.value.trim()));
                await modelsChanged();
                setStatus(status, `Imported ${result.count ?? 0} models. Add any missing API keys before use.`);
            }, status, true));
        }
    }
    async function discoverLocal() {
        const { body, status } = openModal('Local model servers');
        setStatus(status, 'Checking Ollama, LM Studio and llama.cpp on this computer…');
        try {
            const result = (await electron_1.ipcRenderer.invoke('storage:discover-local'));
            requireSuccess(result);
            if (!body.isConnected)
                return;
            setStatus(status, result.servers?.length
                ? 'Choose a server to configure its models.'
                : 'No local model servers were found. Start a server or add its URL manually.');
            for (const server of result.servers || []) {
                const row = element('div', 'agy-row');
                row.append(element('span', '', `${server.provider} · ${server.models.length} models`), element('div', 'agy-muted', server.apiUrl), button('Configure', () => openModelModal({ name: '', provider: server.provider, apiUrl: server.apiUrl, apiKey: 'none', externalModelName: '' }, 'discover'), status));
                body.append(row);
            }
        }
        catch (error) {
            setStatus(status, String(error), true);
        }
    }
    async function openGateway() {
        const { body, status } = openModal('Remote gateway');
        try {
            const saved = (await electron_1.ipcRenderer.invoke('storage:get-gateway'));
            if (!body.isConnected)
                return;
            body.append(element('p', 'agy-muted', 'Connect to your proxy gateway to import its model aliases and open its management dashboard.'));
            const url = field(body, 'Gateway URL', 'agy-gateway-url', saved?.url || '', 'url');
            const token = field(body, 'Gateway token', 'agy-gateway-token', saved?.token || '', 'password');
            const dashboard = field(body, 'Dashboard URL (optional)', 'agy-dashboard-url', saved?.dashboardUrl || '', 'url');
            const config = () => ({
                url: validUrl(url.value),
                token: token.value.trim(),
                dashboardUrl: dashboard.value.trim() ? validUrl(dashboard.value) : '',
            });
            const save = async () => {
                requireSuccess(await electron_1.ipcRenderer.invoke('storage:save-gateway', config()));
            };
            const actions = element('div', 'agy-actions');
            actions.append(button('Save connection', async () => {
                await save();
                setStatus(status, 'Gateway connection saved.');
            }, status, true), button('Test gateway', async () => {
                setStatus(status, 'Connecting…');
                const result = requireSuccess(await electron_1.ipcRenderer.invoke('storage:test-gateway', config()));
                setStatus(status, result.message || 'Gateway reachable and authentication accepted.');
            }, status), button('Import model aliases', async () => {
                await save();
                const result = requireSuccess(await electron_1.ipcRenderer.invoke('storage:import-gateway-models'));
                await modelsChanged();
                setStatus(status, `Imported ${result.count ?? 0} gateway models.`);
            }, status), button('Open dashboard', async () => {
                await save();
                requireSuccess(await electron_1.ipcRenderer.invoke('storage:open-gateway-dashboard'));
            }, status));
            body.append(actions);
        }
        catch (error) {
            setStatus(status, String(error), true);
        }
    }
    function findSettingsMount() {
        const headings = Array.from(document.querySelectorAll('h1,h2,h3,h4,[role="heading"],div,span'));
        const heading = headings.find((node) => node.children.length === 0 &&
            /^(Models\s*(?:&|and)\s*Usage|Model Settings|MCP Servers|MCP)$/i.test(node.textContent?.trim() || '') &&
            !node.closest('#agy-custom-models-section,button,nav,[role="tablist"],[hidden],[aria-hidden="true"]'));
        if (heading) {
            const section = heading.closest('section');
            if (section)
                return section;
            const panel = heading.closest('[role="tabpanel"]');
            if (panel)
                return panel;
            let content = heading;
            while (content.parentElement && content.parentElement !== document.body) {
                if (content.parentElement.classList.contains('overflow-y-auto'))
                    return content;
                content = content.parentElement;
            }
            return heading.parentElement?.parentElement || heading.parentElement;
        }
        const refresh = findRefreshButton();
        const legacy = refresh?.parentElement?.parentElement?.parentElement;
        if (legacy && /MCP|Model Context Protocol/i.test(legacy.textContent || ''))
            return legacy;
        return null;
    }
    function injectCustomModelsSection() {
        if (document.getElementById('agy-custom-models-section'))
            return;
        const mount = findSettingsMount();
        if (!mount)
            return;
        installStyles();
        const section = element('section');
        section.id = 'agy-custom-models-section';
        section.setAttribute('aria-label', 'Custom Models');
        const header = element('div', 'agy-toolbar');
        const titleBox = element('div', 'agy-toolbar');
        titleBox.style.margin = '0';
        titleBox.append(element('h2', '', 'Custom Models'));
        const proxyBadge = element('div', 'agy-proxy-pill direct');
        proxyBadge.innerHTML = '<span class="agy-dot"></span><span>Checking proxy...</span>';
        titleBox.append(proxyBadge);
        header.append(titleBox, button('Add model', () => openModelModal(), undefined, true));
        void (async () => {
            try {
                const res = (await electron_1.ipcRenderer.invoke('storage:get-proxy-status'));
                if (res?.proxy) {
                    const port = res.proxy.split(':').pop();
                    proxyBadge.className = 'agy-proxy-pill active';
                    proxyBadge.innerHTML = `<span class="agy-dot"></span><span>Bypass Active (${port})</span>`;
                    proxyBadge.title = `Google bypass proxy active: ${res.proxy}`;
                }
                else {
                    proxyBadge.className = 'agy-proxy-pill direct';
                    proxyBadge.innerHTML = '<span class="agy-dot"></span><span>Direct (No Proxy)</span>';
                    proxyBadge.title = 'No active proxy detected';
                }
            }
            catch {
                proxyBadge.remove();
            }
        })();
        const actions = element('div', 'agy-actions');
        actions.append(button('Discover local', discoverLocal), button('Import', () => openImportExport('import')), button('Export', () => openImportExport('export')), button('Remote gateway', openGateway));
        const search = field(section, 'Search models', 'agy-model-search', searchTerm, 'search');
        search.placeholder = 'Search by name, model ID or provider';
        search.addEventListener('input', () => {
            searchTerm = search.value.trim().toLowerCase();
            void renderCustomModelsList();
        });
        const content = element('div');
        content.id = 'agy-custom-models-content';
        const status = statusNode();
        status.id = 'agy-main-status';
        section.prepend(header, element('p', 'agy-muted', 'Provider connections, local models and remote gateways.'), actions);
        section.append(status, content);
        mount.append(section);
        void renderCustomModelsList();
    }
    function setupInjectionObserver() {
        injectCustomModelsSection();
        if (!document.body)
            return;
        let pending;
        const observer = new MutationObserver(() => {
            if (document.getElementById('agy-custom-models-section'))
                return;
            if (pending)
                clearTimeout(pending);
            pending = setTimeout(() => {
                pending = undefined;
                injectCustomModelsSection();
            }, 150);
        });
        observer.observe(document.body, { childList: true, subtree: true });
        window.addEventListener('pagehide', () => {
            observer.disconnect();
            if (pending)
                clearTimeout(pending);
        }, { once: true });
    }
    // --- Network Interceptor for Model Injection --------------------------
    function isSafeToIntercept(url) {
        // Never touch the internal Connect-RPC LanguageServerService channel —
        // those responses are protocol-framed, not plain JSON, and rewriting
        // them corrupts the renderer's RPC client / store hydration.
        if (url.includes('exa.language_server_pb.'))
            return false;
        if (url.includes('/LanguageServerService/'))
            return false;
        return true;
    }
    function isJsonResponse(contentType) {
        return contentType?.split(';', 1)[0].trim().toLowerCase() === 'application/json';
    }
    const customModelsCache = { models: [], ts: 0 };
    async function getCustomModelsForInjection() {
        if (Date.now() - customModelsCache.ts < 30000)
            return customModelsCache.models;
        try {
            customModelsCache.models = (await storageAPI.getCustomModels()).filter((model) => model.enabled !== false);
            customModelsCache.ts = Date.now();
        }
        catch {
            /* ignore */
        }
        return customModelsCache.models;
    }
    // Intercept XHR to inject custom models into GetAvailableModels responses
    const origXHROpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function (method, url, async, username, password) {
        this._agy_url = typeof url === 'string' ? url : url.toString();
        this._agy_method = method;
        this._agy_async = async !== false;
        return origXHROpen.call(this, method, url, async !== false, username, password);
    };
    const origXHRSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.send = function (body) {
        const url = this._agy_url || '';
        if ((url.includes('GetAvailableModels') || url.includes('fetchAvailableModels')) && isSafeToIntercept(url)) {
            // Warm the cache without delaying native XHR events. If it is not ready by
            // DONE, leave the response alone; load/readystatechange ordering must survive.
            if (this._agy_async)
                void getCustomModelsForInjection();
            const origOnReady = this.onreadystatechange;
            this.onreadystatechange = (ev) => {
                if (this.readyState === 4 &&
                    this.status === 200 &&
                    (this.responseType === '' || this.responseType === 'text') &&
                    isJsonResponse(this.getResponseHeader('content-type'))) {
                    const customModels = customModelsCache.models;
                    if (customModels && customModels.length > 0) {
                        try {
                            const responseText = this.responseText;
                            if (responseText && responseText.length > 10) {
                                const parsed = JSON.parse(responseText);
                                const modelsObj = (parsed.models || parsed.availableModels || parsed.available_models || {});
                                for (const m of customModels) {
                                    const slug = 'custom-' +
                                        (m.externalModelName || m.name || '')
                                            .replace(/^models\//, '')
                                            .replace(/[^a-zA-Z0-9]+/g, '-')
                                            .replace(/^-+|-+$/g, '')
                                            .toLowerCase();
                                    modelsObj[slug] = {
                                        displayName: m.displayName || m.name,
                                        recommended: true,
                                        maxTokens: m.contextWindow || 1048576,
                                        maxOutputTokens: m.maxOutputTokens || 4096,
                                        tokenizerType: 'LLAMA_WITH_SPECIAL',
                                        model: 'MODEL_PLACEHOLDER_M' +
                                            (400 + (Math.abs(hashCodeStr(m.displayName || m.name || '')) % 200)),
                                        apiProvider: 'API_PROVIDER_GOOGLE_GEMINI',
                                        modelProvider: 'MODEL_PROVIDER_GOOGLE',
                                    };
                                }
                                // Override response
                                Object.defineProperty(this, 'responseText', { value: JSON.stringify(parsed), writable: true });
                                Object.defineProperty(this, 'response', { value: JSON.stringify(parsed), writable: true });
                            }
                        }
                        catch {
                            /* ignore parse errors */
                        }
                    }
                }
                if (origOnReady)
                    origOnReady.call(this, ev);
            };
        }
        return origXHRSend.call(this, body);
    };
    // Intercept fetch responses for model endpoints
    const origFetch = window.fetch;
    window.fetch = async function (input, init) {
        const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
        const response = await origFetch.call(window, input, init);
        if ((url.includes('GetAvailableModels') || url.includes('fetchAvailableModels')) &&
            isSafeToIntercept(url) &&
            response.ok) {
            if (!isJsonResponse(response.headers.get('content-type'))) {
                return response;
            }
            const customModels = await getCustomModelsForInjection();
            if (customModels && customModels.length > 0) {
                try {
                    const cloned = response.clone();
                    const text = await cloned.text();
                    if (text && text.length > 10) {
                        const parsed = JSON.parse(text);
                        const modelsObj = (parsed.models || parsed.availableModels || parsed.available_models || {});
                        for (const m of customModels) {
                            const slug = 'custom-' +
                                (m.externalModelName || m.name || '')
                                    .replace(/^models\//, '')
                                    .replace(/[^a-zA-Z0-9]+/g, '-')
                                    .replace(/^-+|-+$/g, '')
                                    .toLowerCase();
                            modelsObj[slug] = {
                                displayName: m.displayName || m.name,
                                recommended: true,
                                maxTokens: m.contextWindow || 1048576,
                                maxOutputTokens: m.maxOutputTokens || 4096,
                                tokenizerType: 'LLAMA_WITH_SPECIAL',
                                model: 'MODEL_PLACEHOLDER_M' +
                                    (400 + (Math.abs(hashCodeStr(m.displayName || m.name || '')) % 200)),
                                apiProvider: 'API_PROVIDER_GOOGLE_GEMINI',
                                modelProvider: 'MODEL_PROVIDER_GOOGLE',
                            };
                        }
                        return new Response(JSON.stringify(parsed), {
                            status: response.status,
                            statusText: response.statusText,
                            headers: response.headers,
                        });
                    }
                }
                catch {
                    /* ignore parse errors */
                }
            }
        }
        return response;
    };
    function hashCodeStr(s) {
        let h = 5381;
        for (let i = 0; i < s.length; i++) {
            h = (h << 5) + h + s.charCodeAt(i);
            h = h & h;
        }
        return Math.abs(h);
    }
    // Start the observer
    setupInjectionObserver();
});
//# sourceMappingURL=customPreload.js.map