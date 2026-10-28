import type * as http from 'http';
import { type SubagentModelResolver, type SubagentRoutingContext } from './subagentRouting';
export interface NativeSubagentRouting {
    context: SubagentRoutingContext;
    resolve: SubagentModelResolver;
}
/**
 * Rewrite native-model subagent calls at the same Gemini boundary as custom models.
 * Successful bodies are decoded before inspection; upstream HTTP errors remain opaque.
 */
export declare function forwardNativeGeneration(upstream: http.IncomingMessage, downstream: http.ServerResponse, routing: NativeSubagentRouting, streamHint: boolean): Promise<void>;
//# sourceMappingURL=nativeSubagentResponse.d.ts.map