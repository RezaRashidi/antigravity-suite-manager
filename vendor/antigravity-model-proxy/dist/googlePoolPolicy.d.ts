/** Bounded, credential-free interpretation of Google's structured rate-limit responses. */
export type GoogleCooldownReason = 'rate-limited' | 'quota-exhausted' | 'upstream-error';
export interface GoogleRateLimitDecision {
    reason: GoogleCooldownReason;
    retryAfterMs?: number;
}
export declare function classifyGoogleRateLimit(body: string, retryAfter?: string | string[], now?: number): GoogleRateLimitDecision;
//# sourceMappingURL=googlePoolPolicy.d.ts.map