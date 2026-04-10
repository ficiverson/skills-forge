"""Tests for the PublishPack and InstallFromUrl use cases."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pytest

from skill_forge.application.use_cases.pack_skill import UnpackSkill
from skill_forge.application.use_cases.publish_skill import (
    InstallFromUrl,
    InstallFromUrlRequest,
    PublishPack,
    PublishPackRequest,
)
from skill_forge.domain.model import (
    Owner,
    PublishMetadata,
    PublishResult,
    RegistryIndex,
    SkillPackManifest,
    SkillRef,
    SkillScope,
)
from skill_forge.domain.ports import (
    PackFetcher,
    PackPublisher,
    SkillInstaller,
    SkillPacker,
)

_EMPTY_META = PublishMetadata()


def _manifest() -> SkillPackManifest:
    return SkillPackManifest(
        name="python-tdd",
        version="0.2.0",
        author="",
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        skills=(SkillRef(category="dev", name="python-tdd", version="0.2.0"),),
    )


# ----------------------------------------------------------- stub adapters


class _StubPacker(SkillPacker):
    def pack(self, skill_dirs, manifest, output_path):  # type: ignore[no-untyped-def]
        raise NotImplementedError

    def unpack(self, pack_path, dest_dir):  # type: ignore[no-untyped-def]
        manifest = _manifest()
        for ref in manifest.skills:
            target = dest_dir / ref.category / ref.name
            target.mkdir(parents=True, exist_ok=True)
            (target / "SKILL.md").write_text("---\nname: x\n---\nbody")
        return manifest

    def read_manifest(self, pack_path):  # type: ignore[no-untyped-def]
        return _manifest()


class _StubPublisher(PackPublisher):
    def __init__(self) -> None:
        self.calls: list[tuple[Path, str, bool, PublishMetadata]] = []

    def publish(self, pack_path, manifest, message, push, metadata=_EMPTY_META):  # type: ignore[no-untyped-def]
        self.calls.append((pack_path, message, push, metadata))
        return PublishResult(
            pack_name=manifest.name,
            version=manifest.skills[0].version,
            raw_url=f"https://example.com/packs/dev/{manifest.name}-{manifest.skills[0].version}.skillpack",
            repo_relative_path=f"packs/dev/{manifest.name}-{manifest.skills[0].version}.skillpack",
            sha256="a" * 64,
            committed=True,
            pushed=push,
        )

    def read_index(self):  # type: ignore[no-untyped-def]
        return RegistryIndex(
            registry_name="r",
            base_url="https://example.com",
            updated_at="",
            skills=(),
        )


class _StubFetcher(PackFetcher):
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def fetch(self, url, dest):  # type: ignore[no-untyped-def]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(self._payload)
        return dest

    def fetch_index(self, url):  # type: ignore[no-untyped-def]
        raise NotImplementedError


class _StubInstaller(SkillInstaller):
    def __init__(self) -> None:
        self.installed: list[Path] = []

    def install(self, skill_path, scope, target=None):  # type: ignore[no-untyped-def]
        self.installed.append(skill_path)
        return [Path(f"/fake/install/{skill_path.name}")]

    def uninstall(self, skill_name, scope, target=None):  # type: ignore[no-untyped-def]
        return []

    def is_installed(self, skill_name, scope):  # type: ignore[no-untyped-def]
        return False

    def list_installed(self, scope):  # type: ignore[no-untyped-def]
        return []


def _rich_manifest(**overrides: object) -> SkillPackManifest:
    """A manifest that satisfies all required-metadata validation rules."""
    base = _manifest()
    kwargs: dict[str, object] = dict(
        name=base.name,
        version=base.version,
        author=base.author,
        created_at=base.created_at,
        skills=base.skills,
        description="A TDD skill for Python projects",
        tags=("tdd", "python"),
        owner=Owner(name="Test Author", email="author@test.example"),
    )
    kwargs.update(overrides)
    return SkillPackManifest(**kwargs)  # type: ignore[arg-type]


class _RichStubPacker(_StubPacker):
    """Packer whose manifest already satisfies all required-metadata rules."""

    def read_manifest(self, pack_path: Path) -> SkillPackManifest:  # type: ignore[override]
        return _rich_manifest()


# --------------------------------------------------------------------- tests


class TestPublishPack:
    def test_publishes_existing_pack(self, tmp_path: Path) -> None:
        pack = tmp_path / "x.skillpack"
        pack.write_bytes(b"zip-content")
        publisher = _StubPublisher()
        use_case = PublishPack(publisher=publisher, packer=_RichStubPacker())

        response = use_case.execute(
            PublishPackRequest(pack_path=pack, message="ship", push=False)
        )

        assert response.result.pack_name == "python-tdd"
        assert response.result.version == "0.2.0"
        assert response.result.committed is True
        assert len(publisher.calls) == 1
        recorded_pack, recorded_msg, recorded_push, recorded_meta = publisher.calls[0]
        assert recorded_pack == pack
        assert recorded_msg == "ship"
        assert recorded_push is False
        assert isinstance(recorded_meta, PublishMetadata)

    def test_defaults_metadata_from_manifest(self, tmp_path: Path) -> None:
        """When the request omits flags, the publisher gets manifest values."""
        pack = tmp_path / "x.skillpack"
        pack.write_bytes(b"zip-content")
        publisher = _StubPublisher()

        class _RichPacker(_StubPacker):
            def read_manifest(self, pack_path):  # type: ignore[no-untyped-def]
                base = _manifest()
                return SkillPackManifest(
                    name=base.name,
                    version=base.version,
                    author=base.author,
                    created_at=base.created_at,
                    skills=base.skills,
                    description="from-manifest",
                    tags=("tdd",),
                    owner=Owner(name="ManifestOwner", email="m@x.test"),
                    deprecated=True,
                )

        use_case = PublishPack(publisher=publisher, packer=_RichPacker())
        use_case.execute(PublishPackRequest(pack_path=pack))

        meta = publisher.calls[0][3]
        assert meta.description == "from-manifest"
        assert meta.tags == ("tdd",)
        assert meta.owner is not None and meta.owner.name == "ManifestOwner"
        assert meta.deprecated is True

    def test_request_overrides_manifest_metadata(self, tmp_path: Path) -> None:
        pack = tmp_path / "x.skillpack"
        pack.write_bytes(b"zip-content")
        publisher = _StubPublisher()

        class _RichPacker(_StubPacker):
            def read_manifest(self, pack_path):  # type: ignore[no-untyped-def]
                base = _manifest()
                return SkillPackManifest(
                    name=base.name,
                    version=base.version,
                    author=base.author,
                    created_at=base.created_at,
                    skills=base.skills,
                    description="from-manifest",
                    tags=("manifest-tag",),
                    owner=Owner(name="ManifestOwner"),
                )

        use_case = PublishPack(publisher=publisher, packer=_RichPacker())
        use_case.execute(
            PublishPackRequest(
                pack_path=pack,
                tags=("override-tag",),
                owner_name="CliOwner",
                owner_email="cli@x.test",
            )
        )

        meta = publisher.calls[0][3]
        assert meta.tags == ("override-tag",)
        assert meta.owner is not None
        assert meta.owner.name == "CliOwner"
        assert meta.owner.email == "cli@x.test"

    def test_threads_metadata_into_publisher(self, tmp_path: Path) -> None:
        pack = tmp_path / "x.skillpack"
        pack.write_bytes(b"zip-content")
        publisher = _StubPublisher()
        use_case = PublishPack(publisher=publisher, packer=_RichStubPacker())

        use_case.execute(
            PublishPackRequest(
                pack_path=pack,
                tags=("tdd", "python"),
                owner_name="Acme",
                owner_email="team@acme.test",
                deprecated=False,
                release_notes="initial cut",
            )
        )

        meta = publisher.calls[0][3]
        assert meta.tags == ("tdd", "python")
        assert meta.owner is not None
        assert meta.owner.name == "Acme"
        assert meta.owner.email == "team@acme.test"
        assert meta.release_notes == "initial cut"
        assert meta.deprecated is False

    def test_missing_pack_errors(self, tmp_path: Path) -> None:
        use_case = PublishPack(publisher=_StubPublisher(), packer=_StubPacker())
        with pytest.raises(FileNotFoundError):
            use_case.execute(
                PublishPackRequest(pack_path=tmp_path / "missing.skillpack")
            )

    # ------------------------------------------------------------------ validation

    def test_missing_description_raises(self, tmp_path: Path) -> None:
        """Publish without a description must fail with a clear error."""
        pack = tmp_path / "x.skillpack"
        pack.write_bytes(b"zip-content")

        class _NoDesc(_StubPacker):
            def read_manifest(self, pack_path):  # type: ignore[no-untyped-def]
                return _rich_manifest(description="")

        use_case = PublishPack(publisher=_StubPublisher(), packer=_NoDesc())
        with pytest.raises(ValueError, match="description is required"):
            use_case.execute(PublishPackRequest(pack_path=pack))

    def test_missing_tags_raises(self, tmp_path: Path) -> None:
        """Publish with an empty tags tuple must fail with a clear error."""
        pack = tmp_path / "x.skillpack"
        pack.write_bytes(b"zip-content")

        class _NoTags(_StubPacker):
            def read_manifest(self, pack_path):  # type: ignore[no-untyped-def]
                return _rich_manifest(tags=())

        use_case = PublishPack(publisher=_StubPublisher(), packer=_NoTags())
        with pytest.raises(ValueError, match="at least one tag is required"):
            use_case.execute(PublishPackRequest(pack_path=pack))

    def test_missing_owner_raises(self, tmp_path: Path) -> None:
        """Publish without any owner must fail with a clear error."""
        pack = tmp_path / "x.skillpack"
        pack.write_bytes(b"zip-content")

        class _NoOwner(_StubPacker):
            def read_manifest(self, pack_path):  # type: ignore[no-untyped-def]
                return _rich_manifest(owner=None)

        use_case = PublishPack(publisher=_StubPublisher(), packer=_NoOwner())
        with pytest.raises(ValueError, match="owner name and email are required"):
            use_case.execute(PublishPackRequest(pack_path=pack))

    def test_missing_owner_email_raises(self, tmp_path: Path) -> None:
        """Owner without an email address must fail validation."""
        pack = tmp_path / "x.skillpack"
        pack.write_bytes(b"zip-content")

        class _NoEmail(_StubPacker):
            def read_manifest(self, pack_path):  # type: ignore[no-untyped-def]
                return _rich_manifest(owner=Owner(name="Nameless", email=""))

        use_case = PublishPack(publisher=_StubPublisher(), packer=_NoEmail())
        with pytest.raises(ValueError, match="owner name and email are required"):
            use_case.execute(PublishPackRequest(pack_path=pack))

    def test_multiple_missing_fields_reported_together(self, tmp_path: Path) -> None:
        """All missing fields are listed in a single ValueError."""
        pack = tmp_path / "x.skillpack"
        pack.write_bytes(b"zip-content")
        # _StubPacker returns a bare manifest with no description / tags / owner
        use_case = PublishPack(publisher=_StubPublisher(), packer=_StubPacker())
        with pytest.raises(ValueError) as exc_info:
            use_case.execute(PublishPackRequest(pack_path=pack))
        message = str(exc_info.value)
        assert "description is required" in message
        assert "at least one tag is required" in message
        assert "owner name and email are required" in message

    def test_cli_override_satisfies_validation(self, tmp_path: Path) -> None:
        """Passing --owner-name/--owner-email at publish time satisfies validation
        even when the manifest has no owner — description and tags must still be
        present in the manifest."""
        pack = tmp_path / "x.skillpack"
        pack.write_bytes(b"zip-content")

        class _NoOwnerPacker(_StubPacker):
            def read_manifest(self, pack_path):  # type: ignore[no-untyped-def]
                return _rich_manifest(owner=None)

        publisher = _StubPublisher()
        use_case = PublishPack(publisher=publisher, packer=_NoOwnerPacker())
        use_case.execute(
            PublishPackRequest(
                pack_path=pack,
                owner_name="CLI Author",
                owner_email="cli@test.example",
            )
        )
        meta = publisher.calls[0][3]
        assert meta.owner is not None
        assert meta.owner.name == "CLI Author"


class TestInstallFromUrl:
    def test_fetches_unpacks_and_installs(self, tmp_path: Path) -> None:
        payload = b"fake-pack-bytes"
        fetcher = _StubFetcher(payload)
        installer = _StubInstaller()
        use_case = InstallFromUrl(
            fetcher=fetcher,
            unpacker=UnpackSkill(packer=_StubPacker()),
            installer=installer,
        )

        response = use_case.execute(
            InstallFromUrlRequest(
                url="https://example.com/x.skillpack",
                dest_dir=tmp_path / "out",
                scope=SkillScope.GLOBAL,
            )
        )

        assert response.manifest.name == "python-tdd"
        assert len(response.extracted_paths) == 1
        assert len(installer.installed) == 1
        assert response.sha256 == hashlib.sha256(payload).hexdigest()

    def test_rejects_sha256_mismatch(self, tmp_path: Path) -> None:
        fetcher = _StubFetcher(b"some-bytes")
        use_case = InstallFromUrl(
            fetcher=fetcher,
            unpacker=UnpackSkill(packer=_StubPacker()),
            installer=_StubInstaller(),
        )
        with pytest.raises(ValueError, match="sha256 mismatch"):
            use_case.execute(
                InstallFromUrlRequest(
                    url="https://example.com/x.skillpack",
                    dest_dir=tmp_path / "out",
                    expected_sha256="b" * 64,
                )
            )

    def test_install_false_skips_installation(self, tmp_path: Path) -> None:
        installer = _StubInstaller()
        use_case = InstallFromUrl(
            fetcher=_StubFetcher(b"x"),
            unpacker=UnpackSkill(packer=_StubPacker()),
            installer=installer,
        )
        response = use_case.execute(
            InstallFromUrlRequest(
                url="https://example.com/x.skillpack",
                dest_dir=tmp_path / "out",
                install=False,
            )
        )
        assert response.installed_paths == []
        assert installer.installed == []
