#!/usr/bin/env bash
# Legacy compatibility wrappers: Conversation Forking unpatch is merged into Unified Experiments.

unpatch_fork_app() { unpatch_experiments_app "$@"; }
unpatch_fork_ide() { unpatch_experiments_ide "$@"; }
unpatch_fork_all() { unpatch_experiments_all "$@"; }
