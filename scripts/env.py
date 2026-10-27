"""Imported first by every script: makes output and tool lookup work the same on every machine.

- stdout/stderr are UTF-8: on Windows, output piped to an agent is cp1252 by default and crashes on course titles
  with characters such as an arrow or an emoji.
- Windows: tools installed during this session (winget ffmpeg/Deno) are only on the PATH saved in the registry,
  not on the PATH of the already-running terminal, so the saved one is merged in (the terminal's entries win).
"""
import os, sys

for s in (sys.stdout, sys.stderr):
    s.reconfigure(encoding="utf-8", errors="replace")

if os.name == "nt":
    import winreg

    for hive, key in ((winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
                      (winreg.HKEY_CURRENT_USER, "Environment")):
        try:
            with winreg.OpenKey(hive, key) as k:
                saved = os.path.expandvars(winreg.QueryValueEx(k, "Path")[0])
        except OSError:
            continue
        have = {p.lower() for p in os.environ.get("PATH", "").split(os.pathsep)}
        os.environ["PATH"] = os.environ.get("PATH", "") + "".join(os.pathsep + p for p in saved.split(os.pathsep) if p and p.lower() not in have)
