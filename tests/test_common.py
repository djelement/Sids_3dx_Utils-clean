import pytest

from sids_3dx_utils import coerce_path, ensure_list, normalize_name


def test_normalize_name_trims_and_collapses_whitespace():
    assert normalize_name("  3DX   Utility   Name  ") == "3DX Utility Name"


def test_normalize_name_rejects_empty_values():
    with pytest.raises(ValueError):
        normalize_name("   ")


def test_coerce_path_expands_user_home():
    path = coerce_path("~/example/project")
    assert "example" in path
    assert path.startswith("~") or path.startswith("C:") or path.startswith("/")


def test_ensure_list_handles_scalar_and_collection_values():
    assert ensure_list("alpha") == ["alpha"]
    assert ensure_list(["alpha", "beta"]) == ["alpha", "beta"]
    assert ensure_list(None) == []
    assert ensure_list(42) == [42]
