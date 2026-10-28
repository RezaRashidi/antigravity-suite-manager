import type { ToolSchemas } from './translators/utils';
interface AbsolutePath {
    readonly style: 'windows' | 'posix';
    readonly value: string;
}
/** Native context is rebuilt for every request; it is never inferred from model history. */
export interface ArtifactContext {
    readonly artifactDirectory: AbsolutePath;
    readonly workspaces: readonly AbsolutePath[];
    readonly tools: ReadonlySet<string>;
}
export declare function collectArtifactContext(body: unknown, schemas: ToolSchemas): ArtifactContext | undefined;
export declare function normalizeArtifactCandidate(candidate: unknown, context?: ArtifactContext): unknown;
export declare function normalizeArtifactResponse(response: unknown, context?: ArtifactContext): unknown;
export {};
//# sourceMappingURL=artifactMetadata.d.ts.map