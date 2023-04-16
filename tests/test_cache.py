import os
from pathlib import Path
from tempfile import TemporaryDirectory, mkstemp

from bygg.cache import Cache, InputsOutputsDigests


def test_cache_load_non_existing():
    fd, path = mkstemp()
    os.close(fd)
    os.unlink(path)

    cache = Cache(Path(path))
    cache.load()
    assert cache.data is not None
    assert cache.data.digests == {}


def test_cache_load_empty():
    fd, path = mkstemp()
    print(path)
    cache = Cache(Path(path))
    cache.load()
    assert cache.data is not None
    assert cache.data.digests == {}
    os.close(fd)
    os.unlink(path)


def test_cache_write_and_load():
    with TemporaryDirectory() as d:
        cache = Cache(Path(d) / "cache.db")
        cache.load()
        assert cache.data is not None
        assert cache.data.digests == {}

        cache.data.digests["foo"] = InputsOutputsDigests("deadbeef", "f00", "f33d")
        cache.save()

        cache2 = Cache(Path(d) / "cache.db")
        cache2.load()
        assert cache2.data is not None
        assert cache2.data.digests == {
            "foo": InputsOutputsDigests("deadbeef", "f00", "f33d")
        }
