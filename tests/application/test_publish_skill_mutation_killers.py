"""Mutation-killing tests for PublishPack and InstallFromUrl use cases."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from skill_forge.application.use_cases.publish_skill import (
    PublishPack,
    PublishPackRequest,
)
from skill_forge.domain.model import (
    SkillPackManifest,
    SkillRef,
    Owner,
    PublishMetadata,
    PublishResult,
)

@pytest.fixture
def mock_publisher() -> MagicMock:
    return MagicMock()

@pytest.fixture
def mock_packer() -> MagicMock:
    return MagicMock()

@pytest.fixture
def use_case(mock_publisher: MagicMock, mock_packer: MagicMock) -> PublishPack:
    return PublishPack(publisher=mock_publisher, packer=mock_packer)

def test_publish_metadata_mapping_and_overrides(
    use_case: PublishPack, mock_publisher: MagicMock, mock_packer: MagicMock, tmp_path: Path
) -> None:
    # Set up
    pack_path = tmp_path / "test.skillpack"
    pack_path.write_bytes(b"content")
    
    manifest = SkillPackManifest(
        name="p", version="1", 
        author="a", created_at="now",
        description="manifest desc",
        tags=("m-tag",),
        platforms=("m-platform",),
        export_formats=("m-fmt",),
        owner=Owner(name="m-name", email="m@e.com"),
        skills=(SkillRef(name="s", category="c", version="1"),)
    )
    mock_packer.read_manifest.return_value = manifest
    
    # Request overrides some but not all
    request = PublishPackRequest(
        pack_path=pack_path,
        tags=("r-tag",),
        owner_name="r-name",
        owner_email="r@e.com",
        deprecated=True
    )
    
    use_case.execute(request)
    
    # Verify exact PublishMetadata passed to publisher
    # tags -> overridden by request
    # description -> from manifest
    # platforms -> from manifest
    # owner -> overridden by request
    # deprecated -> from request (True)
    expected_metadata = PublishMetadata(
        description="manifest desc",
        tags=("r-tag",),
        platforms=("m-platform",),
        export_formats=("m-fmt",),
        owner=Owner(name="r-name", email="r@e.com"),
        deprecated=True
    )
    
    mock_publisher.publish.assert_called_once_with(
        pack_path=pack_path,
        manifest=manifest,
        message="",
        push=False,
        metadata=expected_metadata
    )

def test_missing_metadata_error_messages(use_case: PublishPack, mock_packer: MagicMock, tmp_path: Path) -> None:
    pack_path = tmp_path / "test.skillpack"
    pack_path.write_bytes(b"")
    
    # Manifest with empty/missing fields
    manifest = SkillPackManifest(
        name="p", version="1", 
        author="a", created_at="now",
        description="",
        tags=(),
        owner=None,
        skills=(SkillRef(name="s", category="c", version="1"),)
    )
    mock_packer.read_manifest.return_value = manifest
    
    request = PublishPackRequest(pack_path=pack_path)
    
    with pytest.raises(ValueError) as exc:
        use_case.execute(request)
    
    err_msg = str(exc.value)
    assert "description is required" in err_msg
    assert "at least one tag is required" in err_msg
    assert "owner name and email are required" in err_msg

def test_publish_metadata_fallbacks(
    use_case: PublishPack, mock_publisher: MagicMock, mock_packer: MagicMock, tmp_path: Path
) -> None:
    """Verify that when request fields are empty, manifest fields are used."""
    pack_path = tmp_path / "test.skillpack"
    pack_path.write_bytes(b"content")
    
    manifest = SkillPackManifest(
        name="p", version="1", 
        author="a", created_at="now",
        description="manifest desc",
        tags=("m-tag",),
        platforms=("m-platform",),
        export_formats=("m-fmt",),
        owner=Owner(name="m-name", email="m@e.com"),
        skills=(SkillRef(name="s", category="c", version="1"),)
    )
    mock_packer.read_manifest.return_value = manifest
    
    # Request with minimal fields (defaults)
    request = PublishPackRequest(pack_path=pack_path)
    
    use_case.execute(request)
    
    # Verify everything fell back to manifest
    expected_metadata = PublishMetadata(
        description="manifest desc",
        tags=("m-tag",),
        platforms=("m-platform",),
        export_formats=("m-fmt",),
        owner=Owner(name="m-name", email="m@e.com"),
        deprecated=False
    )
    
    mock_publisher.publish.assert_called_with(
        pack_path=pack_path,
        manifest=manifest,
        message="",
        push=False,
        metadata=expected_metadata
    )

def test_publish_pack_missing_error_message(use_case: PublishPack, tmp_path: Path) -> None:
    missing = tmp_path / "ghost.skillpack"
    with pytest.raises(FileNotFoundError) as exc:
        use_case.execute(PublishPackRequest(pack_path=missing))
    assert f"Pack does not exist: '{missing}'" in str(exc.value)
    assert "Run 'skills-forge pack <skill-dir>' first" in str(exc.value)

def test_read_description_fallback_logic(mock_publisher: MagicMock, mock_packer: MagicMock, tmp_path: Path) -> None:
    pack_path = tmp_path / "test.skillpack"
    pack_path.write_bytes(b"")
    
    manifest = SkillPackManifest(
        name="p", version="1", 
        author="a", created_at="now",
        description="", # Empty in manifest
        tags=("t",),
        owner=Owner("o", "o@e.com"),
        skills=(SkillRef(name="s", category="dev", version="1"),)
    )
    mock_packer.read_manifest.return_value = manifest
    
    mock_parser = MagicMock()
    mock_skill = MagicMock()
    mock_skill.description.text = "description from SKILL.md"
    mock_parser.parse.return_value = mock_skill
    
    use_case = PublishPack(publisher=mock_publisher, packer=mock_packer, parser=mock_parser)
    
    with patch("tempfile.TemporaryDirectory") as mock_tmp:
        mock_tmp.return_value.__enter__.return_value = str(tmp_path / "mock_tmp")
        (tmp_path / "mock_tmp" / "dev" / "s").mkdir(parents=True)
        (tmp_path / "mock_tmp" / "dev" / "s" / "SKILL.md").write_text("content", encoding="utf-8")
        
        use_case.execute(PublishPackRequest(pack_path=pack_path))
        
        args, kwargs = mock_publisher.publish.call_args
        assert kwargs["metadata"].description == "description from SKILL.md"

def test_install_from_url_sha256_mismatch_error(tmp_path: Path) -> None:
    from skill_forge.application.use_cases.publish_skill import InstallFromUrl, InstallFromUrlRequest
    
    mock_fetcher = MagicMock()
    mock_unpacker = MagicMock()
    mock_installer = MagicMock()
    
    # Mock fetcher to write an empty file (SHA256: e3b0c4...)
    def _fetch(url, path):
        Path(path).write_bytes(b"")
    mock_fetcher.fetch.side_effect = _fetch
    
    use_case = InstallFromUrl(fetcher=mock_fetcher, unpacker=mock_unpacker, installer=mock_installer)
    
    request = InstallFromUrlRequest(
        url="https://example.com/pack.skillpack",
        expected_sha256="wrong-sha"
    )
    
    with pytest.raises(ValueError) as exc:
        use_case.execute(request)
    
    assert "sha256 mismatch" in str(exc.value)
    assert "expected wrong-sha" in str(exc.value)
