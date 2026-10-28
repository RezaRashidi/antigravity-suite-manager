export interface CircuitBreakerOptions {
    enabled?: boolean;
    failureThreshold?: number;
    cooldownMs?: number;
}
/** One half-open probe per model; other callers use their configured fallback. */
export declare class CircuitBreaker {
    private readonly now;
    private readonly states;
    constructor(now?: () => number);
    acquire(key: string, options?: CircuitBreakerOptions): boolean;
    succeed(key: string): void;
    fail(key: string, options?: CircuitBreakerOptions): void;
    cancel(key: string): void;
    snapshot(): {
        tracked: number;
        open: number;
        probing: number;
    };
}
//# sourceMappingURL=circuitBreaker.d.ts.map