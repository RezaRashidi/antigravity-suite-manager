"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.getTranslator = getTranslator;
exports.translateRequest = translateRequest;
exports.translateResponse = translateResponse;
exports.translateStreamChunk = translateStreamChunk;
exports.getProviderHeaders = getProviderHeaders;
exports.supportsStreaming = supportsStreaming;
exports.getProviderUrl = getProviderUrl;
/** Wire-format dispatch, independent from provider branding and authentication. */
const openai = __importStar(require("./translators/openai"));
const anthropic = __importStar(require("./translators/anthropic"));
const google = __importStar(require("./translators/google"));
const providers_1 = require("../providers");
const artifactMetadata_1 = require("./artifactMetadata");
function getTranslator(provider, apiFormat) {
    const format = (0, providers_1.resolveApiFormat)(provider, apiFormat);
    return format === 'google' ? google : format === 'anthropic' ? anthropic : openai;
}
function translateRequest(provider, body, modelName, apiFormat, stateKey) {
    const format = (0, providers_1.resolveApiFormat)(provider, apiFormat);
    if (format === 'google')
        return google.mapGeminiToGoogle(body, modelName);
    if (format === 'anthropic')
        return anthropic.mapGeminiToAnthropic(body, modelName, stateKey);
    return openai.mapGeminiToOpenAI(body, modelName, stateKey);
}
function translateResponse(provider, response, stateKey, apiFormat, toolSchemas, artifactContext) {
    const format = (0, providers_1.resolveApiFormat)(provider, apiFormat);
    const mapped = format === 'google'
        ? google.mapGoogleToGemini(response, stateKey)
        : format === 'anthropic'
            ? anthropic.mapAnthropicToGemini(response, stateKey, toolSchemas)
            : openai.mapOpenAIToGemini(response, stateKey, toolSchemas);
    return (0, artifactMetadata_1.normalizeArtifactResponse)(mapped, artifactContext);
}
function translateStreamChunk(provider, chunk, stateKey, apiFormat, streamKey, toolSchemas, artifactContext) {
    const format = (0, providers_1.resolveApiFormat)(provider, apiFormat);
    const mapped = format === 'google'
        ? google.mapGoogleChunkToGemini(chunk, stateKey)
        : format === 'anthropic'
            ? anthropic.mapAnthropicChunkToGemini(chunk, stateKey, streamKey, toolSchemas)
            : openai.mapOpenAIChunkToGemini(chunk, stateKey, streamKey, toolSchemas);
    // Normalize before customRequest records reasoning against the emitted arguments.
    return (0, artifactMetadata_1.normalizeArtifactCandidate)(mapped, artifactContext);
}
function getProviderHeaders(provider, apiKey = '', apiFormat, apiUrl = '') {
    const headers = { 'Content-Type': 'application/json' };
    const format = (0, providers_1.resolveApiFormat)(provider, apiFormat);
    const opencode = (0, providers_1.isOpencodeEndpoint)(apiUrl, provider);
    if (format === 'anthropic')
        headers['anthropic-version'] = '2023-06-01';
    if (apiKey && apiKey !== 'none') {
        if (/^(enc:|fallback:|local-gcm:|DECRYPTION_FAILED)/.test(apiKey))
            throw new Error('API key could not be decrypted; save the key again.');
        if (opencode)
            headers.Authorization = `Bearer ${apiKey}`;
        else if (format === 'google')
            headers['x-goog-api-key'] = apiKey;
        else if (format === 'anthropic')
            headers['x-api-key'] = apiKey;
        else
            headers.Authorization = `Bearer ${apiKey}`;
    }
    if (provider === 'openrouter') {
        headers['HTTP-Referer'] = 'https://antigravity.google';
        headers['X-Title'] = 'Antigravity';
    }
    if (opencode)
        headers['User-Agent'] = providers_1.OPENCODE_USER_AGENT;
    return headers;
}
function supportsStreaming(_provider) {
    return true;
}
function getProviderUrl(baseUrl, modelName, isStream, translator) {
    if (typeof translator?.getGoogleApiUrl === 'function')
        return translator.getGoogleApiUrl(baseUrl, modelName, isStream);
    const url = new URL(baseUrl);
    let pathname = url.pathname.replace(/\/+$/, '');
    const anthropicFormat = translator === anthropic;
    pathname = pathname.replace(/\/(?:chat\/completions|completions|messages)$/, '');
    if (!pathname)
        pathname = '/v1';
    pathname += anthropicFormat ? '/messages' : '/chat/completions';
    url.pathname = pathname;
    return url.toString();
}
//# sourceMappingURL=registry.js.map