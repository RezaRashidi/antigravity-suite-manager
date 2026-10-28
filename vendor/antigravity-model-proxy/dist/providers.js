"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.PROVIDERS = void 0;
exports.getProvider = getProvider;
exports.resolveApiFormat = resolveApiFormat;
const preset = (id, label, defaultUrl, apiFormat = 'openai', keyRequired = true) => ({ id, label, defaultUrl, apiFormat, keyRequired });
exports.PROVIDERS = [
    preset('9router', '9Router (Local AI Gateway)', 'http://127.0.0.1:20128/v1/chat/completions', 'openai', true),
    preset('openai', 'OpenAI', 'https://api.openai.com/v1/chat/completions'),
    preset('anthropic', 'Anthropic', 'https://api.anthropic.com/v1/messages', 'anthropic'),
    preset('google', 'Google Gemini', 'https://generativelanguage.googleapis.com/v1beta', 'google'),
    preset('google-cloudcode', 'Google Cloud Code account pool', 'https://daily-cloudcode-pa.googleapis.com', 'google', false),
    preset('openrouter', 'OpenRouter', 'https://openrouter.ai/api/v1/chat/completions'),
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
    preset('opencode', 'OpenCode', 'https://opencode.ai/zen/v1/chat/completions'),
    preset('zen', 'OpenCode Zen', 'https://opencode.ai/zen/v1/chat/completions'),
    preset('opencode-go', 'OpenCode Go', 'https://opencode.ai/zen/go/v1/chat/completions'),
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
/** Defaults for old files without apiFormat must not silently change protocol. */
function resolveApiFormat(provider, override) {
    if (override)
        return override;
    if (['deepseek', 'kimi', 'fireworks', 'lmstudio', 'llamacpp'].includes(provider))
        return 'anthropic';
    return getProvider(provider)?.apiFormat || 'openai';
}
//# sourceMappingURL=providers.js.map