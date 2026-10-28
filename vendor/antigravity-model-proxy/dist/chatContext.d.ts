export interface ContextModel {
    name?: string;
    displayName?: string;
    externalModelName?: string;
    provider?: string;
    contextWindow?: number;
}
export interface ChatContextRequest {
    conversationId?: string;
    title?: string;
    modelName?: string;
    discoverLimit?: boolean;
}
export interface ChatContextUsage {
    conversationId: string;
    source: 'estimated' | 'unavailable';
    /** Visible transcript only: excludes hidden prompts, tool definitions and images. */
    currentTokens?: number;
    maxTokens?: number;
    limitSource?: 'configured' | 'public-catalog';
}
/** Never let an earlier prefix match shadow an exact model or effort variant. */
export declare function findContextModel(name: string | undefined, models: ContextModel[]): ContextModel | undefined;
/** A title is usable only when it identifies one conversation, including archived rows. */
export declare function findConversationIdByTitle(title: unknown, dataDirectory: string): string | undefined;
export declare function getChatContextUsage(conversationId: unknown, dataDirectory: string): Promise<ChatContextUsage>;
/** Exact catalog identifiers only; conflicting provider limits remain unknown. */
export declare function discoverContextLimit(modelName: string, provider?: string): Promise<number | undefined>;
export declare function getContextInformation(payload: unknown, dataDirectory: string, models: ContextModel[]): Promise<ChatContextUsage>;
//# sourceMappingURL=chatContext.d.ts.map