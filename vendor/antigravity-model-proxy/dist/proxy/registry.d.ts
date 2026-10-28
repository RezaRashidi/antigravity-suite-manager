import { ApiFormat } from '../providers';
import type { ToolSchemas } from './translators/utils';
export interface TranslatorModule {
    [key: string]: unknown;
}
export interface ProviderHeaders {
    'Content-Type': string;
    [key: string]: string | undefined;
}
export declare function getTranslator(provider: string, apiFormat?: ApiFormat): TranslatorModule;
export declare function translateRequest(provider: string, body: unknown, modelName: string, apiFormat?: ApiFormat, stateKey?: string): unknown;
export declare function translateResponse(provider: string, response: unknown, stateKey: string, apiFormat?: ApiFormat, toolSchemas?: ToolSchemas): unknown;
export declare function translateStreamChunk(provider: string, chunk: unknown, stateKey: string, apiFormat?: ApiFormat, streamKey?: string, toolSchemas?: ToolSchemas): unknown;
export declare function getProviderHeaders(provider: string, apiKey?: string, apiFormat?: ApiFormat): ProviderHeaders;
export declare function supportsStreaming(_provider: string): boolean;
export declare function getProviderUrl(baseUrl: string, modelName: string, isStream: boolean, translator: TranslatorModule | null): string;
//# sourceMappingURL=registry.d.ts.map