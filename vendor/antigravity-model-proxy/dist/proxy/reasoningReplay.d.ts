import type { GeminiBody } from './requestOptions';
export interface ReasoningReplayModel {
    name: string;
    provider: string;
    apiUrl: string;
    externalModelName?: string;
    apiFormat?: string;
    apiKey?: string;
    customHeaders?: Record<string, string>;
    rawUrl?: boolean;
}
/** Volatile, bounded recovery for clients that omit thought parts from tool history. */
export declare class ReasoningReplayCache {
    private readonly now;
    private readonly entries;
    private characters;
    constructor(now?: () => number);
    private remove;
    private prune;
    clear(): void;
    /** Call only after successful completion, with all mapped thought/tool-call parts. */
    record(body: GeminiBody, model: ReasoningReplayModel, parts: readonly unknown[]): void;
    /** Recover before context budgeting; return a copy only when a history item changes. */
    restore<T extends GeminiBody>(body: T, model: ReasoningReplayModel): T;
}
export declare const reasoningReplayCache: ReasoningReplayCache;
//# sourceMappingURL=reasoningReplay.d.ts.map