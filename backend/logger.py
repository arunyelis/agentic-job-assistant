import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class JsonLogger:
    """Small JSONL logger that records metadata, never user content."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self._lock = asyncio.Lock()

    async def write(self, event: str, **fields: Any) -> None:
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event": event,
            **fields,
        }
        line = json.dumps(record, ensure_ascii=True, default=str)

        async with self._lock:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with self.file_path.open("a", encoding="utf-8") as log_file:
                log_file.write(f"{line}\n")
