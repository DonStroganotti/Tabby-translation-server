# this is a bad solution, looping all files all the time
# but watchdog was giving me issues where it triggered the on_modified even 3 times every time a file changed
import signal
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from globals import *
from functions import *


def monitor_files(file_paths, callback):
    previous_modify_time = {file: os.path.getmtime(file) for file in file_paths}
    run = True

    def signal_handler(signal, frame):
        nonlocal run
        run = False

    # Register the signal handler
    signal.signal(signal.SIGINT, signal_handler)

    while run:
        for file in file_paths:
            m_time = os.path.getmtime(file)
            if m_time != previous_modify_time.get(file):
                callback(file)
                previous_modify_time[file] = m_time
        time.sleep(0.5)


def get_files_in_repositories(repositories):
    file_paths = []
    for repository_info in repositories:
        if repository_info["monitor"] == True:
            for language in Language:
                # language_name = language["name"]
                language_ext = language["ext"]
                path = repository_info["path"]
                recursive = repository_info["recursive_search"]
                files = get_files_from_directory(path, language_ext, recursive)
                file_paths += files


class FileEventHandler(FileSystemEventHandler):
    def __init__(self, modified_callback, created_callback, deleted_callback) -> None:
        self.last_change = {}
        self.last_change_type = {}
        self.modified_callback = modified_callback
        self.created_callback = created_callback
        self.deleted_callback = deleted_callback

    def get_last_change(self, path, _type):
        # check if key exists in object
        if not self.last_change.get(path):
            # add initial element in self.last_change
            self.last_change[path] = 0
            self.last_change_type[path] = ""

        return self.last_change[path], self.last_change_type[path]

    def update_last_change(self, path, _type):
        self.last_change[path] = time.time()
        self.last_change_type[path] = _type

    def on_modified(self, event):
        if not event.is_directory:
            path = event.src_path
            last_change, last_type = self.get_last_change(path, "modified")
            # trigger event maximum every 0.1 seconds
            if (time.time() - last_change) > 0.1 or last_type != "modified":
                self.update_last_change(path, "modified")
                self.modified_callback(path)

    def on_created(self, event):
        if not event.is_directory:
            path = event.src_path
            last_change, last_type = self.get_last_change(path, "created")
            # trigger event maximum every 0.1 seconds
            if (time.time() - last_change) > 0.1 or last_type != "created":
                self.update_last_change(path, "created")
                self.created_callback(path)

    def on_deleted(self, event):
        if not event.is_directory:
            path = event.src_path
            last_change, last_type = self.get_last_change(path, "deleted")
            # trigger event maximum every 0.1 seconds
            if (time.time() - last_change) > 0.1 or last_type != "deleted":
                self.update_last_change(path, "deleted")
                self.deleted_callback(path)


def WatchRepositories(
    repositories, modified_callback, created_callback, deleted_callback
):
    event_handler = FileEventHandler(
        modified_callback, created_callback, deleted_callback
    )
    observer = Observer()

    for repo in repositories:
        path = repo["path"]
        recursive = repo["recursive_search"]
        observer.schedule(event_handler, path, recursive=recursive)

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()
