"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.OPENCODE_USER_AGENT = exports.PROVIDERS = void 0;
exports.getProvider = getProvider;
exports.isOpencodeProvider = isOpencodeProvider;
exports.isOpencodeEndpoint = isOpencodeEndpoint;
exports.describeOpencodeAccessError = describeOpencodeAccessError;
exports.workersAiAccountPath = workersAiAccountPath;
exports.resolveApiFormat = resolveApiFormat;
const preset = (id, label, defaultUrl, apiFormat = 'openai', keyRequired = true) => ({ id, label, defaultUrl, apiFormat, keyRequired });
exports.PROVIDERS = [
    preset('openai', 'OpenAI', 'https://api.openai.com/v1/chat/completions'),
    preset('anthropic', 'Anthropic', 'https://api.anthropic.com/v1/messages', 'anthropic'),
    preset('google', 'Google Gemini', 'https://generativelanguage.googleapis.com/v1beta', 'google'),
    preset('google-cloudcode', 'Google Cloud Code account pool', 'https://daily-cloudcode-pa.googleapis.com', 'google', false),
    preset('openrouter', 'OpenRouter', 'https://openrouter.ai/api/v1/chat/completions'),
    preset('workers-ai', 'Cloudflare Workers AI', 'https://api.cloudflare.com/client/v4/accounts/ACCOUNT_ID/ai/v1/chat/completions'),
    preset('together', 'Together AI', 'https://api.together.ai/v1/chat/completions'),
    preset('huggingface', 'Hugging Face Inference Providers', 'https://router.huggingface.co/v1/chat/completions'),
    preset('sambanova', 'SambaNova', 'https://api.sambanova.ai/v1/chat/completions'),
    preset('siliconflow', 'SiliconFlow (International)', 'https://api.siliconflow.com/v1/chat/completions'),
    preset('novita', 'Novita AI', 'https://api.novita.ai/openai/v1/chat/completions'),
    preset('dashscope', 'Alibaba Cloud Model Studio (International)', 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions'),
    preset('deepseek', 'DeepSeek', 'https://api.deepseek.com/v1/chat/completions'),
    preset('kimi', 'Moonshot / Kimi', 'https://api.moonshot.ai/v1/chat/completions'),
    preset('fireworks', 'Fireworks AI', 'https://api.fireworks.ai/inference/v1/chat/completions'),
    preset('groq', 'Groq', 'https://api.groq.com/openai/v1/chat/completions'),
    preset('mistral', 'Mistral', 'https://api.mistral.ai/v1/chat/completions'),
    preset('codestral', 'Codestral', 'https://codestral.mistral.ai/v1/chat/completions'),
    preset('cerebras', 'Cerebras', 'https://api.cerebras.ai/v1/chat/completions'),
    preset('nvidia', 'NVIDIA NIM', 'https://integrate.api.nvidia.com/v1/chat/completions'),
    preset('minimax', 'MiniMax', 'https://api.minimax.io/anthropic/v1/messages', 'anthropic'),
    preset('opencode', 'OpenCode', 'https://opencode.ai/inference/openai/v1/chat/completions', 'openai', false),
    preset('zen', 'OpenCode Zen', 'https://opencode.ai/zen/v1/chat/completions', 'openai', false),
    preset('opencode-go', 'OpenCode Go', 'https://opencode.ai/inference/go/openai/v1/chat/completions'),
    preset('wafer', 'Wafer (custom endpoint)', '', 'anthropic'),
    preset('zai', 'Z.AI', 'https://api.z.ai/api/anthropic/v1/messages', 'anthropic'),
    preset('xai', 'xAI', 'https://api.x.ai/v1/chat/completions'),
    preset('ollama', 'Ollama', 'http://localhost:11434/v1/chat/completions', 'openai', false),
    preset('lmstudio', 'LM Studio', 'http://localhost:1234/v1/chat/completions', 'openai', false),
    preset('llamacpp', 'llama.cpp', 'http://localhost:8080/v1/chat/completions', 'openai', false),
    preset('vllm', 'vLLM', 'http://localhost:8000/v1/chat/completions', 'openai', false),
    preset('localai', 'LocalAI', 'http://localhost:8080/v1/chat/completions', 'openai', false),
    preset('tabby', 'TabbyAPI', 'http://localhost:5000/v1/chat/completions', 'openai', false),
    preset('textgen', 'Text Generation WebUI', 'http://localhost:5000/v1/chat/completions', 'openai', false),
    preset('litellm', 'LiteLLM', 'http://localhost:4000/v1/chat/completions', 'openai', false),
    preset('aphrodite', 'Aphrodite', 'http://localhost:2242/v1/chat/completions', 'openai', false),
    preset('custom', 'Custom endpoint', '', 'openai', false),
];
function getProvider(id) {
    return exports.PROVIDERS.find((provider) => provider.id === id);
}
// OpenCode documents free chat requests without Authorization and asks external
// coding agents to identify themselves, rather than impersonating its own CLI.
exports.OPENCODE_USER_AGENT = 'antigravity-add-model/2.0.1';
function isOpencodeProvider(provider) {
    return ['opencode', 'zen', 'opencode-go'].includes(provider || '');
}
/** Explicit providers may use a gateway; automatic detection requires the exact official origin. */
function isOpencodeEndpoint(apiUrl, provider) {
    if (isOpencodeProvider(provider))
        return true;
    try {
        const url = new URL(apiUrl);
        return url.origin === 'https://opencode.ai' && /^\/(?:inference|zen)(?:\/|$)/.test(url.pathname);
    }
    catch {
        return false;
    }
}
/** Classify access failures without exposing echoed credentials or provider response text. */
function describeOpencodeAccessError(status, body = '') {
    if (status === 403 && /free tier can only be used from within opencode/i.test(body)) {
        return 'OpenCode restricts this free model to its own client (HTTP 403). Use the official OpenCode client or choose a model available to external clients through the OpenCode API.';
    }
    if (status === 401) {
        return 'OpenCode authentication rejected (HTTP 401). Add a valid OpenCode Console API key for paid models; keyless access is limited to the free chat models allowed by the service.';
    }
    return `OpenCode denied access (HTTP ${status}). Check the model, workspace permissions, and API key or Go subscription. Free pricing does not guarantee access from every client.`;
}
/** Explicit presets can use a proxy origin; only the official HTTPS origin is auto-detected. */
function workersAiAccountPath(apiUrl, provider) {
    const url = new URL(apiUrl);
    if (provider !== 'workers-ai' &&
        !(url.origin === 'https://api.cloudflare.com' && /^\/client\/v4\/accounts\//.test(url.pathname)))
        return undefined;
    const match = url.pathname.match(/^(\/client\/v4\/accounts\/([^/]+)\/ai)\/v1(?:\/chat\/completions)?\/?$/);
    if (!match || !/^[a-f0-9]{32}$/i.test(match[2])) {
        throw new Error('Set the Cloudflare API URL to https://api.cloudflare.com/client/v4/accounts/YOUR_ACCOUNT_ID/ai/v1/chat/completions using your 32-character Account ID.');
    }
    return match[1];
}
/** Defaults for old files without apiFormat must not silently change protocol. */
function resolveApiFormat(provider, override) {
    if (override)
        return override;
    if (['deepseek', 'kimi', 'fireworks', 'lmstudio', 'llamacpp'].includes(provider))
        return 'anthropic';
    return getProvider(provider)?.apiFormat || 'openai';
}
//# sourceMappingURL=providers.js.map