import { type GoogleAccount } from './googleAccounts';
export declare const GOOGLE_CLOUD_CODE_PRODUCTION = "https://cloudcode-pa.googleapis.com";
export declare const GOOGLE_CLOUD_CODE_DAILY = "https://daily-cloudcode-pa.googleapis.com";
type JsonObject = Record<string, unknown>;
export interface GooglePreparationOptions {
    signal?: AbortSignal;
    /** Only an explicit login/preparation action may authorize first-time enrollment. */
    allowOnboard?: boolean;
    /** Official service or a loopback protocol-test endpoint; arbitrary remote origins are refused. */
    endpoint?: string;
}
export interface GooglePreparationDependencies {
    /** Test-only transport injection. URLs are validated before this function is called. */
    request?: (url: URL, method: 'GET' | 'POST', accessToken: string, body: JsonObject | undefined, signal: AbortSignal) => Promise<JsonObject>;
    timeoutMs?: number;
    pollIntervalMs?: number;
    maxPolls?: number;
}
/** Discover the account's project/service route, and enroll only after an explicit user action. */
export declare function prepareGoogleAccount(account: GoogleAccount, options?: GooglePreparationOptions, dependencies?: GooglePreparationDependencies): Promise<GoogleAccount & {
    project: string;
    cloudCodeEndpoint: string;
}>;
export {};
//# sourceMappingURL=googleOnboarding.d.ts.map