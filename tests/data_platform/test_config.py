from pathlib import Path

from data_platform.config import Settings


def test_allowed_domains_can_be_loaded_from_comma_separated_string() -> None:
    settings = Settings(allowed_domains="hus.vnu.edu.vn,tuyensinh.hus.vnu.edu.vn")

    assert settings.allowed_domains == ("hus.vnu.edu.vn", "tuyensinh.hus.vnu.edu.vn")


def test_data_paths_resolve_under_project_root(tmp_path: Path) -> None:
    settings = Settings(project_root=tmp_path, data_root=Path("data"))

    assert settings.resolved_data_root == tmp_path / "data"
    assert settings.raw_web_root == tmp_path / "data" / "raw" / "web"
    assert settings.metadata_root == tmp_path / "data" / "metadata"
