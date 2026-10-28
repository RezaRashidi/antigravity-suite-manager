/** Transport-independent addon actions shared by Electron IPC and the local IDE manager. */
import type { createModelManager } from './modelManagement';
export declare function createModelActions(manager: ReturnType<typeof createModelManager>): Record<string, (...args: unknown[]) => unknown>;
//# sourceMappingURL=modelActions.d.ts.map