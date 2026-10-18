"""
Cascade Trajectory Metadata Submessage and Identity Resolution.
"""

from __future__ import annotations

import re
from typing import Any, Dict

from antigravity_suite.proto.wire import read_varint

UUID_REGEX = re.compile(r"^[0-9a-fA-F-]{36}$")


def parse_metadata_submessage(val_bytes: bytes, res: Dict[Any, Any]) -> None:
    try:
        p17 = 0
        while p17 < len(val_bytes):
            tw17, p17 = read_varint(val_bytes, p17)
            w17, t17 = tw17 & 7, tw17 >> 3
            if w17 == 2:
                l17, p17 = read_varint(val_bytes, p17)
                b17 = val_bytes[p17 : p17 + l17]
                p17 += l17
                if t17 in (14, 18):
                    val = b17.decode("utf-8", "ignore")
                    res.setdefault("project_id", val)
                    res[f"has_tag_{t17}"] = True
                elif t17 == 6:
                    res["root_conversation_id"] = b17.decode("utf-8", "ignore")
                elif t17 == 7:
                    res.setdefault("workspace_uri", b17.decode("utf-8", "ignore"))
                elif t17 == 1:
                    _parse_metadata_sub_workspace(b17, res)
            elif w17 == 0:
                _, p17 = read_varint(val_bytes, p17)
            elif w17 in (1, 5):
                p17 += 8 if w17 == 1 else 4
            else:
                break
    except Exception:
        pass


def _parse_metadata_sub_workspace(b17: bytes, res: Dict[Any, Any]) -> None:
    try:
        p_sub = 0
        while p_sub < len(b17):
            tw_sub, p_sub = read_varint(b17, p_sub)
            if (tw_sub & 7) == 2:
                l_sub, p_sub = read_varint(b17, p_sub)
                sub_val = b17[p_sub : p_sub + l_sub]
                p_sub += l_sub
                if (tw_sub >> 3) == 1 and "workspace_uri" not in res:
                    res["workspace_uri"] = sub_val.decode("utf-8", "ignore")
            elif (tw_sub & 7) == 0:
                _, p_sub = read_varint(b17, p_sub)
            elif (tw_sub & 7) in (1, 5):
                p_sub += 8 if (tw_sub & 7) == 1 else 4
            else:
                break
    except Exception:
        pass


def parse_legacy_annotations(val_bytes: bytes, res: Dict[Any, Any]) -> None:
    try:
        p16 = 0
        while p16 < len(val_bytes):
            tw16, p16 = read_varint(val_bytes, p16)
            if (tw16 & 7) == 0:
                v16, p16 = read_varint(val_bytes, p16)
                if (tw16 >> 3) == 4:
                    res["last_user_step"] = v16
            elif (tw16 & 7) == 2:
                l16, p16 = read_varint(val_bytes, p16)
                p16 += l16
            else:
                break
    except Exception:
        pass


def resolve_cascade_identity(tag_strings: Dict[int, str], res: Dict[Any, Any]) -> None:
    if 4 in tag_strings and UUID_REGEX.match(tag_strings[4]):
        res["trajectory_id"] = tag_strings[4]
    elif "root_conversation_id" in res and UUID_REGEX.match(res["root_conversation_id"]):
        res["trajectory_id"] = res["root_conversation_id"]
    elif 1 in tag_strings and UUID_REGEX.match(tag_strings[1]):
        res["trajectory_id"] = tag_strings[1]

    if 1 in tag_strings and not UUID_REGEX.match(tag_strings[1]):
        res["summary"] = tag_strings[1]
    elif 4 in tag_strings and not UUID_REGEX.match(tag_strings[4]):
        res["summary"] = tag_strings[4]

    if "title" not in res or not res["title"]:
        if "summary" in res and res["summary"]:
            res["title"] = res["summary"]
