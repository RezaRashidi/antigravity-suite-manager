import * as https from 'node:https';
export declare function checkPort(port: number, host?: string, timeout?: number): Promise<boolean>;
export declare function detectLocalProxy(): Promise<string | undefined>;
export declare function createTunnelAgent(proxyUrl: string): https.Agent;
export declare function getProxyAgent(customProxyUrl?: string): https.Agent | undefined;
export declare function getRelayUrl(): string | undefined;
export declare function resetProxyCache(): void;
//# sourceMappingURL=proxyAgent.d.ts.map