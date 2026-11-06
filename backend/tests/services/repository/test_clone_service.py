import stat

from app.services.repository.clone_service import remove_clone_directory


def test_remove_clone_directory_clears_readonly_git_pack_files(tmp_path) -> None:
    clone_path = tmp_path / "repository"
    pack_path = clone_path / ".git" / "objects" / "pack"
    pack_path.mkdir(parents=True)
    pack_file = pack_path / "pack.idx"
    pack_file.write_bytes(b"git pack index")
    pack_file.chmod(stat.S_IREAD)

    remove_clone_directory(clone_path)

    assert not clone_path.exists()
