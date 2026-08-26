"""Phase 14 suite: package/distribution hardening.

These tests BUILD the real wheel (pip wheel, no deps) into a temporary
directory and verify its contents -- the Phase 8 "wheel unverifiable"
limitation is closed. Build tooling is required; failures are honest.
"""
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

try:
    import tomllib  # Python >= 3.11
except ModuleNotFoundError:  # pragma: no cover - exercised only on 3.9/3.10 CI
    import tomli as tomllib  # type: ignore[no-redef]

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_NAME = "behavioral_evasion_ten_patches_hardened_v15"


def load_pyproject():
    with open(REPO_ROOT / "pyproject.toml", "rb") as f:
        return tomllib.load(f)


def build_wheel(tmp_path: Path) -> Path:
    out = tmp_path / "wheelhouse"
    result = subprocess.run(
        [sys.executable, "-m", "pip", "wheel", str(REPO_ROOT),
         "--no-deps", "-w", str(out)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"pip wheel failed:\n{result.stdout}\n{result.stderr}"
    wheels = list(out.glob("*.whl"))
    assert len(wheels) == 1
    return wheels[0]


class TestWheelBuild:
    def test_wheel_builds_successfully(self, tmp_path):
        whl = build_wheel(tmp_path)
        assert whl.name.startswith("behavioral_playwright-")

    def test_wheel_payload_is_exactly_module_plus_shim(self, tmp_path):
        whl = build_wheel(tmp_path)
        with zipfile.ZipFile(whl) as z:
            payload = {
                n for n in z.namelist()
                if not n.split("/")[0].endswith(".dist-info")
            }
        assert payload == {f"{MODULE_NAME}.py", "behavioral_playwright/__init__.py"}

    def test_wheel_carries_no_generated_artifacts(self, tmp_path):
        whl = build_wheel(tmp_path)
        with zipfile.ZipFile(whl) as z:
            names = z.namelist()
        forbidden = ("__pycache__", ".pytest_cache", ".db", ".ndjson",
                     ".log", ".tmp", ".corrupt", "tests/", "dist/", "build/")
        for name in names:
            for marker in forbidden:
                assert marker not in name, f"generated artifact in wheel: {name}"

    def test_wheel_metadata_matches_pyproject(self, tmp_path):
        pyproject = load_pyproject()
        project = pyproject["project"]
        whl = build_wheel(tmp_path)
        with zipfile.ZipFile(whl) as z:
            meta_name = [n for n in z.namelist() if n.endswith("METADATA")][0]
            metadata = z.read(meta_name).decode("utf-8")
        assert f"Name: {project['name']}" in metadata
        assert f"Version: {project['version']}" in metadata
        assert f"Requires-Python: {project['requires-python']}" in metadata
        assert "Requires-Dist: pydantic>=2" in metadata


class TestDistributionMetadata:
    def test_version_was_bumped_for_feature_release(self):
        project = load_pyproject()["project"]
        # 1.0.0 was the Phase 8 baseline; resilience/observability/UX work
        # justifies a minor bump. Guard against accidental downgrade.
        major, minor, _ = (int(p) for p in project["version"].split("."))
        assert (major, minor) >= (1, 1)

    def test_requires_python_stays_39_floor(self):
        assert load_pyproject()["project"]["requires-python"] == ">=3.9"

    def test_runtime_dependency_boundary_unchanged(self):
        """Only pydantic is required at runtime; everything else stays optional."""
        deps = load_pyproject()["project"]["dependencies"]
        assert deps == ["pydantic>=2"]

    def test_declared_build_files_exist(self):
        project = load_pyproject()
        tool = project["tool"]["setuptools"]
        for module in tool["py-modules"]:
            assert (REPO_ROOT / f"{module}.py").exists()
        for package in tool["packages"]:
            assert (REPO_ROOT / package.replace(".", "/") / "__init__.py").exists()

    @pytest.mark.parametrize("py_file", [
        MODULE_NAME + ".py",
        "behavioral_playwright/__init__.py",
        "conftest.py",
    ])
    def test_source_parses_under_target_syntax(self, py_file):
        import ast
        ast.parse((REPO_ROOT / py_file).read_text(encoding="utf-8"))
