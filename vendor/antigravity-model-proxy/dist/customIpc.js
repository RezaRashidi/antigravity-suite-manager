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
exports.registerCustomModelHandlers = registerCustomModelHandlers;
/** Addon-owned channels only; vendor desktop APIs are left intact. */
const electron_1 = require("electron");
const path = __importStar(require("node:path"));
const cryptoStore = __importStar(require("./cryptoStore"));
const modelManagement_1 = require("./modelManagement");
const modelActions_1 = require("./modelActions");
function registerCustomModelHandlers() {
    const manager = (0, modelManagement_1.createModelManager)(path.join(electron_1.app.getPath('home'), '.gemini', 'antigravity'), cryptoStore, (url) => electron_1.shell.openExternal(url));
    const handle = (channel, action) => {
        electron_1.ipcMain.handle(channel, async (_event, ...args) => {
            try {
                return await action(...args);
            }
            catch (error) {
                if (channel === 'storage:get-custom-models' || channel === 'storage:export-custom-models')
                    throw error;
                const status = error.status;
                return { success: false, error: error.message, ...(status ? { status } : {}) };
            }
        });
    };
    for (const [channel, action] of Object.entries((0, modelActions_1.createModelActions)(manager)))
        handle(channel, action);
}
//# sourceMappingURL=customIpc.js.map