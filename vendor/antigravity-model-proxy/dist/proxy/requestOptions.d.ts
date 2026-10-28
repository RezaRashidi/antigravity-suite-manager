import type { CustomModel } from '../proxy';
import type { ApiFormat } from '../providers';
export interface GeminiBody {
    contents?: {
        role?: string;
        parts?: {
            functionResponse?: unknown;
            [key: string]: unknown;
        }[];
    }[];
    generationConfig?: Record<string, unknown>;
    [key: string]: unknown;
}
/**
 * Fingerprints from the verified Antigravity IDE 2.5.5 language-server binary
 * and its observed live checkpoint request.
 * Only the final plain user turn can trigger it; quoted prompts, history, tool
 * output, and ordinary requests to summarize must retain the normal effort.
 */
export declare function isAntigravityCompactionRequest(body: GeminiBody): boolean;
type CompactionEffort = NonNullable<CustomModel['compactionReasoningEffort']>;
/** Approximate input budget. Drop whole oldest turns, never half a tool exchange. */
export declare function trimContext(body: GeminiBody, contextWindow?: number, maxOutputTokens?: number): GeminiBody;
export declare function applyRequestOptions(payload: Record<string, unknown>, model: CustomModel, format: ApiFormat, stream: boolean, compactionEffort?: CompactionEffort): Record<string, unknown>;
export declare function parseRetryAfter(value: string | string[] | undefined, now?: number): number;
export {};
//# sourceMappingURL=requestOptions.d.ts.map