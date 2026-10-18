"""
Protobuf Summaries Binary Serialization Engine.

Atomically serializes conversation summaries to agyhub_summaries_proto.pb
and companion protobuf files for high-speed UI listing.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Dict, Optional, Set

from antigravity_suite.proto.wire import (
    encode_tag_bytes,
    extract_pure_binary_summary,
)


def serialize_master_proto(
    master_proto: Path,
    all_summaries: Dict[str, bytes],
    hub_ids: Optional[Set[str]] = None,
) -> bool:
    """Serializes in-memory summaries dictionary to binary Protobuf file atomically if changed."""
    try:
        entries_data = bytearray()
        for u_id, p_bin in sorted(all_summaries.items()):
            if hub_ids is not None and u_id not in hub_ids:
                continue
            raw = extract_pure_binary_summary(p_bin)
            if raw and len(raw) >= 10:
                entry = bytearray()
                entry += encode_tag_bytes(1, u_id.encode("utf-8"))
                entry += encode_tag_bytes(2, raw)
                entries_data += encode_tag_bytes(1, bytes(entry))

        new_bytes = bytes(entries_data)
        updated = False
        master_needs_write = True
        if master_proto.is_file():
            try:
                if master_proto.stat().st_size == len(new_bytes):
                    with open(master_proto, "rb") as cur_f:
                        if cur_f.read() == new_bytes:
                            master_needs_write = False
            except Exception:
                pass

        if master_needs_write:
            tmp_proto = str(master_proto) + ".tmp"
            with open(tmp_proto, "wb") as f:
                f.write(new_bytes)
            os.replace(tmp_proto, master_proto)
            updated = True

        parent_dir = master_proto.parent
        for companion in ["jetbox_summaries.pb", "jetbox_summaries_proto.pb", "agyhub_summaries.pb"]:
            companion_file = parent_dir / companion
            if companion_file.exists() and not companion_file.is_symlink():
                try:
                    needs_copy = False
                    if not companion_file.is_file() or companion_file.stat().st_size != len(new_bytes):
                        needs_copy = True
                    else:
                        with open(companion_file, "rb") as cf:
                            if cf.read() != new_bytes:
                                needs_copy = True
                    if needs_copy:
                        shutil.copy2(master_proto, companion_file)
                        updated = True
                except Exception:
                    pass
        return updated
    except Exception:
        return False
