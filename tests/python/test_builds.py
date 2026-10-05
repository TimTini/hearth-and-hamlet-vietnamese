import json
from pathlib import Path

import pytest

from hnh_vi.builds import BuildSpec, load_build_specs, sha256_file, verify_game_dir

EXE_SHA256 = "CA978112CA1BBDCAFAC231B39A23DC4DA786EFF8147C4E72B9807785AFEE48BB"
PCK_SHA256 = "3E23E8160039594A33894F6564E1B1348BBD7A0088D42C4ACB73EEAED59C009D"


@pytest.fixture
def spec() -> BuildSpec:
    return BuildSpec(
        build_id="25600292",
        exe_version="1.1.0.0",
        confirmed_on="2026-10-05",
        exe_name="Hearth and Hamlet.exe",
        exe_sha256=EXE_SHA256,
        pck_name="Hearth and Hamlet.pck",
        pck_sha256=PCK_SHA256,
    )


def write_game_fixture(game_dir: Path) -> None:
    game_dir.mkdir()
    (game_dir / "Hearth and Hamlet.exe").write_bytes(b"a")
    (game_dir / "Hearth and Hamlet.pck").write_bytes(b"b")


def test_loads_supported_build_25600292() -> None:
    manifest = Path(__file__).resolve().parents[2] / "manifests/game-builds.json"
    specs = load_build_specs(manifest)

    assert isinstance(specs, tuple)
    assert specs == (
        BuildSpec(
            build_id="25600292",
            exe_version="1.1.0.0",
            confirmed_on="2026-10-05",
            exe_name="Hearth and Hamlet.exe",
            exe_sha256="7D37BBF3BD6AB823F2659CE410FE792EFF2A51D1280FC211E3175C2D412F9A2A",
            pck_name="Hearth and Hamlet.pck",
            pck_sha256="7D5A2113B5D63B40605413A70B707DC7F56AFC7DE02BCE34760E227BFE6E0201",
        ),
    )


def test_verifies_matching_fixture_hashes(tmp_path: Path, spec: BuildSpec) -> None:
    game_dir = tmp_path / "game"
    write_game_fixture(game_dir)
    appmanifest = tmp_path / "appmanifest_4315040.acf"
    appmanifest.write_text(
        '"AppState"\n{\n\t"appid" "4315040"\n\t"buildid" "25600292"\n}\n',
        encoding="utf-8",
    )

    result = verify_game_dir(game_dir, spec, appmanifest)

    assert result.ok
    assert result.issues == ()


def test_rejects_hash_mismatch_without_mutation(
    tmp_path: Path, spec: BuildSpec, capsys: pytest.CaptureFixture[str]
) -> None:
    game_dir = tmp_path / "game"
    write_game_fixture(game_dir)
    (game_dir / spec.pck_name).write_bytes(b"modified synthetic fixture")
    before = {path.name: path.read_bytes() for path in game_dir.iterdir()}

    result = verify_game_dir(game_dir, spec)

    assert not result.ok
    assert result.issues == ("hash_mismatch",)
    assert {path.name: path.read_bytes() for path in game_dir.iterdir()} == before
    assert capsys.readouterr() == ("", "")


def test_rejects_missing_files(tmp_path: Path, spec: BuildSpec) -> None:
    result = verify_game_dir(tmp_path / "missing game", spec)

    assert not result.ok
    assert result.issues == ("missing_file", "missing_file")
    assert list(tmp_path.iterdir()) == []


def test_accepts_game_path_with_spaces_and_unicode(
    tmp_path: Path, spec: BuildSpec
) -> None:
    game_dir = tmp_path / "Trò chơi Hearth and Hamlet"
    write_game_fixture(game_dir)

    result = verify_game_dir(game_dir, spec)

    assert result.ok
    assert result.issues == ()


@pytest.mark.parametrize("build_id", ["25600291", "", "not-a-build"])
def test_rejects_steam_build_mismatch(
    tmp_path: Path, spec: BuildSpec, build_id: str
) -> None:
    game_dir = tmp_path / "game"
    write_game_fixture(game_dir)
    appmanifest = tmp_path / "appmanifest.acf"
    appmanifest.write_text(
        f'"AppState"\n{{\n"buildid" "{build_id}"\n}}\n', encoding="utf-8"
    )

    result = verify_game_dir(game_dir, spec, appmanifest)

    assert not result.ok
    assert result.issues == ("steam_build_mismatch",)


def test_preserves_issue_order(tmp_path: Path, spec: BuildSpec) -> None:
    (tmp_path / spec.pck_name).write_bytes(b"changed")
    appmanifest = tmp_path / "appmanifest.acf"
    appmanifest.write_text('"buildid" "old"\n', encoding="utf-8")

    result = verify_game_dir(tmp_path, spec, appmanifest)

    assert not result.ok
    assert result.issues == ("missing_file", "hash_mismatch", "steam_build_mismatch")


def test_rejects_missing_appmanifest(tmp_path: Path, spec: BuildSpec) -> None:
    game_dir = tmp_path / "game"
    write_game_fixture(game_dir)

    result = verify_game_dir(game_dir, spec, tmp_path / "missing.acf")

    assert not result.ok
    assert result.issues == ("missing_file",)


def test_sha256_file_matches_known_digest(tmp_path: Path) -> None:
    path = tmp_path / "synthetic.bin"
    path.write_bytes(b"abc")

    assert sha256_file(path) == (
        "BA7816BF8F01CFEA414140DE5DAE2223B00361A396177A9CB410FF61F20015AD"
    )


@pytest.mark.parametrize("file_name", ["../outside.exe", "C:/outside.exe", "a/b.exe"])
def test_rejects_manifest_paths_outside_game_dir(
    tmp_path: Path, file_name: str
) -> None:
    manifest = tmp_path / "builds.json"
    manifest.write_text(
        json.dumps(
            {
                "builds": [
                    {
                        "build_id": "25600292",
                        "exe_version": "1.1.0.0",
                        "confirmed_on": "2026-10-05",
                        "exe_name": file_name,
                        "exe_sha256": EXE_SHA256,
                        "pck_name": "Hearth and Hamlet.pck",
                        "pck_sha256": PCK_SHA256,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        load_build_specs(manifest)
