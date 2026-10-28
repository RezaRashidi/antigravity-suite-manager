import { createModelManager, DiscoveredModel } from './modelManagement';
import { ModelEntry } from './modelStore';
export declare class WorkersAiSetupError extends Error {
}
interface CloudflareEnvelope {
    success?: boolean;
    result?: unknown;
    result_info?: Record<string, number>;
}
export type CloudflareTransport = (route: string, token: string, method?: 'GET' | 'POST', body?: unknown) => Promise<CloudflareEnvelope>;
export declare function checkedAccount(value: string): string;
export declare function checkedToken(value: string): string;
export declare function expiresOn(value: string | undefined, days?: number, now?: number): string;
/** Fixed origin, bounded response and deadline, no redirects or retries. */
export declare const cloudflareRequest: CloudflareTransport;
export declare function isAccountWorkersModel(model: ModelEntry, account: string): boolean;
export interface WorkersAiSetupOptions {
    mode: 'existing' | 'create' | 'verify-only';
    dataDirectory: string;
    token: string;
    accountId?: string;
    selected?: string[];
    rotate?: boolean;
    expires?: string;
    expiresInDays?: number;
    chooseAccount?: (accounts: {
        id: string;
        name: string;
    }[]) => Promise<string>;
    chooseModels?: (models: DiscoveredModel[]) => Promise<string[]>;
    confirmCreate?: (account: string, expiry: string) => Promise<boolean>;
}
export interface SetupDependencies {
    request?: CloudflareTransport;
    manager?: Pick<ReturnType<typeof createModelManager>, 'store' | 'discoverModels'>;
    now?: () => number;
}
export declare function setupWorkersAi(options: WorkersAiSetupOptions, dependencies?: SetupDependencies): Promise<{
    accountId: string;
    catalog: DiscoveredModel[];
    saved: number;
    verification: string;
    tokenCreated: boolean;
} | {
    tokenId?: string;
    expiresOn?: string;
    accountId: string;
    saved: number;
    verification: string;
    tokenCreated: boolean;
    catalog?: undefined;
}>;
export {};
//# sourceMappingURL=workersAiSetup.d.ts.map