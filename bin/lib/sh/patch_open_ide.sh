#!/usr/bin/env bash
# Legacy compatibility wrapper: Native 'Open in IDE' button is merged into Unified Experiments.

patch_open_ide_app() { patch_experiments_app "$@"; }
