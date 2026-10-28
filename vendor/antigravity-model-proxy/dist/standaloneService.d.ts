export interface ServiceOptions {
    port: number;
    dataDirectory: string;
    token: string;
    instance: string;
    onStop?: () => void;
}
export declare function startStandaloneService(options: ServiceOptions): Promise<{
    port: number;
    stop: () => Promise<void>;
}>;
//# sourceMappingURL=standaloneService.d.ts.map