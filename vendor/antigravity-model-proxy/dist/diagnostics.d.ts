export type DiagnosticOutcome = 'succeeded' | 'failed' | 'cancelled';
export interface DiagnosticRequest {
    id: string;
    timestamp: number;
    model: string;
    provider: string;
    stream: boolean;
    kind: 'request' | 'generation-test';
    outcome: DiagnosticOutcome;
    status?: number;
    latencyMs: number;
    inputTokens?: number;
    outputTokens?: number;
    cachedTokens?: number;
}
export declare function beginDiagnosticRequest(input: {
    model: string;
    provider: string;
    stream: boolean;
    kind?: 'request' | 'generation-test';
}): {
    /** Usage belongs to the final attempted provider/model, not a sum of retry billing. */
    resetUsage(): void;
    observe(value: unknown, format: "openai" | "anthropic" | "google"): void;
    finish(result: {
        outcome: DiagnosticOutcome;
        status?: number;
        model?: string;
        provider?: string;
    }): void;
};
export declare function getDiagnostics(): {
    success: boolean;
    startedAt: number;
    active: number;
    capacity: number;
    summary: {
        requests: number;
        succeeded: number;
        failed: number;
        cancelled: number;
        measuredRequests: number;
        measuredInputRequests: number;
        measuredOutputRequests: number;
        measuredCachedRequests: number;
        inputTokens: number;
        outputTokens: number;
        cachedTokens: number;
    };
    recentModels: string[];
    requests: {
        id: string;
        timestamp: number;
        model: string;
        provider: string;
        stream: boolean;
        kind: "request" | "generation-test";
        outcome: DiagnosticOutcome;
        status?: number;
        latencyMs: number;
        inputTokens?: number;
        outputTokens?: number;
        cachedTokens?: number;
    }[];
};
export declare function getRecentModelNames(): string[];
export declare function clearDiagnostics(): {
    success: boolean;
};
//# sourceMappingURL=diagnostics.d.ts.map