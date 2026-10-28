import * as http from 'http';
import type { CustomModel } from '../proxy';
import { GeminiBody } from './requestOptions';
export declare function getProxyMetrics(): {
    circuits: {
        tracked: number;
        open: number;
        probing: number;
    };
    requests: number;
    active: number;
    succeeded: number;
    failed: number;
    cancelled: number;
    upstreamAttempts: number;
    retries: number;
    fallbacks: number;
    circuitSkips: number;
    accountSwitches: number;
};
export declare function stopCustomRequests(): void;
export declare function buildFallbackChain(primary: CustomModel, allModels: CustomModel[]): CustomModel[];
/** The sole retry/fallback owner; nothing is retried after any model output was received. */
export declare function runCustomModelRequest(res: http.ServerResponse, primary: CustomModel, originalBody: GeminiBody, isStream: boolean, allModels: CustomModel[], cloudEnvelope?: boolean): Promise<void>;
//# sourceMappingURL=customRequest.d.ts.map