"""Phase 8 suite: release packaging + public import surface audit.

Additive only: no existing test is modified. These tests treat the packaging
metadata as an executable specification of the distribution contract.
"""
import ast
import os
import subprocess
import sys
try:
    import tomllib  # Python >= 3.11
except ModuleNotFoundError:  # pragma: no cover - exercised only on 3.9/3.10 CI
    import tomli as tomllib  # type: ignore[no-redef]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYPROJECT = os.path.join(ROOT, "pyproject.toml")

KNOWN_OPTIONAL_PROVIDERS = {"pandas", "numpy", "curl_cffi", "frida"}
ALLOWED_EXTRA_NAMES = {"pandas", "numpy", "tls", "frida", "all"}


def load_pyproject():
    with open(PYPROJECT, "rb") as fh:
        return tomllib.load(fh)


# =====================================================================
# Metadata validity
# =====================================================================
class TestPyprojectMetadata:
    def test_parses_as_valid_toml(self):
        data = load_pyproject()
        assert "project" in data

    def test_distribution_name_and_version(self):
        proj = load_pyproject()["project"]
        assert proj["name"] == "behavioral-playwright"
        assert isinstance(proj["version"], str) and proj["version"].count(".") == 2

    def test_requires_python_declared(self):
        assert load_pyproject()["project"]["requires-python"].startswith(">=")

    def test_runtime_dependency_is_exactly_pydantic_2(self):
        deps = load_pyproject()["project"]["dependencies"]
        assert deps == ["pydantic>=2"]

    def test_optional_dependencies_are_only_known_providers(self):
        extras = load_pyproject()["project"]["optional-dependencies"]
        assert set(extras) <= ALLOWED_EXTRA_NAMES
        for extra, deps in extras.items():
            if extra == "all":
                continue
            provider = deps[0].split("[")[0].split(">=")[0].strip()
            assert provider in KNOWN_OPTIONAL_PROVIDERS, f"unexpected dep {provider!r} in extra {extra!r}"
        all_deps = {d.split("[")[0] for d in extras["all"]}
        assert all_deps == KNOWN_OPTIONAL_PROVIDERS

    def test_declared_module_file_exists(self):
        mods = load_pyproject()["tool"]["setuptools"]["py-modules"]
        assert mods == ["behavioral_evasion_ten_patches_hardened_v15"]
        assert os.path.isfile(os.path.join(ROOT, mods[0] + ".py"))

    def test_no_generated_artifacts_packaged(self):
        cfg = load_pyproject()["tool"]["setuptools"]
        assert "packages" in cfg and cfg["packages"] == ["behavioral_playwright"]


# =====================================================================
# Public import surface (clean-interpreter checks)
# =====================================================================
def fresh_import(code: str):
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return proc


class TestBehavioralPlaywrightImportSurface:
    def test_clean_environment_import(self):
        proc = fresh_import("import behavioral_playwright; print('OK')")
        assert proc.returncode == 0, proc.stderr
        assert "OK" in proc.stdout

    def test_facade_and_core_namespaces_reexported(self):
        code = (
            "import behavioral_playwright as bp\n"
            "names = ['BehavioralPlaywright', 'SelfHealingSelectorEngine',\n"
            "         'SelectorHealMemory', 'QuantPersistencePipeline',\n"
            "         'QuantDataContractSentinel', 'PITQuantEngine',\n"
            "         'ElementResolutionError', 'configure_framework_logging']\n"
            "missing = [n for n in names if not hasattr(bp, n)]\n"
            "assert not missing, missing\n"
            "print('OK')\n"
        )
        proc = fresh_import(code)
        assert proc.returncode == 0, proc.stderr
        assert "OK" in proc.stdout

    def test_all_excludes_foreign_leaked_names(self):
        code = (
            "import behavioral_playwright as bp\n"
            "for bad in ('BaseModel', 'ValidationError', 'datetime', 'deque',\n"
            "            'timezone', 'Any', 'AsyncSession'):\n"
            "    assert bad not in bp.__all__, bad\n"
            "assert len(bp.__all__) > 20\n"
            "print('OK')\n"
        )
        proc = fresh_import(code)
        assert proc.returncode == 0, proc.stderr
        assert "OK" in proc.stdout

    def test_import_via_shim_installs_no_root_logger_handler(self):
        code = (
            "import logging\n"
            "before = list(logging.getLogger().handlers)\n"
            "import behavioral_playwright\n"
            "after = logging.getLogger().handlers\n"
            "assert len(after) == len(before), 'root logger mutated by import'\n"
            "print('OK')\n"
        )
        proc = fresh_import(code)
        assert proc.returncode == 0, proc.stderr
        assert "OK" in proc.stdout

    def test_single_implementation_identity_between_import_paths(self):
        code = (
            "import behavioral_playwright as shim\n"
            "import behavioral_evasion_ten_patches_hardened_v15 as impl\n"
            "assert shim.BehavioralPlaywright is impl.BehavioralPlaywright\n"
            "assert shim.SelectorHealMemory is impl.SelectorHealMemory\n"
            "print('OK')\n"
        )
        proc = fresh_import(code)
        assert proc.returncode == 0, proc.stderr
        assert "OK" in proc.stdout


class TestSourceHygiene:
    def test_module_has_no_stale_third_party_imports(self):
        """Only pydantic may appear at module level besides the stdlib."""
        src_path = os.path.join(ROOT, "behavioral_evasion_ten_patches_hardened_v15.py")
        tree = ast.parse(open(src_path, encoding="utf-8").read())
        stdlib = set(sys.stdlib_module_names)
        offenders = []
        for node in tree.body:
            names = []
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [(node.module or "").split(".")[0]]
            for name in names:
                if name and name not in stdlib and name != "pydantic":
                    offenders.append(name)
        assert not offenders, f"undeclared module-level dependencies: {offenders}"

    def test_shim_is_thin_no_logic(self):
        src_path = os.path.join(ROOT, "behavioral_playwright", "__init__.py")
        tree = ast.parse(open(src_path, encoding="utf-8").read())
        funcdefs = [
            n for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        ]
        assert not funcdefs, "shim must stay declarative; move logic to the impl module"
