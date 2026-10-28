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
exports.getRequiredProxyPort = getRequiredProxyPort;
exports.listenProxy = listenProxy;
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
/** The optional binary patch cannot follow the language server's dynamic port flag. */
function getRequiredProxyPort(appPath) {
    const marker = path.join(appPath, 'antigravity-proxy.json');
    if (!fs.existsSync(marker))
        return undefined;
    const value = JSON.parse(fs.readFileSync(marker, 'utf8'));
    if (value?.requiredPort !== 50999) {
        throw new Error('Invalid antigravity-proxy.json: the binary patch requires port 50999');
    }
    return value.requiredPort;
}
function listenProxy(server, preferredPort = 50999, allowFallback = true) {
    return new Promise((resolve, reject) => {
        let triedFallback = false;
        const onListening = () => {
            server.removeListener('error', onError);
            resolve(server.address().port);
        };
        const onError = (error) => {
            if (error.code === 'EADDRINUSE' && allowFallback && !triedFallback) {
                triedFallback = true;
                server.listen(0, '127.0.0.1');
                return;
            }
            server.removeListener('listening', onListening);
            server.removeListener('error', onError);
            if (error.code === 'EADDRINUSE' && !allowFallback) {
                error.message = `Port ${preferredPort} is occupied. The patched language server requires this exact port; close the other instance before starting Antigravity.`;
            }
            reject(error);
        };
        server.once('listening', onListening);
        server.on('error', onError);
        server.listen(preferredPort, '127.0.0.1');
    });
}
//# sourceMappingURL=listen.js.map