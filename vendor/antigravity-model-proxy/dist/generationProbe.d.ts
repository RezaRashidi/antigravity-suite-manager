import type { CustomModel } from './proxy';
/** Explicitly invoked only. One short generation; no retries, tools, user prompt or fallback models. */
export declare function runGenerationProbe(input: CustomModel): Promise<{
    success: boolean;
    status: number;
    error: string;
    message?: undefined;
} | {
    success: boolean;
    status: number;
    message: string;
    error?: undefined;
}>;
//# sourceMappingURL=generationProbe.d.ts.map