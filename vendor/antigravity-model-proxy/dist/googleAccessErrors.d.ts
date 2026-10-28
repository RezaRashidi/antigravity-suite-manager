/** Fixed Google error guidance. Never accepts or returns provider response bodies or credentials. */
export type GoogleAccessErrorCategory = 'authentication' | 'access-denied' | 'rate-limited' | 'transient' | 'request-failed';
export type GoogleAccessOperation = 'oauth' | 'quota' | 'models' | 'generation';
export declare function describeGoogleAccessError(status: number, operation?: GoogleAccessOperation): {
    category: GoogleAccessErrorCategory;
    message: string;
};
//# sourceMappingURL=googleAccessErrors.d.ts.map