/** Explicit, text-only model delegation for MCP clients, including Antigravity IDE. */
import type { IncomingMessage, ServerResponse } from 'node:http';
import type { CustomModel } from './proxy';
/** Call only after the owned service's origin and bearer checks have passed. */
export declare function createModelDelegation(loadModels: () => CustomModel[]): (req: IncomingMessage, res: ServerResponse) => boolean;
//# sourceMappingURL=modelDelegation.d.ts.map