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
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.configureCredentialDirectory = configureCredentialDirectory;
exports.backupFile = backupFile;
exports.isEncryptionAvailable = isEncryptionAvailable;
exports.encryptString = encryptString;
exports.decryptString = decryptString;
exports.encryptModels = encryptModels;
exports.decryptModels = decryptModels;
// eslint-disable-next-line @typescript-eslint/no-var-requires
const { safeStorage, app } = (() => {
    try {
        return require('electron');
    }
    catch {
        return {};
    }
})();
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const crypto_1 = require("crypto");
const os = __importStar(require("node:os"));
const electron_log_1 = __importDefault(require("electron-log"));
let credentialDirectory;
/** Set before reading credentials when running the owned Node proxy service. */
function configureCredentialDirectory(directory) {
    credentialDirectory = path.resolve(directory);
}
function localKey(create) {
    const directory = credentialDirectory || path.join(app?.getPath('home') || os.homedir(), '.gemini', 'antigravity');
    const filename = path.join(directory, '.model-credentials-key');
    if (create && !fs.existsSync(filename)) {
        fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
        try {
            fs.writeFileSync(filename, (0, crypto_1.randomBytes)(32), { mode: 0o600, flag: 'wx' });
        }
        catch (error) {
            if (error.code !== 'EEXIST')
                throw error;
        }
    }
    const key = fs.readFileSync(filename);
    if (key.length !== 32)
        throw new Error('Invalid local credential encryption key');
    return key;
}
function encryptLocal(value) {
    const iv = (0, crypto_1.randomBytes)(12);
    const cipher = (0, crypto_1.createCipheriv)('aes-256-gcm', localKey(true), iv);
    const encrypted = Buffer.concat([cipher.update(value, 'utf8'), cipher.final()]);
    return 'local-gcm:' + Buffer.concat([iv, cipher.getAuthTag(), encrypted]).toString('base64');
}
/**
 * Creates a backup of the specified file with a .bak extension.
 */
function backupFile(filePath) {
    try {
        if (fs.existsSync(filePath)) {
            const backupPath = filePath + '.bak';
            fs.copyFileSync(filePath, backupPath);
            electron_log_1.default.info('[CryptoStore] Credential backup created.');
        }
    }
    catch {
        electron_log_1.default.error('[CryptoStore] Could not create credential backup. Check file permissions and available disk space.');
    }
}
/**
 * Checks if Electron's safeStorage API is fully functional on the current system.
 */
function isEncryptionAvailable() {
    try {
        return !!(safeStorage && safeStorage.isEncryptionAvailable());
    }
    catch (_e) {
        return false;
    }
}
/**
 * Use OS-backed storage when available; otherwise AES-GCM with a local user key.
 */
function encryptString(plainText) {
    if (!plainText || plainText === 'none')
        return plainText;
    if (isEncryptionAvailable()) {
        try {
            const buffer = safeStorage.encryptString(plainText);
            return 'enc:' + buffer.toString('base64');
        }
        catch {
            electron_log_1.default.error('[CryptoStore] safeStorage encryption failed; using local authenticated encryption.');
            return encryptLocal(plainText);
        }
    }
    else {
        return encryptLocal(plainText);
    }
}
/**
 * Decrypts a previously encrypted string. Handles safeStorage, base64 fallback, and plaintext gracefully.
 */
function decryptString(encryptedText) {
    if (!encryptedText || encryptedText === 'none')
        return encryptedText;
    if (encryptedText.startsWith('local-gcm:')) {
        try {
            const bytes = Buffer.from(encryptedText.slice(10), 'base64');
            if (bytes.length < 28)
                throw new Error('Truncated ciphertext');
            const cipher = (0, crypto_1.createDecipheriv)('aes-256-gcm', localKey(false), bytes.subarray(0, 12));
            cipher.setAuthTag(bytes.subarray(12, 28));
            return Buffer.concat([cipher.update(bytes.subarray(28)), cipher.final()]).toString('utf8');
        }
        catch {
            electron_log_1.default.error('[CryptoStore] Local credentials could not be decrypted. Check the credential key or re-enter the key.');
            return 'DECRYPTION_FAILED';
        }
    }
    if (encryptedText.startsWith('enc:')) {
        const base64Data = encryptedText.substring(4);
        if (isEncryptionAvailable()) {
            try {
                const buffer = Buffer.from(base64Data, 'base64');
                return safeStorage.decryptString(buffer);
            }
            catch {
                electron_log_1.default.error('[CryptoStore] OS-backed credentials could not be decrypted. Re-enter them in the model manager.');
                return 'DECRYPTION_FAILED';
            }
        }
        else {
            electron_log_1.default.error('[CryptoStore] OS-encrypted credentials are unavailable in this runtime. Re-enter them in its model manager.');
            return 'DECRYPTION_FAILED_STORAGE_UNAVAILABLE';
        }
    }
    else if (encryptedText.startsWith('fallback:')) {
        const base64Data = encryptedText.substring(9);
        try {
            return Buffer.from(base64Data, 'base64').toString('utf-8');
        }
        catch {
            electron_log_1.default.error('[CryptoStore] Legacy credentials could not be decoded. Re-enter them in the model manager.');
            return 'DECRYPTION_FAILED';
        }
    }
    // Plaintext (older config, not yet migrated)
    return encryptedText;
}
/**
 * Iterates through a list of custom models and encrypts their API keys.
 */
function encryptModels(models) {
    if (!models || !Array.isArray(models))
        return [];
    return models.map((model) => {
        if (model.apiKey && model.apiKey !== 'none' && !model.encrypted) {
            return {
                ...model,
                apiKey: encryptString(model.apiKey),
                encrypted: true,
            };
        }
        return model;
    });
}
/**
 * Iterates through a list of custom models and decrypts their API keys for in-memory use.
 */
function decryptModels(models) {
    if (!models || !Array.isArray(models))
        return [];
    return models.map((model) => {
        if (model.encrypted) {
            return {
                ...model,
                apiKey: decryptString(model.apiKey),
                encrypted: false,
            };
        }
        return model;
    });
}
//# sourceMappingURL=cryptoStore.js.map