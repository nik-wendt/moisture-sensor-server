import subprocess
import sys
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class RestartOnChange(FileSystemEventHandler):
    def __init__(self, command):
        self.command = command
        self.process = self.start_process()
        self.last_restart = time.time()

    def start_process(self):
        print(f"\n🚀 Starting: {' '.join(self.command)}")
        return subprocess.Popen(self.command)

    def restart_process(self):
        print("🔄 Restarting process...")
        self.process.terminate()
        self.process.wait()
        self.process = self.start_process()

    def handle_event(self, event):
        path = Path(event.src_path)

        if event.is_directory:
            return
        if path.suffix != ".py":
            return
        if "__pycache__" in path.parts or path.name.startswith("."):
            return

        now = time.time()
        if now - self.last_restart < 1:
            return  # debounce

        print(f"📦 File change detected: {path}")
        self.restart_process()
        self.last_restart = now

    def on_modified(self, event):
        self.handle_event(event)

    def on_created(self, event):
        self.handle_event(event)

    def stop(self):
        self.process.terminate()
        self.process.wait()


if __name__ == "__main__":
    command = f"/app/{sys.argv[1]}"
    if not command:
        print("Usage: python autoreload.py your_script.py [args...]")
        sys.exit(1)

    watch_path = "."
    event_handler = RestartOnChange(command)
    observer = Observer()
    observer.schedule(event_handler, path=watch_path, recursive=True)
    print(f"👀 Watching for changes in: {watch_path}/**/*.py")

    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("🛑 Stopping...")
        observer.stop()
        event_handler.stop()

    observer.join()
