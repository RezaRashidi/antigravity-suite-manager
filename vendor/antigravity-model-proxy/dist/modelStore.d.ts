export interface ModelEntry {
    name: string;
    provider: string;
    apiUrl: string;
    apiKey?: string;
    externalModelName: string;
    displayName?: string;
    description?: string;
    enabled?: boolean;
    encrypted?: boolean;
    [key: string]: unknown;
}
export interface SecretCodec {
    encryptString(value: string): string;
    decryptString(value: string): string;
}
/** Accept flat legacy files and provider-group exports without losing model overrides. */
export declare function normalizeModelConfig(payload: unknown): ModelEntry[];
export declare function readModelConfig(filename: string): ModelEntry[];
export declare function writeJsonAtomic(filename: string, value: unknown): void;
export declare function isMaskedSecret(value: unknown): boolean;
export declare function decodeSecret(value: string | undefined, codec: SecretCodec): string;
export declare function redactModel(model: ModelEntry): ModelEntry;
/** All writes are synchronous atomic read/modify/write operations, including bulk imports. */
export declare class ModelStore {
    readonly filename: string;
    readonly codec: SecretCodec;
    readonly pendingAccount?: (id: string) => Record<string, unknown> | undefined;
    constructor(filename: string, codec: SecretCodec, pendingAccount?: (id: string) => Record<string, unknown> | undefined);
    read(): ModelEntry[];
    list(): ModelEntry[];
    private prepare;
    save(input: ModelEntry & {
        originalName?: string;
        copyFrom?: string;
    }): void;
    delete(name: string): void;
    import(payload: unknown): number;
    export(): {
        version: number;
        models: ModelEntry[];
    };
}
//# sourceMappingURL=modelStore.d.ts.map