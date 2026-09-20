import json
from pathlib import Path
import zlib


def write_deflated(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    compressor = zlib.compressobj(wbits=-zlib.MAX_WBITS)
    payload = ("\ufeff" + json.dumps(value)).encode("utf-8")
    path.write_bytes(compressor.compress(payload) + compressor.flush())
    return path
