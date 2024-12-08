import os
from pathlib import Path
import time

import pytest

from bygg.core.digest import (
    calculate_dependency_digest,
    calculate_file_digest,
    file_digest_memo,
)

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


# Time to sleep after modifying file content that is different but has the same size.
# Simulates that it's unlikely that different content with the same size is written at
# the same time as the previous content that we digested.
SETTLE_TIME = 1 / 1e2


def test_file_digest_memo(tmp_path, mocker):
    import bygg.core.digest

    digest_spy = mocker.spy(bygg.core.digest, "file_digest")

    file = tmp_path / "file"
    filename = str(file)

    # Initial run, should give cache miss.
    expected_digest_calls = 1
    file.write_text(f"content for {filename}")
    st = os.stat(filename)
    digest1 = file_digest_memo(filename, st.st_ctime_ns, st.st_mtime_ns, st.st_size)

    assert digest1
    assert digest_spy.call_count == expected_digest_calls

    # No content or stat change. Should give cache hit.
    digest2 = file_digest_memo(filename, st.st_ctime_ns, st.st_mtime_ns, st.st_size)

    assert digest2 == digest1
    assert digest_spy.call_count == expected_digest_calls

    # Write the same content again. Should give cache miss.
    expected_digest_calls += 1
    time.sleep(SETTLE_TIME)
    file.write_text(f"content for {filename}")
    st = os.stat(filename)
    digest3 = file_digest_memo(filename, st.st_ctime_ns, st.st_mtime_ns, st.st_size)

    assert digest3 == digest1
    assert digest_spy.call_count == expected_digest_calls

    # Again, no content or stat change. Should give cache hit.
    digest4 = file_digest_memo(filename, st.st_ctime_ns, st.st_mtime_ns, st.st_size)

    assert digest4 == digest1
    assert digest_spy.call_count == expected_digest_calls

    # Write new content but with same size. Should give cache miss.
    expected_digest_calls += 1
    time.sleep(SETTLE_TIME)
    file.write_text(f"content_for_{filename}")
    st = os.stat(filename)
    digest5 = file_digest_memo(filename, st.st_ctime_ns, st.st_mtime_ns, st.st_size)

    assert digest5 != digest1
    assert digest_spy.call_count == expected_digest_calls

    # Write new content with different size. Should give cache miss.
    expected_digest_calls += 1
    file.write_text(f"more content for {filename}")
    st = os.stat(filename)
    digest6 = file_digest_memo(filename, st.st_ctime_ns, st.st_mtime_ns, st.st_size)

    assert digest6 != digest1
    assert digest_spy.call_count == expected_digest_calls

    # Again, no content or stat change. Should give cache hit.
    digest7 = file_digest_memo(filename, st.st_ctime_ns, st.st_mtime_ns, st.st_size)

    assert digest7 == digest6
    assert digest_spy.call_count == expected_digest_calls

    # No content or stat change. Should give cache hit.
    digest8 = file_digest_memo(filename, st.st_ctime_ns, st.st_mtime_ns, st.st_size)

    assert digest8 == digest6
    assert digest_spy.call_count == expected_digest_calls


def test_calculate_dependency_digest(tmp_path: Path, mocker):
    file = tmp_path / "file"
    filename = str(file)
    file_set = set([filename])

    # Initial run
    file.write_text(f"content for {filename}")
    digests1, was_missing1 = calculate_dependency_digest(file_set)

    assert digests1
    assert not was_missing1

    # No content change
    time.sleep(SETTLE_TIME)
    file.write_text(f"content for {filename}")
    digests2, was_missing2 = calculate_dependency_digest(file_set)

    assert digests2 == digests1
    assert not was_missing2

    # Content change but no size change
    time.sleep(SETTLE_TIME)
    file.write_text(f"content_for_{filename}")
    digests3, was_missing3 = calculate_dependency_digest(file_set)

    assert digests3 != digests1
    assert not was_missing3

    # Content change with size change
    file.write_text(f"more content for {filename}")
    digests4, was_missing4 = calculate_dependency_digest(file_set)

    assert digests4 != digests3
    assert not was_missing4


def test_file_digest_memo_symlinks(tmp_path, mocker):
    import bygg.core.digest

    digest_spy = mocker.spy(bygg.core.digest, "file_digest")

    file = tmp_path / "real.txt"
    file.write_text(f"real file content for {str(file)}")

    link = tmp_path / "link.txt"
    os.symlink(file, link)

    st = os.stat(str(link))
    digest1 = file_digest_memo(str(file), st.st_ctime_ns, st.st_mtime_ns, st.st_size)
    digest2 = file_digest_memo(str(link), st.st_ctime_ns, st.st_mtime_ns, st.st_size)

    assert digest1 == digest2
    assert digest_spy.call_count == 2


def test_calculate_dependency_digest_symlinks(tmp_path: Path, mocker):
    import bygg.core.digest

    digest_spy = mocker.spy(bygg.core.digest, "file_digest")

    file = tmp_path / "file"
    file.write_text(f"content for {str(file)}")

    link = tmp_path / "link"
    link.symlink_to(file)

    digests1, was_missing1 = calculate_dependency_digest(set([str(link)]))

    assert digests1
    assert not was_missing1
    assert digest_spy.call_count == 1

    file.write_text(f"different content for {str(file)}")

    digests2, was_missing2 = calculate_dependency_digest(set([str(link)]))

    assert digests1 != digests2
    assert not was_missing2
    assert digest_spy.call_count == 2
