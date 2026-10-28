/** Shared provider presets. Existing saved models retain their historical wire format. */
export type ApiFormat = 'openai' | 'anthropic' | 'google';
export interface ProviderPreset {
    id: string;
    label: string;
    defaultUrl: string;
    apiFormat: ApiFormat;
    keyRequired: boolean;
}
export declare const PROVIDERS: readonly ProviderPreset[];
export declare function getProvider(id: string): ProviderPreset | undefined;
export declare const OPENCODE_USER_AGENT = "antigravity-add-model/2.0.1";
export declare function isOpencodeProvider(provider?: string): boolean;
/** Explicit providers may use a gateway; automatic detection requires the exact official origin. */
export declare function isOpencodeEndpoint(apiUrl: string, provider?: string): boolean;
/** Classify access failures without exposing echoed credentials or provider response text. */
export declare function describeOpencodeAccessError(status: number, body?: string): string;
/** Explicit presets can use a proxy origin; only the official HTTPS origin is auto-detected. */
export declare function workersAiAccountPath(apiUrl: string, provider?: string): string | undefined;
/** Defaults for old files without apiFormat must not silently change protocol. */
export declare function resolveApiFormat(provider: string, override?: ApiFormat): ApiFormat;
//# sourceMappingURL=providers.d.ts.map