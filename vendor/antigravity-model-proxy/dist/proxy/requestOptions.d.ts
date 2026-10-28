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
/** Conservative estimate, not a tokenizer. Drop whole oldest turns, never half a tool exchange. */
export declare function trimContext(body: GeminiBody, contextWindow?: number, maxOutputTokens?: number): GeminiBody;
export declare function applyRequestOptions(payload: Record<string, unknown>, model: CustomModel, format: ApiFormat, stream: boolean): Record<string, unknown>;
export declare function parseRetryAfter(value: string | string[] | undefined, now?: number): number;
//# sourceMappingURL=requestOptions.d.ts.map