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
/** Defaults for old files without apiFormat must not silently change protocol. */
export declare function resolveApiFormat(provider: string, override?: ApiFormat): ApiFormat;
//# sourceMappingURL=providers.d.ts.map