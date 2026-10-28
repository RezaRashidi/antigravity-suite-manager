"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.collectArtifactContext = collectArtifactContext;
exports.normalizeArtifactCandidate = normalizeArtifactCandidate;
exports.normalizeArtifactResponse = normalizeArtifactResponse;
const path = __importStar(require("node:path"));
const object = (value) => value && typeof value === 'object' && !Array.isArray(value) ? value : undefined;
const owns = (value, key) => Object.prototype.hasOwnProperty.call(value, key);
const typed = (value, type) => {
    const declared = object(value)?.type;
    return typeof declared === 'string' && declared.toLowerCase() === type;
};
const WORKSPACE_HEADER = /^The user has ([1-9]\d{0,2}) active workspaces, each defined by a URI and a CorpusName\. Multiple URIs potentially map to the same CorpusName\. The mapping is shown as follows in the format \[URI\] -> \[CorpusName\]:$/;
const METADATA_DESCRIPTIONS = new Set([
    'Metadata that defines artifact properties. Required when creating an artifact file.',
    'Metadata updates if updating an artifact file, leave blank if not updating an artifact. Should be updated if the content is changing meaningfully.',
]);
/** Compare client paths without consulting the proxy host's filesystem or operating system. */
function absolutePath(value, uri = false) {
    if (typeof value !== 'string' || !value || value.length > 32768 || value.trim() !== value)
        return undefined;
    if (uri && value.startsWith('file:')) {
        try {
            if (value.split('/').some((segment) => segment === '.' || segment === '..') || value.includes('\\'))
                return undefined;
            const parsed = new URL(value);
            if (parsed.protocol !== 'file:' ||
                parsed.username ||
                parsed.password ||
                parsed.port ||
                parsed.search ||
                parsed.hash)
                return undefined;
            // Encoded separators and dot segments have ambiguous URI/path interpretations.
            if (/%(?:2f|5c|2e)/i.test(value))
                return undefined;
            const pathname = decodeURIComponent(parsed.pathname);
            value =
                parsed.hostname && parsed.hostname !== 'localhost'
                    ? `\\\\${parsed.hostname}${pathname.replace(/\//g, '\\')}`
                    : /^\/[A-Za-z]:\//.test(pathname)
                        ? pathname.slice(1)
                        : pathname;
        }
        catch {
            return undefined;
        }
    }
    if (typeof value !== 'string' || /[\x00-\x1f\x7f<>]/.test(value))
        return undefined;
    const windows = /^[A-Za-z]:[\\/]/.test(value) || /^\\\\[^\\/]+[\\/][^\\/]+/.test(value);
    if (windows) {
        if (/^\\\\[?.][\\/]/.test(value))
            return undefined;
        const rest = /^[A-Za-z]:/.test(value) ? value.slice(2) : value;
        if (/[|"?:*]/.test(rest))
            return undefined;
        const segments = rest.split(/[\\/]+/).filter(Boolean);
        if (segments.some((segment) => segment === '.' || segment === '..' || /[ .]$/.test(segment)))
            return undefined;
        return {
            style: 'windows',
            value: path.win32
                .normalize(value)
                .replace(/[\\/]+$/, '')
                .toLowerCase(),
        };
    }
    if (!value.startsWith('/') || value.startsWith('//') || value.includes('\\'))
        return undefined;
    if (value.split('/').some((segment) => segment === '.' || segment === '..'))
        return undefined;
    return { style: 'posix', value: path.posix.normalize(value).replace(/\/+$/, '') || '/' };
}
function contains(directory, target) {
    if (directory.style !== target.style)
        return false;
    const separator = directory.style === 'windows' ? '\\' : '/';
    return target.value === directory.value || target.value.startsWith(directory.value.replace(/[\\/]$/, '') + separator);
}
function nativeOptionalMetadata(name, value) {
    if (!['write_to_file', 'replace_file_content', 'multi_replace_file_content'].includes(name))
        return false;
    const schema = object(value), properties = object(schema?.properties);
    if (!schema || !properties || !typed(schema, 'object') || !Array.isArray(schema.required))
        return false;
    // Do not guess whether metadata is optional through references/conditional schemas.
    if ([
        '$ref',
        'allOf',
        'anyOf',
        'oneOf',
        'not',
        'if',
        'then',
        'else',
        'dependencies',
        'dependentRequired',
        'dependentSchemas',
    ].some((key) => owns(schema, key)))
        return false;
    if (!schema.required.includes('TargetFile') ||
        schema.required.includes('ArtifactMetadata') ||
        !typed(properties.TargetFile, 'string'))
        return false;
    const metadata = object(properties.ArtifactMetadata), fields = object(metadata?.properties);
    if (!metadata || !fields || !typed(metadata, 'object') || !METADATA_DESCRIPTIONS.has(String(metadata.description)))
        return false;
    if (!typed(fields.Summary, 'string') ||
        !typed(fields.UserFacing, 'boolean') ||
        !typed(fields.RequestFeedback, 'boolean'))
        return false;
    const metadataRequired = metadata.required, required = schema.required;
    if (!Array.isArray(metadataRequired) ||
        !['Summary', 'UserFacing', 'RequestFeedback'].every((key) => metadataRequired.includes(key)))
        return false;
    const payloadFields = name === 'write_to_file'
        ? ['CodeContent']
        : name === 'replace_file_content'
            ? ['TargetContent', 'ReplacementContent']
            : ['ReplacementChunks'];
    return payloadFields.every((key) => required.includes(key) && typed(properties[key], key === 'ReplacementChunks' ? 'array' : 'string'));
}
function collectArtifactContext(body, schemas) {
    const parts = object(object(body)?.systemInstruction)?.parts;
    if (!Array.isArray(parts))
        return undefined;
    const text = parts.map((part) => (typeof object(part)?.text === 'string' ? object(part).text : '')).join('');
    if (text.length > 2 * 1024 * 1024)
        return undefined;
    const lines = text.split(/\r?\n/);
    const starts = lines.flatMap((line, index) => (line === '<artifacts>' ? [index] : []));
    const ends = lines.flatMap((line, index) => (line === '</artifacts>' ? [index] : []));
    if (starts.length !== 1 || ends.length !== 1 || ends[0] <= starts[0])
        return undefined;
    const roots = lines.slice(starts[0] + 1, ends[0]).filter((line) => line.startsWith('Artifact Directory Path: '));
    if (roots.length !== 1)
        return undefined;
    const artifactDirectory = absolutePath(roots[0].slice('Artifact Directory Path: '.length));
    if (!artifactDirectory)
        return undefined;
    const headers = lines.flatMap((line, index) => (WORKSPACE_HEADER.test(line) ? [index] : []));
    if (headers.length !== 1)
        return undefined;
    const header = headers[0], count = Number(WORKSPACE_HEADER.exec(lines[header])[1]);
    const mappings = lines
        .slice(header + 1)
        .filter((line) => line.trim())
        .slice(0, count);
    if (mappings.length !== count)
        return undefined;
    const workspaces = [];
    for (const mapping of mappings) {
        const pieces = mapping.split(' -> ');
        if (pieces.length !== 2 || !pieces[1].trim())
            return undefined;
        const workspace = absolutePath(pieces[0], true);
        if (!workspace || workspace.style !== artifactDirectory.style)
            return undefined;
        workspaces.push(workspace);
    }
    const tools = new Set([...schemas].filter(([name, schema]) => nativeOptionalMetadata(name, schema)).map(([name]) => name));
    return tools.size ? { artifactDirectory, workspaces, tools } : undefined;
}
function normalizeArtifactCandidate(candidate, context) {
    const record = object(candidate), content = object(record?.content);
    if (!context || !record || !content || !Array.isArray(content.parts))
        return candidate;
    let changed = false;
    const parts = content.parts.map((part) => {
        const item = object(part), call = object(item?.functionCall), args = object(call?.args);
        if (!item ||
            !call ||
            typeof call.name !== 'string' ||
            !context.tools.has(call.name) ||
            !args ||
            !owns(args, 'ArtifactMetadata'))
            return part;
        const target = absolutePath(args.TargetFile), metadata = object(args.ArtifactMetadata);
        if (!target || !metadata || typeof args.TargetFile !== 'string' || /[\\/]$/.test(args.TargetFile))
            return part;
        if (Object.keys(metadata).some((key) => !['Summary', 'UserFacing', 'RequestFeedback'].includes(key)) ||
            typeof metadata.Summary !== 'string' ||
            typeof metadata.UserFacing !== 'boolean' ||
            typeof metadata.RequestFeedback !== 'boolean')
            return part;
        if (contains(context.artifactDirectory, target) ||
            !context.workspaces.some((workspace) => target.value !== workspace.value && contains(workspace, target)))
            return part;
        const normalized = { ...args };
        delete normalized.ArtifactMetadata;
        changed = true;
        return { ...item, functionCall: { ...call, args: normalized } };
    });
    return changed ? { ...record, content: { ...content, parts } } : candidate;
}
function normalizeArtifactResponse(response, context) {
    const record = object(response);
    if (!context || !record || !Array.isArray(record.candidates))
        return response;
    const original = record.candidates;
    const candidates = original.map((candidate) => normalizeArtifactCandidate(candidate, context));
    return candidates.some((candidate, index) => candidate !== original[index]) ? { ...record, candidates } : response;
}
//# sourceMappingURL=artifactMetadata.js.map