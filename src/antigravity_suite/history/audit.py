"""Audit Logger and Change Tracker for Antigravity History Merger."""
from __future__ import annotations
import datetime, os
from pathlib import Path
from typing import Any, Dict, List, Optional
from antigravity_suite.history.audit_anomalies import detect_partition_anomalies, detect_title_anomalies
from antigravity_suite.history.audit_writer import write_audit_event


class HistoryAuditLogger:
    """Records audit events and surfaces alerts for synchronization anomalies."""

    def __init__(self, log_path: Optional[Path] = None) -> None:
        if log_path is None:
            gemini_dir = os.environ.get("GEMINI_DIR") or os.path.expanduser("~/.gemini")
            self.log_path = Path(gemini_dir) / "antigravity" / "history_merger_audit.log"
        else:
            self.log_path = Path(log_path)
        self.run_id = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        self.events: List[Dict[str, Any]] = []

    def log_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """Appends and persists an event in the audit log."""
        event = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "run_id": self.run_id,
            "type": event_type,
            **details,
        }
        self.events.append(event)
        write_audit_event(self.log_path, event)

    def log_title_change(
        self,
        conv_id: str,
        old_title: str,
        new_title: str,
        reason: str,
        workspace_uri: Optional[str] = None,
    ) -> None:
        """Logs title updates and fires TITLE_WARNING if an anomaly is detected."""
        anomalies = detect_title_anomalies(new_title, old_title, workspace_uri)
        self.log_event(
            "TITLE_CHANGED",
            {
                "conv_id": conv_id,
                "old_title": old_title,
                "new_title": new_title,
                "reason": reason,
                "is_suspicious": bool(anomalies),
                "anomalies": anomalies,
            },
        )
        if anomalies:
            self.log_event(
                "TITLE_WARNING",
                {
                    "conv_id": conv_id,
                    "old_title": old_title,
                    "new_title": new_title,
                    "anomalies": anomalies,
                    "severity": "HIGH",
                },
            )

    def log_workspace_change(self, conv_id: str, old_ws: str, new_ws: str, project_id: str) -> None:
        self.log_event("WORKSPACE_CHANGED", {"conv_id": conv_id, "old_ws": old_ws, "new_ws": new_ws, "project_id": project_id})

    def log_partition_change(self, conv_id: str, old_part: str, new_part: str, reason: str, ws: Optional[str] = None) -> None:
        anomalies = detect_partition_anomalies(new_part, ws)
        self.log_event("PARTITION_CHANGED", {"conv_id": conv_id, "old": old_part, "new": new_part, "reason": reason, "anomalies": anomalies})

    def log_database_reconstruction(self, conv_id: str, transcript: str, steps: int) -> None:
        self.log_event("DATABASE_RECONSTRUCTED", {"conv_id": conv_id, "transcript": transcript, "steps": steps})

    def log_store_ingestion(self, source: str, target: str, copied: int) -> None:
        self.log_event("STORE_INGESTED", {"source": source, "target": target, "copied": copied})

    def log_symlink_action(self, target: str, link_name: str, action: str) -> None:
        self.log_event("SYMLINK_ACTION", {"target": target, "link_name": link_name, "action": action})

    def log_run_summary(self, summary_stats: Dict[str, Any]) -> None:
        self.log_event("RUN_COMPLETE", {"summary": summary_stats})


_AUDIT_LOGGER: Optional[HistoryAuditLogger] = None


def get_audit_logger(log_path: Optional[Path] = None) -> HistoryAuditLogger:
    global _AUDIT_LOGGER
    if _AUDIT_LOGGER is None or log_path is not None:
        _AUDIT_LOGGER = HistoryAuditLogger(log_path)
    return _AUDIT_LOGGER
