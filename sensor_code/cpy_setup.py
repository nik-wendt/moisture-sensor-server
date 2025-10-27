#!/usr/bin/env python3
import argparse
from requests import exceptions as reqexc
import glob
import os
import sys
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, quote

# Deps: pyserial, requests, watchdog
try:
    import serial
    from serial.serialutil import SerialException
except Exception:
    print("Missing dependency: pyserial  (pip install pyserial)", file=sys.stderr)
    sys.exit(1)

try:
    import requests
except Exception:
    print("Missing dependency: requests  (pip install requests)", file=sys.stderr)
    sys.exit(1)

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    HAVE_WATCHDOG = True
except Exception:
    HAVE_WATCHDOG = False


# ------------------------------ Utilities ------------------------------
def input_prompt(prompt: str, default: Optional[str] = None) -> str:
    s = input(prompt).strip()
    return s if s else (default or "")


def print_hr():
    print("-" * 60)


def encode_remote_path(rel: str) -> str:
    # URL-encode each segment but keep slashes
    parts = rel.replace("\\", "/").split("/")
    return "/".join(quote(p) for p in parts if p)


def is_excluded(path: Path) -> bool:
    p = str(path)
    return (
        any(seg in p for seg in ("/.git/", "/__pycache__/", "/.venv/"))
        or path.name == ".DS_Store"
    )


# ------------------------------ Serial: write settings.toml ------------------------------
PASTE_CTRL_E = b"\x05"
CTRL_C = b"\x03"
CTRL_D = b"\x04"
PROMPT = b">>> "


def wait_for_prompt(ser: serial.Serial, timeout: float = 5.0) -> bool:
    deadline = time.time() + timeout
    buf = b""
    while time.time() < deadline:
        buf += ser.read(ser.in_waiting or 1)
        if PROMPT in buf:
            return True
        time.sleep(0.02)
    return False


def write_settings_over_serial(
    port: str, ssid: str, wifi_pass: str, web_pass: str, instance: str
) -> None:
    try:
        with serial.Serial(port, 115200, timeout=0.1) as s:
            s.reset_input_buffer()
            s.write(b"\r" + CTRL_C)  # interrupt
            s.flush()
            wait_for_prompt(s, 1.0)

            # Enter paste mode
            s.reset_input_buffer()
            s.write(PASTE_CTRL_E)
            s.flush()
            time.sleep(0.05)

            contents = (
                f'CIRCUITPY_WIFI_SSID="{ssid}"\n'
                f'CIRCUITPY_WIFI_PASSWORD="{wifi_pass}"\n'
                f'CIRCUITPY_WEB_API_PASSWORD="{web_pass}"\n'
                f'CIRCUITPY_WEB_INSTANCE_NAME="{instance}"\n'
            )
            code = f"""
import os
with open("/settings.toml","w") as f:
    f.write({contents!r})
print("WROTE_SETTINGS_TOML")
"""
            s.write(code.encode("utf-8"))
            s.write(CTRL_D)  # finish paste
            s.flush()

            time.sleep(0.3)
            _ = s.read(4096)

            # Soft reboot: Ctrl-D at normal prompt
            s.write(b"\r" + CTRL_D)
            s.flush()
        print("✓ Wrote settings.toml and soft-rebooted.")
    except SerialException as e:
        msg = str(e).lower()
        if "resource busy" in msg or "errno 16" in msg:
            raise RuntimeError("SERIAL_BUSY") from e
        raise


def choose_port_menu(pattern: str = "/dev/tty.usb*") -> str:
    while True:
        ports = sorted(glob.glob(pattern))
        print(f"Detected serial ports (pattern: {pattern}):")
        if not ports:
            print("  (none found)")
            sel = input_prompt("Options: [r]etry listing  [q]uit  > ")
            if sel.lower() == "r":
                continue
            elif sel.lower() == "q":
                raise SystemExit("Re-plug the ESP device and run again.")
            else:
                print("Unknown choice.")
                continue
        else:
            for i, p in enumerate(ports):
                print(f"  [{i}] {p}")
            sel = input_prompt("Select index, or [r]etry listing, or [q]uit  > ")
            if sel.isdigit():
                idx = int(sel)
                if 0 <= idx < len(ports):
                    port = ports[idx]
                    print(f"Using {port}")
                    return port
                else:
                    print("Invalid index.")
            elif sel.lower() == "r":
                continue
            elif sel.lower() == "q":
                raise SystemExit(1)
            else:
                print("Invalid selection.")


# ------------------------------ Discovery via circuitpython.local ------------------------------
def detect_discovery_base(timeout: float = 3.0) -> Optional[str]:
    url = "http://circuitpython.local/cp/devices.json"
    try:
        with requests.Session() as sess:
            r = sess.get(url, timeout=timeout, allow_redirects=True)
            # Capture effective URL even if content is 401/etc.
            eff = r.url
            p = urlparse(eff)
            if p.scheme and p.netloc:
                return f"{p.scheme}://{p.netloc}"
    except requests.RequestException:
        pass
    return None


def list_devices_json(base: Optional[str], timeout: float = 3.0) -> dict:
    url = (
        base.rstrip("/") if base else "http://circuitpython.local"
    ) + "/cp/devices.json"
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {"total": 0, "devices": []}


def menu_pick_device(initial_base: Optional[str]) -> dict:
    base = initial_base
    while True:
        if not base:
            print("Discovery base unknown; trying circuitpython.local …")
        else:
            print(f"Discovery base: {base}")

        data = list_devices_json(base)
        total = int(data.get("total", 0) or 0)
        if total > 0 and isinstance(data.get("devices"), list):
            print(f"Found {total} device(s):")
            for i, d in enumerate(data["devices"]):
                print(
                    f"  [{i}] hostname={d.get('hostname', '?')}  instance={d.get('instance_name', '')}  ip={d.get('ip', '?')}  port={d.get('port', '?')}"
                )
            sel = input_prompt(
                "Select index, or [r]etry, or [d] re-detect base, or [q]uit  > "
            )
            if sel.isdigit():
                idx = int(sel)
                if 0 <= idx < total:
                    return data["devices"][idx]
                else:
                    print("Invalid index.")
            elif sel.lower() == "r":
                continue
            elif sel.lower() == "d":
                base = detect_discovery_base()
                continue
            elif sel.lower() == "q":
                raise SystemExit(1)
            else:
                print("Invalid selection.")
        else:
            print("No devices found.")
            sel = input_prompt("Options: [r]etry  [d] re-detect base  [q]uit  > ")
            if sel.lower() == "r":
                continue
            elif sel.lower() == "d":
                base = detect_discovery_base()
            elif sel.lower() == "q":
                raise SystemExit(1)
            else:
                print("Unknown choice.")


# ------------------------------ Web Workflow API ------------------------------


class WebWorkflow:
    def __init__(self, base_url: str, password: str):
        self.base = base_url.rstrip("/")
        self.fs = f"{self.base}/fs"
        self.auth = ("", password)
        self._new_session()

    def _new_session(self):
        # fresh session each time we want to reset connections
        self.sess = requests.Session()

    def probe(self) -> bool:
        try:
            r = self.sess.get(
                f"{self.fs}/",
                auth=self.auth,
                headers={"Accept": "application/json"},
                timeout=3,
            )
            r.raise_for_status()
            return True
        except Exception:
            return False

    # ---- robust HTTP helpers with backoff ----
    def _with_backoff(self, func, *, desc: str, max_wait: float = 60.0):
        start = time.time()
        delay = 0.5
        attempt = 1
        while True:
            try:
                return func()
            except (
                reqexc.ConnectionError,
                reqexc.Timeout,
                reqexc.ChunkedEncodingError,
            ) as e:
                elapsed = time.time() - start
                remaining = max_wait - elapsed
                if remaining <= 0:
                    print(
                        f"✗ {desc}: still failing after {int(max_wait)}s "
                        f"({e.__class__.__name__})"
                    )
                    # For debugging if needed: print(traceback.format_exc())
                    raise
                print(
                    f"  {desc}: attempt {attempt} failed "
                    f"({e.__class__.__name__}); retrying in {delay:.1f}s "
                    f"… [{int(remaining)}s left]  (Ctrl+C to cancel)"
                )
                try:
                    time.sleep(delay)
                except KeyboardInterrupt:
                    print("\nCanceled by user.")
                    raise
                # recreate session to drop any bad keep-alive sockets
                self._new_session()
                delay = min(delay * 1.7, 8.0)
                attempt += 1

    def mk_remote_dir(self, rel: str):
        rel = rel.strip("/")
        if not rel or rel == ".":
            return
        parts = [p for p in rel.split("/") if p]
        accum = ""
        for p in parts:
            accum = f"{accum}/{p}" if accum else p
            url = f"{self.fs}/{encode_remote_path(accum)}/"

            def do_put():
                return self.sess.put(url, auth=self.auth, timeout=10)

            self._with_backoff(do_put, desc=f"mkdir {accum}", max_wait=30.0)

    def put_file(self, src: Path, rel: str, max_wait: float = 60.0):
        rel = rel.strip("/")
        self.mk_remote_dir(str(Path(rel).parent))
        url = f"{self.fs}/{encode_remote_path(rel)}"

        def do_put():
            with src.open("rb") as f:
                # Expect: 100-continue can reduce wasted upload on flaky links
                r = self.sess.put(
                    url,
                    data=f,
                    auth=self.auth,
                    headers={"Expect": "100-continue"},
                    timeout=60,
                )
            r.raise_for_status()
            return r

        self._with_backoff(do_put, desc=f"put {rel}", max_wait=max_wait)
        print(f"↑  {rel}")

    def delete_path(self, rel: str, max_wait: float = 30.0):
        rel = rel.strip("/")
        url_file = f"{self.fs}/{encode_remote_path(rel)}"
        url_dir = f"{url_file}/"

        def try_delete(u):
            def do_del():
                r = self.sess.delete(u, auth=self.auth, timeout=15)
                # 404 is fine (idempotent)
                if r.status_code not in (200, 201, 204, 404):
                    r.raise_for_status()
                return r

            self._with_backoff(do_del, desc=f"delete {rel}", max_wait=max_wait)

        # try file, then dir
        try:
            try_delete(url_file)
        except Exception:
            pass
        try:
            try_delete(url_dir)
        except Exception:
            pass
        print(f"×  {rel}")


# ------------------------------ Initial sync & watch ------------------------------
def initial_sync(api: WebWorkflow, root: Path):
    print(f"Initial sync: {root}  ->  {api.base}")

    # Gather files
    files = []
    for path in root.rglob("*"):
        if path.is_dir() or is_excluded(path):
            continue
        rel = str(path.relative_to(root)).replace("\\", "/")
        files.append((path, rel))

    # Upload order: everything except these, then these last
    critical_last = {"code.py", "main.py", "boot.py", "settings.toml"}

    def is_critical(rel: str) -> bool:
        name = Path(rel).name.lower()
        return name in critical_last

    files.sort(key=lambda pr: (is_critical(pr[1]), pr[1]))

    for path, rel in files:
        # small settle delay between files helps stability on tiny boards
        try:
            api.put_file(path, rel)
            time.sleep(0.10)
        except Exception:
            # If a critical file caused a reset mid-sync, a short pause then continue
            print(f"Warning: failed uploading {rel}; continuing.", file=sys.stderr)
            # Optional: re-probe with backoff here if you want


class Handler(FileSystemEventHandler):
    def __init__(self, api: WebWorkflow, root: Path):
        super().__init__()
        self.api = api
        self.root = root

    def _rel(self, p: str) -> str:
        return str(Path(p).resolve().relative_to(self.root)).replace("\\", "/")

    def on_created(self, event):
        p = Path(event.src_path)
        if is_excluded(p):
            return
        if p.is_dir():
            self.api.mk_remote_dir(self._rel(event.src_path))
            print(f"＋  {self._rel(event.src_path)}/")
        elif p.is_file():
            self.api.put_file(p, self._rel(event.src_path))

    def on_modified(self, event):
        p = Path(event.src_path)
        if is_excluded(p) or not p.is_file():
            return
        self.api.put_file(p, self._rel(event.src_path))

    def on_moved(self, event):
        # Treat as delete old + put new
        src = Path(event.src_path)
        dst = Path(event.dest_path)
        if not is_excluded(src):
            self.api.delete_path(self._rel(event.src_path))
        if not is_excluded(dst):
            if dst.is_dir():
                self.api.mk_remote_dir(self._rel(event.dest_path))
                print(f"＋  {self._rel(event.dest_path)}/")
            elif dst.is_file():
                self.api.put_file(dst, self._rel(event.dest_path))

    def on_deleted(self, event):
        rel = self._rel(event.src_path)
        self.api.delete_path(rel)


def watch_loop(api: WebWorkflow, root: Path):
    if not HAVE_WATCHDOG:
        print("Install watchdog for watching:  pip install watchdog", file=sys.stderr)
        return
    obs = Observer()
    handler = Handler(api, root.resolve())
    obs.schedule(handler, str(root), recursive=True)
    obs.start()
    print("Watching for changes… (Ctrl+C to stop)")
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        obs.stop()
        obs.join()


# ------------------------------ Main ------------------------------
def probe_with_backoff(api, max_wait: float = 60.0) -> bool:
    """
    Try reaching <base>/fs/ with exponential backoff up to max_wait seconds.
    Prints progress and supports Ctrl+C to cancel.
    Returns True if reachable, else False.
    """
    start = time.time()
    delay = 0.5  # seconds
    attempt = 1
    target = f"{api.fs}/"

    print(f"Waiting for Web Workflow at {target} (Ctrl+C to cancel)…")
    while True:
        try:
            r = api.sess.get(
                target,
                auth=api.auth,
                headers={"Accept": "application/json"},
                timeout=3,
            )
            r.raise_for_status()
            print(f"✓ Reached {target}")
            return True
        except Exception as e:
            elapsed = time.time() - start
            remaining = max_wait - elapsed
            if remaining <= 0:
                print(f"✗ Still unreachable after {int(max_wait)}s: {target}")
                return False

            # Show a friendly status line, then sleep
            print(
                f"  attempt {attempt}: not ready ({type(e).__name__}). "
                f"retrying in {delay:.1f}s … [{int(remaining)}s left]"
            )
            try:
                time.sleep(delay)
            except KeyboardInterrupt:
                print("\nCanceled by user.")
                return False

            # Exponential backoff with an upper bound to keep logs readable
            delay = min(delay * 1.7, 8.0)
            attempt += 1


def main():
    ap = argparse.ArgumentParser(description="CircuitPython setup & sync CLI")
    ap.add_argument("ssid")
    ap.add_argument("wifi_password")
    ap.add_argument("web_password")
    ap.add_argument(
        "--instance", default="circuitpy", help="CIRCUITPY_WEB_INSTANCE_NAME"
    )
    ap.add_argument(
        "--port-pattern",
        default="/dev/tty.usb*",
        help="Glob for serial ports (default: /dev/tty.usb*)",
    )
    args = ap.parse_args()

    print_hr()
    print("Pick a serial port")
    print_hr()
    while True:
        try:
            port = choose_port_menu(args.port_pattern)
            write_settings_over_serial(
                port, args.ssid, args.wifi_password, args.web_password, args.instance
            )
            break
        except RuntimeError as e:
            if str(e) == "SERIAL_BUSY":
                print(f"Port '{port}' is busy.")
                sel = input_prompt(
                    "Choose: [s]elect another port  [r]etry same port  [q]uit  > "
                )
                if sel.lower() == "s":
                    continue
                elif sel.lower() == "r":
                    # retry same
                    continue
                else:
                    sys.exit(1)
            else:
                print(f"Serial error: {e}", file=sys.stderr)
                sys.exit(1)
        except SerialException as e:
            print(f"Serial failed on '{port}': {e}", file=sys.stderr)
            sel = input_prompt("Choose: [s]elect another port  [q]uit  > ")
            if sel.lower() == "s":
                continue
            else:
                sys.exit(1)

    print_hr()
    # After successful serial setup:
    print("Unplug & re-plug your ESP device")
    print("This forces USB re-enumeration and ensures Web Workflow starts cleanly.")
    print("Close any serial monitors (Arduino IDE, Thonny, mpremote) first.")
    input_prompt("Press Enter once you've re-plugged the board… ")
    time.sleep(1.0)  # brief settle

    print("Discover devices via circuitpython.local")
    print_hr()
    base = detect_discovery_base()
    if not base:
        print("Could not resolve circuitpython.local; continuing anyway.")

    dev = menu_pick_device(base)
    hostname = dev.get("hostname") or ""
    ip = dev.get("ip") or ""
    if not hostname:
        print("No hostname in selection.", file=sys.stderr)
        sys.exit(1)

    cpy_url = f"http://{hostname}.local"
    cpy_pass = args.web_password

    # Save .env.cpy
    print_hr()
    print("Environment:")
    print(f"  CPY_URL = {cpy_url}")
    print(f"  CPY_PASS = <hidden>")
    yn = input_prompt(
        "Write these to ./.env.cpy (and export for this run)? [Y/n] ", "Y"
    )
    if yn.lower().startswith("y"):
        Path(".env.cpy").write_text(
            f'CPY_URL="{cpy_url}"\nCPY_PASS="{cpy_pass}"\n', encoding="utf-8"
        )
        print("Wrote .env.cpy")
        os.environ["CPY_URL"] = cpy_url
        os.environ["CPY_PASS"] = cpy_pass

    # Web Workflow session
    api = WebWorkflow(cpy_url, cpy_pass)

    # Try hostname (.local) with backoff
    if not probe_with_backoff(api):
        # Fallback to IP (if available) with backoff
        if ip:
            print(f"mDNS probe failed; trying IP {ip} …")
            api = WebWorkflow(f"http://{ip}", cpy_pass)
            if not probe_with_backoff(api):
                print(
                    f"Cannot reach {api.fs}/  (check network/Web Workflow/password).",
                    file=sys.stderr,
                )
                print(
                    f"Quick test: curl -sSf -u \":$CPY_PASS\" -H 'Accept: application/json' {api.fs}/"
                )
                sys.exit(1)
        else:
            print(
                f"Cannot reach {api.fs}/  (check network/Web Workflow/password).",
                file=sys.stderr,
            )
            print(
                f"Quick test: curl -sSf -u \":$CPY_PASS\" -H 'Accept: application/json' {api.fs}/"
            )
            sys.exit(1)

    print_hr()
    print(f"Next for {api.base}:")
    print("  [1] Initial sync now, then watch for changes")
    print("  [2] Watch for changes only (no initial sync)")
    print("  [3] Skip")
    act = input_prompt("Choose [1/2/3]: ", "1")
    root = Path.cwd()

    if act == "1":
        initial_sync(api, root)
        watch_loop(api, root)
    elif act == "2":
        watch_loop(api, root)
    else:
        print("Done. Variables saved in .env.cpy")
        print("Use later:  source .env.cpy")


if __name__ == "__main__":
    main()
