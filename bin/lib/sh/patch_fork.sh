#!/usr/bin/env bash
# Legacy compatibility wrappers: Conversation Forking is merged into Unified Experiments.

patch_fork_app() { patch_experiments_app "$@"; }
patch_fork_ide() { patch_experiments_ide "$@"; }
patch_fork_all() { patch_experiments_all "$@"; }
