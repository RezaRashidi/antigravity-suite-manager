import type { IncomingHttpHeaders } from 'node:http';
interface TierResponse {
    status: number;
    body: unknown;
}
type TierLookup = (headers: IncomingHttpHeaders, body: Buffer, signal: AbortSignal) => Promise<TierResponse>;
/** Read account routing with the same identity/project; never replay a generation. */
export declare const fetchCloudCodeTier: TierLookup;
/**
 * Antigravity IDE 2.5.5 uses production Cloud Code until loadCodeAssist reveals
 * the account tier, then moves non-GCP tiers to daily Cloud Code. A loopback
 * setting masks that native URL switch, so the IDE service preserves it here.
 * Cache entries contain only an irreversible bearer digest and routing state.
 */
export declare class CloudCodeRouting {
    private readonly now;
    private readonly lookup;
    private readonly callers;
    private readonly pending;
    constructor(now?: () => number, lookup?: TierLookup);
    private expire;
    resolve(headers: IncomingHttpHeaders): string;
    resolveForGeneration(headers: IncomingHttpHeaders, body: Buffer, signal: AbortSignal): Promise<string>;
    observe(headers: IncomingHttpHeaders, status: number, response: unknown): void;
    clear(): void;
}
export {};
//# sourceMappingURL=cloudCodeRouting.d.ts.map