/** Verified against the Antigravity IDE 2.5.5 Model enum: M0..M650 = 1000..1650. */
export declare const NATIVE_MODEL_CAPACITY = 651;
export interface IdentityModel {
    name: string;
    displayName?: string;
    externalModelName?: string;
}
export interface ModelIdentity {
    name: string;
    catalogId: string;
    placeholderId?: string;
    placeholderValue?: number;
}
export declare function legacyPlaceholderId(model: IdentityModel): string;
export declare function placeholderIndex(value: unknown): number | undefined;
/**
 * Persist enum ownership independently of model ordering, display labels and secrets.
 * Removed models retain their assignment so cached IDE selections never select a different model.
 * Native enum reservations survive offline catalog fallback; a newly observed native owner wins.
 */
export declare function allocateModelIdentities(dataDirectory: string, models: IdentityModel[], upstream?: unknown): ModelIdentity[];
//# sourceMappingURL=modelIdentity.d.ts.map