import os
import time

from watchdog.events import DirModifiedEvent, FileModifiedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from bygg.logutils import logger


class FileEventHandler(FileSystemEventHandler):
    def __init__(self, paths: set[str]):
        self.paths = paths
        self.has_matching_path = False

    def should_keep_running(self) -> bool:
        return True

    def on_modified(self, event: DirModifiedEvent | FileModifiedEvent):
        filename = os.path.realpath(event.src_path)
        if filename in self.paths:
            logger.debug("Modified event: %s", filename)
            self.has_matching_path = True


def do_watch(files_to_watch: set[str]):
    normalised_paths = set(os.path.realpath(path) for path in files_to_watch)
    logger.debug("Watching for file changes in: %s", normalised_paths)

    event_handler = FileEventHandler(normalised_paths)
    observer = Observer()
    observer.schedule(event_handler, ".", recursive=True)
    observer.start()

    try:
        while not event_handler.has_matching_path:
            time.sleep(1)
    finally:
        logger.debug("Stopping watcher")
        observer.stop()
        observer.join()
