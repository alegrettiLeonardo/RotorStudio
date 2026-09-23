from pathlib import Path
import hashlib
ROOT=Path(__file__).resolve().parents[2]
HASHES=ROOT/'validation'/'baseline'/'transient'/'SOURCE_HASHES.sha256'

def test_transient_authority_source_hashes_frozen():
    for line in HASHES.read_text().splitlines():
        if not line.strip(): continue
        expected,path=line.split(None,1);p=ROOT/path.strip()
        assert p.exists(),path
        assert hashlib.sha256(p.read_bytes()).hexdigest()==expected,path
