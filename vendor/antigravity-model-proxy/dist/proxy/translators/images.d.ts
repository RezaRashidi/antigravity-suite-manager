export interface GeminiImagePart {
    inlineData?: {
        mimeType: string;
        data: string;
    };
    fileData?: {
        mimeType?: string;
        fileUri: string;
    };
}
type ImageMimeType = 'image/jpeg' | 'image/png' | 'image/gif' | 'image/webp';
export type ImageSource = {
    type: 'base64';
    media_type: ImageMimeType;
    data: string;
} | {
    type: 'url';
    url: string;
};
export declare function hasImagePart(part: GeminiImagePart): boolean;
export declare function assertUserImageParts(parts: GeminiImagePart[], role: string): void;
/** Converting a file URL must never turn an attachment into a remote SMB read. */
export declare function localFilePath(url: URL): string;
/** Never fetch remote URLs here; the selected provider resolves them. */
export declare function getImageSource(part: GeminiImagePart): ImageSource | undefined;
export {};
//# sourceMappingURL=images.d.ts.map