"""Unit tests for data storage and exporter manager."""

import json
import os
import sqlite3
import tempfile
import pytest
from behavioral_playwright.storage.exporters import DataStorageManager


def test_storage_manager_exports():
    manager = DataStorageManager()
    sample_records = [
        {"id": 1, "title": "First Article", "tags": ["tech", "ai"]},
        {"id": 2, "title": "Second Article", "tags": ["quant", "finance"]},
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. JSON Export
        json_path = os.path.join(tmpdir, "data.json")
        manager.export(sample_records, json_path)
        with open(json_path, "r", encoding="utf-8") as f:
            loaded_json = json.load(f)
        assert len(loaded_json) == 2
        assert loaded_json[0]["id"] == 1

        # 2. NDJSON Export
        ndjson_path = os.path.join(tmpdir, "data.ndjson")
        manager.export(sample_records, ndjson_path)
        with open(ndjson_path, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]
        assert len(lines) == 2
        assert lines[1]["title"] == "Second Article"

        # 3. CSV Export
        csv_path = os.path.join(tmpdir, "data.csv")
        manager.export(sample_records, csv_path)
        with open(csv_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "First Article" in content
        assert "Second Article" in content

        # 4. SQLite Export
        sqlite_path = os.path.join(tmpdir, "data.db")
        manager.export(sample_records, sqlite_path, table_name="articles")
        conn = sqlite3.connect(sqlite_path)
        count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        conn.close()
        assert count == 2
