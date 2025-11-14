"""Tests for medica area schema package exports."""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from enum import EnumMeta

from pydantic import BaseModel

import app.schemas.medica_area as medica_area


def _iter_expected_exports() -> set[str]:
    """Collect schema names that should be re-exported by the package."""

    expected: set[str] = set()
    package_path = getattr(medica_area, "__path__", [])
    package_name = medica_area.__name__

    for module_info in pkgutil.iter_modules(package_path):
        module = importlib.import_module(f"{package_name}.{module_info.name}")
        for name, obj in vars(module).items():
            if name.startswith("_"):
                continue
            if not inspect.isclass(obj) or obj.__module__ != module.__name__:
                continue
            if issubclass(obj, BaseModel) or isinstance(obj, EnumMeta):
                expected.add(name)

    return expected


def test_medica_area_exports_are_complete() -> None:
    """Ensure the package exports every schema class and enum."""

    exported_names = {name for name in dir(medica_area) if not name.startswith("_")}
    expected_names = _iter_expected_exports()

    missing_exports = sorted(expected_names - exported_names)

    assert not missing_exports, (
        "Missing medica_area schema exports detected. "
        "Update app.schemas.medica_area.__init__ with: "
        f"{', '.join(missing_exports)}"
    )
