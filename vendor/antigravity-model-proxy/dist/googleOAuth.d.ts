export declare const GOOGLE_AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth";
export declare const GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token";
export interface GoogleLoginOptions {
    clientId: string;
    clientSecret?: string;
    label?: string;
    signal?: AbortSignal;
    timeoutMs?: number;
}
export interface GoogleLoginAccount {
    id: string;
    label?: string;
    accessToken: string;
    refreshToken?: string;
    expiresAt: number;
    clientId: string;
    clientSecret?: string;
}
interface TokenResponse {
    access_token: string;
    refresh_token?: string;
    expires_in?: number;
}
export interface GoogleOAuthDependencies {
    /** Dependency injection is for local protocol tests; production always uses Google's fixed token URL. */
    exchangeToken?: (parameters: URLSearchParams, signal: AbortSignal) => Promise<TokenResponse>;
    now?: () => number;
}
/** Returns credentials to the main process only. IPC callers must store them before returning a redacted account. */
export declare function loginGoogleAccount(options: GoogleLoginOptions, openExternal: (url: string) => Promise<unknown>, dependencies?: GoogleOAuthDependencies): Promise<GoogleLoginAccount>;
export {};
//# sourceMappingURL=googleOAuth.d.ts.map