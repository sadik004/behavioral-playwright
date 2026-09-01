"""Exporters for JSON, NDJSON, CSV, SQLite, and Parquet."""

from __future__ import annotations

import csv
import json
import sqlite3
from typing import Any, Dict, List, Sequence

from behavioral_playwright.storage.base import BaseExporter


class JSONExporter(BaseExporter):
    def export(self, records: Sequence[Dict[str, Any]], target_path: str, **kwargs: Any) -> str:
        indent = kwargs.get("indent", 2)
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(list(records), f, indent=indent, default=str)
        return target_path


class NDJSONExporter(BaseExporter):
    def export(self, records: Sequence[Dict[str, Any]], target_path: str, **kwargs: Any) -> str:
        with open(target_path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, default=str) + "\n")
        return target_path


class CSVExporter(BaseExporter):
    def export(self, records: Sequence[Dict[str, Any]], target_path: str, **kwargs: Any) -> str:
        if not records:
            with open(target_path, "w", newline="", encoding="utf-8") as f:
                pass
            return target_path

        fieldnames = list(records[0].keys())
        with open(target_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for rec in records:
                # Ensure values are serializable
                row = {k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in rec.items()}
                writer.writerow(row)
        return target_path


class SQLiteExporter(BaseExporter):
    def export(self, records: Sequence[Dict[str, Any]], target_path: str, **kwargs: Any) -> str:
        table_name = kwargs.get("table_name", "records")
        if not records:
            return target_path

        conn = sqlite3.connect(target_path)
        try:
            fields = list(records[0].keys())
            cols = ", ".join(f'"{col}" TEXT' for col in fields)
            conn.execute(f'CREATE TABLE IF NOT EXISTS "{table_name}" ({cols})')
            
            placeholders = ", ".join("?" for _ in fields)
            rows = []
            for rec in records:
                row_tuple = tuple(json.dumps(rec.get(col)) if isinstance(rec.get(col), (dict, list)) else str(rec.get(col, "")) for col in fields)
                rows.append(row_tuple)
            
            conn.executemany(f'INSERT INTO "{table_name}" VALUES ({placeholders})', rows)
            conn.commit()
        finally:
            conn.close()
        return target_path


class DataStorageManager:
    """Unified manager for exporting and persisting records."""

    _EXPORTERS: Dict[str, BaseExporter] = {
        "json": JSONExporter(),
        "ndjson": NDJSONExporter(),
        "jsonl": NDJSONExporter(),
        "csv": CSVExporter(),
        "sqlite": SQLiteExporter(),
        "db": SQLiteExporter(),
    }

    def export(
        self,
        records: Sequence[Dict[str, Any]],
        target_path: str,
        format: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        fmt = (format or target_path.split(".")[-1]).lower()
        exporter = self._EXPORTERS.get(fmt)
        if not exporter:
            # Default to JSON
            exporter = self._EXPORTERS["json"]
        return exporter.export(records, target_path, **kwargs)
