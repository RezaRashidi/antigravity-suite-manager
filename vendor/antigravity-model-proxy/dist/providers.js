"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.PROVIDERS = void 0;
exports.getProvider = getProvider;
exports.resolveApiFormat = resolveApiFormat;
const preset = (id, label, defaultUrl, apiFormat = 'openai', keyRequired = true) => ({ id, label, defaultUrl, apiFormat, keyRequired });
exports.PROVIDERS = [
    preset('odirect', 'ODirect (AI Gateway)', 'https://ai.odirect.app/v1/', 'openai', true),
    preset('9router', '9Router (Local AI Gateway)', 'http://127.0.0.1:20128/v1/', 'openai', true),
    preset('openai', 'OpenAI', 'https://api.openai.com/v1/'),
    preset('anthropic', 'Anthropic', 'https://api.anthropic.com/v1/', 'anthropic'),
    preset('google', 'Google Gemini', 'https://generativelanguage.googleapis.com/v1beta/', 'google'),
    preset('google-cloudcode', 'Google Cloud Code account pool', 'https://daily-cloudcode-pa.googleapis.com/', 'google', false),
    preset('openrouter', 'OpenRouter', 'https://openrouter.ai/api/v1/'),
    preset('together', 'Together AI', 'https://api.together.ai/v1/'),
    preset('huggingface', 'Hugging Face Inference Providers', 'https://router.huggingface.co/v1/'),
    preset('sambanova', 'SambaNova', 'https://api.sambanova.ai/v1/'),
    preset('siliconflow', 'SiliconFlow (International)', 'https://api.siliconflow.com/v1/'),
    preset('novita', 'Novita AI', 'https://api.novita.ai/openai/v1/'),
    preset('dashscope', 'Alibaba Cloud Model Studio (International)', 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1/'),
    preset('deepseek', 'DeepSeek', 'https://api.deepseek.com/v1/'),
    preset('kimi', 'Moonshot / Kimi', 'https://api.moonshot.ai/v1/'),
    preset('fireworks', 'Fireworks AI', 'https://api.fireworks.ai/inference/v1/'),
    preset('groq', 'Groq', 'https://api.groq.com/openai/v1/'),
    preset('mistral', 'Mistral', 'https://api.mistral.ai/v1/'),
    preset('codestral', 'Codestral', 'https://codestral.mistral.ai/v1/'),
    preset('cerebras', 'Cerebras', 'https://api.cerebras.ai/v1/'),
    preset('nvidia', 'NVIDIA NIM', 'https://integrate.api.nvidia.com/v1/'),
    preset('minimax', 'MiniMax', 'https://api.minimax.io/anthropic/v1/', 'anthropic'),
    preset('opencode', 'OpenCode', 'https://opencode.ai/zen/v1/'),
    preset('zen', 'OpenCode Zen', 'https://opencode.ai/zen/v1/'),
    preset('opencode-go', 'OpenCode Go', 'https://opencode.ai/zen/go/v1/'),
    preset('wafer', 'Wafer (custom endpoint)', '', 'anthropic'),
    preset('zai', 'Z.AI', 'https://api.z.ai/api/anthropic/v1/', 'anthropic'),
    preset('xai', 'xAI', 'https://api.x.ai/v1/'),
    preset('ollama', 'Ollama', 'http://localhost:11434/v1/', 'openai', false),
    preset('lmstudio', 'LM Studio', 'http://localhost:1234/v1/', 'openai', false),
    preset('llamacpp', 'llama.cpp', 'http://localhost:8080/v1/', 'openai', false),
    preset('vllm', 'vLLM', 'http://localhost:8000/v1/', 'openai', false),
    preset('localai', 'LocalAI', 'http://localhost:8080/v1/', 'openai', false),
    preset('tabby', 'TabbyAPI', 'http://localhost:5000/v1/', 'openai', false),
    preset('textgen', 'Text Generation WebUI', 'http://localhost:5000/v1/', 'openai', false),
    preset('litellm', 'LiteLLM', 'http://localhost:4000/v1/', 'openai', false),
    preset('aphrodite', 'Aphrodite', 'http://localhost:2242/v1/', 'openai', false),
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