/**
 * Antigravity Local Proxy Server.
 * Routes requests to Google, OpenAI, Anthropic, Ollama, and custom provider endpoints.
 * Intercepts model lists to inject user-defined custom models.
 */
export interface CustomModel {
    name: string;
    displayName: string;
    description: string;
    provider: string;
    apiKey: string;
    apiUrl: string;
    externalModelName: string;
    allowUnauthorized?: boolean;
    encrypted?: boolean;
    _slug?: string;
    timeout?: number;
    maxRetries?: number;
    enabled?: boolean;
    apiFormat?: import('./providers').ApiFormat;
    fallbackModels?: string[];
    reasoningEffort?: 'none' | 'minimal' | 'low' | 'medium' | 'high' | 'xhigh';
    thinkingBudget?: number;
    maxOutputTokens?: number;
    contextWindow?: number;
    idleTimeout?: number;
    retryBudgetMs?: number;
    circuitBreaker?: import('./proxy/circuitBreaker').CircuitBreakerOptions;
    customHeaders?: Record<string, string>;
    encryptedHeaders?: boolean;
    extraBody?: Record<string, unknown>;
    rawUrl?: boolean;
    gateway?: boolean;
    supportsVision?: boolean;
    supportsThinking?: boolean;
    googleProject?: string;
    googleAccounts?: import('./googleAccounts').GoogleAccount[];
    googlePool?: import('./googleAccounts').GooglePoolOptions;
    encryptedGoogleAccounts?: boolean;
}
export declare function startProxy(): Promise<number>;
export declare function stopProxy(): Promise<void>;
export declare function getProxyPort(): number;
//# sourceMappingURL=proxy.d.ts.map