import os

try:
    os.stat("/.safemode")
    SAFE = True
except OSError:
    SAFE = False

if SAFE:
    print(">>> safe mode: USB reinit will be skipped")
