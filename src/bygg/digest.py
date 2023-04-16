import dis
import functools
import hashlib
import io
import os
from typing import Callable, List, Set, Tuple

DIGEST_TYPE = "sha1"

# If True, cache the file digest in memory based on the content and stat.mtime_ns of the
# file.
ALLOW_DIGEST_CACHING = True


@functools.cache
def file_digest_memo(file: str, mtime: int) -> str | None:
    with open(file, "rb") as f:
        return hashlib.file_digest(f, DIGEST_TYPE).hexdigest()


def calculate_file_digest(file: str) -> str | None:
    """
    Calculate the digest of a file.

    file: The file to calculate the digest of.
    Returns: The digest of the file as a hex string, or None if the file does not exist.

    """
    if os.path.isfile(file):
        s = os.stat(file)
        with open(file, "rb") as f:
            if ALLOW_DIGEST_CACHING:
                return file_digest_memo(file, s.st_mtime_ns)
            return hashlib.file_digest(f, DIGEST_TYPE).hexdigest()


def calculate_dependency_digest(filenames: Set[str]) -> Tuple[str, bool]:
    """
    Calculate the digest of a set of files.
    filenames: The files to calculate the digest of.
    Returns: The digest of the files as a hex string.
    """

    files_were_missing = False

    digests = sorted(
        filter(None, [calculate_file_digest(filename) for filename in filenames])
    )

    # if len(digests) == 0:
    #     return ""

    return (
        hashlib.new(DIGEST_TYPE, "".join(digests).encode()).hexdigest(),
        files_were_missing,
    )


def calculate_digest(items: List[str]) -> str:
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
