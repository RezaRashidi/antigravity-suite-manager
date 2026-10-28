"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.debug = exports.error = exports.warn = exports.info = void 0;
/** Mock for electron-log */
const log = {
    info: (..._args) => { },
    warn: (..._args) => { },
    error: (..._args) => { },
    debug: (..._args) => { },
    verbose: (..._args) => { },
};
exports.default = log;
exports.info = log.info;
exports.warn = log.warn;
exports.error = log.error;
exports.debug = log.debug;
//# sourceMappingURL=electron-log.js.map