import dis
import functools
import hashlib
import io
import os
from typing import Callable

DIGEST_TYPE = "sha1"

# If True, cache the file digest in memory based on the filename, stat.ctime_ns,
# stat.mtime_ns and stat.size of the file.
ALLOW_DIGEST_CACHING = True


def file_digest(file: str) -> str:
    with open(file, "rb") as f:
        return hashlib.file_digest(f, DIGEST_TYPE).hexdigest()


@functools.cache
def file_digest_memo(
    file: str, st_ctime_ns: int, st_mtime_ns: int, st_size: int
) -> str:
    """
    Cache a file's digest based on the content, stat.ctime_ns, stat.mtime_ns and
    stat.size of the file.
    """
    return file_digest(file)


def calculate_file_digest(file: str) -> str | None:
    """
    Calculate the digest of a file.

    file: The file to calculate the digest of.
    Returns: The digest of the file as a hex string, or None if the file does not exist.

    """
    real_path = os.path.realpath(file)
    if os.path.isfile(real_path):
        if ALLOW_DIGEST_CACHING:
            st = os.stat(real_path)
            return file_digest_memo(
                real_path, st.st_ctime_ns, st.st_mtime_ns, st.st_size
            )
        return file_digest(real_path)


def calculate_dependency_digest(filenames: set[str]) -> tuple[str, bool]:
    """
    Calculate the digest of a set of files.
    filenames: The files to calculate the digest of.
    Returns: The digest of the files as a hex string.
    """

    file_digests = [calculate_file_digest(filename) for filename in filenames]
    digests = sorted(filter(None, file_digests))
    files_were_missing = len(file_digests) != len(digests)

    return (
        hashlib.new(DIGEST_TYPE, "".join(digests).encode()).hexdigest(),
        files_were_missing,
    )


def calculate_digest(items: list[str]) -> str:
    digests = sorted(
        filter(
            None,
            [hashlib.new(DIGEST_TYPE, item.encode()).hexdigest() for item in items],
        )
    )

    return hashlib.new(DIGEST_TYPE, "".join(digests).encode()).hexdigest()


def calculate_function_digest(fn: Callable) -> str:
    """
    Calculate the digest of a function.
    fn: The function to calculate the digest of.
    Returns: The digest of the function as a hex string.
    """
    # Just looking at the code object is not enough, so let's disassemble it.
    out = io.StringIO()
    dis.dis(fn, file=out)
    function_dis_string = out.getvalue()
    return hashlib.new(DIGEST_TYPE, function_dis_string.encode()).hexdigest()


def calculate_string_digest(s: str) -> str:
    """
    Calculate the digest of a string.
    s: The string to calculate the digest of.
    Returns: The digest of the string as a hex string.
    """
    return hashlib.new(DIGEST_TYPE, s.encode()).hexdigest()
