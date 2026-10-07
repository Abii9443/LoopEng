"""Storage for code review traces."""
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from src.config import settings
from src.models.review_models import Trace


class TraceStore:
    """Manages storage and retrieval of review traces."""

    def __init__(self, storage_dir: Path = None):
        """
        Initialize trace storage.

        Args:
            storage_dir: Directory to store traces. Uses config default if None.
        """
        self.storage_dir = storage_dir or settings.traces_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save(self, trace: Trace) -> Path:
        """
        Save a trace to disk.

        Args:
            trace: Trace object to save

        Returns:
            Path to the saved trace file
        """
        timestamp = trace.timestamp.strftime("%Y%m%d_%H%M%S")
        filename = f"trace_{timestamp}_{trace.id[:8]}.json"
        filepath = self.storage_dir / filename

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                # Convert to dict and handle datetime serialization
                trace_dict = trace.model_dump()
                trace_dict['timestamp'] = trace.timestamp.isoformat()
                trace_dict['verified_review']['review']['timestamp'] = trace.verified_review.review.timestamp.isoformat()

                json.dump(trace_dict, f, indent=2, default=str)

            return filepath

        except Exception as e:
            print(f"Error saving trace: {e}")
            raise

    def load(self, trace_id: str) -> Optional[Trace]:
        """
        Load a specific trace by ID.

        Args:
            trace_id: Trace ID to load

        Returns:
            Trace object or None if not found
        """
        # Find file with this ID
        for filepath in self.storage_dir.glob(f"trace_*_{trace_id[:8]}.json"):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Convert ISO strings back to datetime
                    data['timestamp'] = datetime.fromisoformat(data['timestamp'])
                    data['verified_review']['review']['timestamp'] = datetime.fromisoformat(
                        data['verified_review']['review']['timestamp']
                    )
                    return Trace(**data)
            except Exception as e:
                print(f"Error loading trace {trace_id}: {e}")
                return None

        return None

    def get_recent(self, n: int = 10) -> List[Trace]:
        """
        Get the N most recent traces.

        Args:
            n: Number of traces to retrieve

        Returns:
            List of Trace objects, most recent first
        """
        traces = []

        # Get all trace files, sorted by modification time (newest first)
        trace_files = sorted(
            self.storage_dir.glob("trace_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        for filepath in trace_files[:n]:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Convert ISO strings back to datetime
                    data['timestamp'] = datetime.fromisoformat(data['timestamp'])
                    data['verified_review']['review']['timestamp'] = datetime.fromisoformat(
                        data['verified_review']['review']['timestamp']
                    )
                    traces.append(Trace(**data))
            except Exception as e:
                print(f"Error loading trace from {filepath}: {e}")
                continue

        return traces

    def count(self) -> int:
        """
        Count total number of stored traces.

        Returns:
            Number of trace files
        """
        return len(list(self.storage_dir.glob("trace_*.json")))

    def get_all(self) -> List[Trace]:
        """
        Load all traces.

        Returns:
            List of all Trace objects
        """
        return self.get_recent(n=9999)  # Get all traces
