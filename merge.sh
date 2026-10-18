#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="${1:-.}"
OUTPUT_FILE="${2:-merged_output.txt}"

OUTPUT_ABS="$(realpath -m "$OUTPUT_FILE")"
: > "$OUTPUT_ABS"

find "$SOURCE_DIR" \
    -type d \( -name ".git" -o -name "node_modules" -o -name "__pycache__" -o -name ".venv" -o -name "venv" \) -prune -o \
    -type f \( -name "*.py" -o -name "*.js" -o -name "*.mjs" -o -name "*.sh" -o -name "*.bash" -o -name "*.txt" -o -name "*.md" \) -print0 | while IFS= read -r -d '' file; do

    if [ "$(realpath "$file")" = "$OUTPUT_ABS" ]; then
        continue
    fi

    printf '\n%s\n' "============================================================" >> "$OUTPUT_ABS"
    printf 'FILE: %s\n' "$file" >> "$OUTPUT_ABS"
    printf '%s\n\n' "============================================================" >> "$OUTPUT_ABS"

    cat "$file" >> "$OUTPUT_ABS"
    printf '\n' >> "$OUTPUT_ABS"
done

printf "عملیات تکمیل شد. فایل خروجی: %s\n" "$OUTPUT_FILE"
