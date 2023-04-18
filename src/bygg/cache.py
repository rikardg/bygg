from dataclasses import dataclass
from pathlib import Path
import pickle

from bygg.scaffolding import STATUS_DIR, make_sure_status_dir_exists

DEFAULT_DB_FILE = STATUS_DIR / "cache.db"


@dataclass
class InputsOutputsDigests:
    inputs_digest: str
    outputs_digest: str
    dynamic_digest: str | None


@dataclass
class CacheState:
    digests: dict[str, InputsOutputsDigests]


class Cache:
    data: CacheState | None
    db_file: Path

    def __init__(self, db_file: Path = DEFAULT_DB_FILE):
        self.data = CacheState({})
        self.db_file = db_file

    def load(self):
        make_sure_status_dir_exists()
        try:
            with open(self.db_file, "rb") as f:
                self.data = pickle.load(f)
        except (EOFError, FileNotFoundError):
            self.data = CacheState({})

    def save(self):
        if not self.data:
            return
        with open(self.db_file, "wb") as f:
            pickle.dump(self.data, f)
        # print(f"Cache: {self.data.digests}")

    def get_digests(self, name: str) -> InputsOutputsDigests | None:
        if not self.data:
            return None
        return self.data.digests.get(name, None)

    def set_digests(
        self,
        name: str,
        inputs_digest: str,
        outputs_digest: str,
        dynamic_digest: str | None = None,
    ):
        if not self.data:
            return
        self.data.digests[name] = InputsOutputsDigests(
            inputs_digest, outputs_digest, dynamic_digest
        )

    def remove_digests(self, name: str):
        if not self.data:
            return
        self.data.digests.pop(name, None)
