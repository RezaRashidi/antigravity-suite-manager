"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.runGenerationProbe = runGenerationProbe;
const node_stream_1 = require("node:stream");
const customRequest_1 = require("./proxy/customRequest");
/** A bounded response sink exercises the real request path without opening another listening port. */
class ProbeResponse extends node_stream_1.Writable {
    constructor() {
        super(...arguments);
        this.statusCode = 200;
        this.headersSent = false;
        this.bytes = 0;
    }
    writeHead(status) {
        this.statusCode = status;
        this.headersSent = true;
        return this;
    }
    _write(chunk, _encoding, done) {
        this.bytes += chunk.length;
        if (this.bytes > 256 * 1024)
            return done(new Error('Generation test response exceeds limit'));
        done();
    }
}
/** Explicitly invoked only. One short generation; no retries, tools, user prompt or fallback models. */
async function runGenerationProbe(input) {
    const startedAt = Date.now();
    const response = new ProbeResponse();
    response.on('error', () => { });
    const model = {
        ...input,
        enabled: true,
        maxRetries: 0,
        fallbackModels: [],
        timeout: 30000,
        retryBudgetMs: 30000,
        maxOutputTokens: 32,
        extraBody: undefined,
        thinkingBudget: undefined,
        circuitBreaker: { enabled: false },
    };
    await (0, customRequest_1.runCustomModelRequest)(response, model, { contents: [{ role: 'user', parts: [{ text: 'Reply with OK.' }] }], generationConfig: { maxOutputTokens: 32 } }, false, [model], false, 'generation-test');
    if (response.statusCode < 200 || response.statusCode >= 300 || response.errored)
        return {
            success: false,
            status: response.statusCode,
            error: `Generation failed (HTTP ${response.statusCode}). Check model access, provider quota, configuration and the 32-token test output limit.`,
        };
    return {
        success: true,
        status: response.statusCode,
        message: `Generation succeeded (HTTP ${response.statusCode}, ${Date.now() - startedAt} ms).`,
    };
}
//# sourceMappingURL=generationProbe.js.map