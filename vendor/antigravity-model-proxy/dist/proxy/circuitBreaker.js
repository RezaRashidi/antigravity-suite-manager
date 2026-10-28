"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.CircuitBreaker = void 0;
/** One half-open probe per model; other callers use their configured fallback. */
class CircuitBreaker {
    constructor(now = Date.now) {
        this.now = now;
        this.states = new Map();
    }
    acquire(key, options = {}) {
        if (options.enabled === false)
            return true;
        const state = this.states.get(key);
        if (!state || state.openedAt === undefined)
            return true;
        if (state.probing || this.now() - state.openedAt < (options.cooldownMs ?? 30000))
            return false;
        state.probing = true;
        return true;
    }
    succeed(key) {
        this.states.delete(key);
    }
    fail(key, options = {}) {
        if (options.enabled === false)
            return;
        const state = this.states.get(key) || { failures: 0, probing: false };
        state.failures += 1;
        if (state.probing || state.failures >= (options.failureThreshold ?? 3))
            state.openedAt = this.now();
        state.probing = false;
        this.states.set(key, state);
    }
    cancel(key) {
        const state = this.states.get(key);
        if (state)
            state.probing = false;
    }
    snapshot() {
        const states = [...this.states.values()];
        return {
            tracked: states.length,
            open: states.filter((s) => s.openedAt !== undefined).length,
            probing: states.filter((s) => s.probing).length,
        };
    }
}
exports.CircuitBreaker = CircuitBreaker;
//# sourceMappingURL=circuitBreaker.js.map