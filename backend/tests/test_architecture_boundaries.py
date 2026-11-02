"""
Strict AST and architectural boundary verification.
Ensures zero cyclic or unauthorized imports across modules, and no Gnani field leakage.
"""
from __future__ import annotations

import ast
from pathlib import Path


def test_communication_does_not_import_campaigns():
    """Verify backend/app/communication never imports backend/app/campaigns."""
    comm_dir = Path("backend/app/communication")
    for py_file in comm_dir.glob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "campaigns" not in alias.name, f"Forbidden import of campaigns in {py_file}"
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                assert "campaigns" not in mod, f"Forbidden from-import of campaigns in {py_file}"


def test_campaigns_does_not_import_providers_or_voice():
    """Verify backend/app/campaigns never imports providers or voice modules."""
    camp_dir = Path("backend/app/campaigns")
    for py_file in camp_dir.glob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "providers" not in alias.name, f"Forbidden import of providers in {py_file}"
                    assert "voice" not in alias.name, f"Forbidden import of voice in {py_file}"
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                assert "providers" not in mod, f"Forbidden from-import of providers in {py_file}"
                assert "voice" not in mod, f"Forbidden from-import of voice in {py_file}"


def test_no_gnani_field_names_outside_providers():
    """Verify Gnani provider-specific field names do not leak into app domain models."""
    gnani_fields = ["audio_file", "audio_content"]
    app_dir = Path("backend/app")

    for py_file in app_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        for gf in gnani_fields:
            assert gf not in content, (
                f"Gnani wire field name '{gf}' detected in domain file {py_file}"
            )
