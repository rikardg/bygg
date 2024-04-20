from bygg.core.digest import calculate_dependency_digest, calculate_file_digest
import pytest

pytestmark = pytest.mark.digest


def test_calculate_file_digest_existing(tmp_path):
    filenames = ["file1", "file2", "file3"]

    for filename in filenames:
        file = tmp_path / filename
        file.write_text(f"content for {filename}")

    digests1 = set(
        calculate_file_digest(str(tmp_path / filename)) for filename in filenames
    )
    assert all(digests1)

    digests2 = set(
        calculate_file_digest(str(tmp_path / filename)) for filename in filenames
    )

    assert digests1 == digests2


def test_calculate_file_digest_non_existing(tmp_path):
    filenames = ["file1", "file2", "file3"]

    digests1 = set(
        calculate_file_digest(str(tmp_path / filename)) for filename in filenames
    )
    assert map(lambda x: x is None, digests1)

    digests2 = set(
        calculate_file_digest(str(tmp_path / filename)) for filename in filenames
    )

    assert map(lambda x: x is None, digests2)


def test_calculate_dependency_digest_existing(tmp_path):
    files = set(tmp_path / filename for filename in ["file1", "file2", "file3"])

    for file in files:
        file.write_text(f"content for {str(file)}")

    digests1, was_missing1 = calculate_dependency_digest(
        set(str(file) for file in files)
    )

    assert digests1
    assert not was_missing1

    digests2, was_missing2 = calculate_dependency_digest(
        set(str(file) for file in files)
    )

    assert digests1 == digests2
    assert not was_missing2


def test_calculate_dependency_digest_non_existing(tmp_path):
    files = list(tmp_path / filename for filename in ["file1", "file2", "file3"])

    for file in files:
        file.write_text(f"content for {str(file)}")

    digests1, was_missing1 = calculate_dependency_digest(
        set(str(file) for file in files)
    )

    assert digests1
    assert not was_missing1

    filenames = set(str(file) for file in files)
    unlinked_file = files.pop()
    unlinked_file.unlink()

    digests2, was_missing2 = calculate_dependency_digest(filenames)

    assert len(digests2)
    assert digests2 != digests1
    assert was_missing2
