#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Run one of Corry's Python job modules outside Calamares, for CI and manual tests.

    run-job.py MODULE [--root DIR] [--storage FILE.json] [--config FILE.conf] [--allow-live-root]

A stand-in for libcalamares runs the module's commands with chroot when --root
is not /, and directly against this system with --root / --allow-live-root
(only for throw-away containers!). Global storage is read from and written
back to the JSON file, so a caller can check what the job recorded.
"""
import argparse
import importlib.util
import json
import subprocess
import sys
import types
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("module")
    parser.add_argument("--root", default="/")
    parser.add_argument("--storage", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--allow-live-root", action="store_true")
    args = parser.parse_args()
    storage = json.loads(args.storage.read_text()) if args.storage and args.storage.exists() else {}
    storage.setdefault("rootMountPoint", args.root)
    config = args.config or ROOT / "config/corry/modules" / (args.module + ".conf")
    configuration = yaml.safe_load(config.read_text()) if config.exists() else {}

    def wrap(command):
        return list(command) if args.root == "/" else ["chroot", args.root] + list(command)

    def target_env_call(command, stdin=None, timeout=-1):
        print("+", " ".join(command), flush=True)
        return subprocess.run(wrap(command), stdin=subprocess.DEVNULL, timeout=timeout if timeout > 0 else None).returncode

    def target_env_process_output(command, callback=None, stdin=None, timeout=-1):
        print("+", " ".join(command), flush=True)
        result = subprocess.run(wrap(command), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, timeout=timeout if timeout > 0 else None)
        if result.returncode:
            raise subprocess.CalledProcessError(result.returncode, command, output=result.stdout)
        return result.stdout

    fake = types.SimpleNamespace(
        globalstorage=types.SimpleNamespace(value=storage.get, insert=storage.__setitem__, contains=storage.__contains__),
        job=types.SimpleNamespace(configuration=configuration, setprogress=lambda value: None),
        utils=types.SimpleNamespace(target_env_call=target_env_call, target_env_process_output=target_env_process_output,
                                    check_target_env_call=target_env_call, check_target_env_output=target_env_process_output,
                                    warning=lambda text: print("WARNING:", text, flush=True),
                                    debug=lambda text: print("DEBUG:", text, flush=True),
                                    gettext_path=lambda: None, gettext_languages=lambda: []))
    sys.modules["libcalamares"] = fake
    sys.modules["libcalamares.utils"] = fake.utils
    spec = importlib.util.spec_from_file_location(args.module, ROOT / "src/modules" / args.module / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if args.allow_live_root:
        module.ALLOW_LIVE_ROOT = True
    result = module.run()
    print("RESULT:", result, flush=True)
    if args.storage:
        args.storage.write_text(json.dumps(storage, indent=1, default=str))
    return 0 if result is None else 1


if __name__ == "__main__":
    sys.exit(main())
