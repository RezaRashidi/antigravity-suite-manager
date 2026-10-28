export interface GoogleNativeClient {
    clientId: string;
    clientSecret: string;
    scopes: string[];
}
export interface GoogleNativeClientOptions {
    resources?: string;
    platform?: NodeJS.Platform;
    env?: NodeJS.ProcessEnv;
    home?: string;
    runtimeResources?: string;
}
export declare const GOOGLE_NATIVE_SCOPES: readonly ["https://www.googleapis.com/auth/cloud-platform", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/cclog", "https://www.googleapis.com/auth/experimentsandconfigs"];
export declare function resolveGoogleNativeClient(options?: GoogleNativeClientOptions): GoogleNativeClient;
//# sourceMappingURL=googleNativeClient.d.ts.map