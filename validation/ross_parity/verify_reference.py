"""Immutable reference integrity and strict numerical comparison."""
import argparse
import json
from pathlib import Path
import numpy as np
from generate_reference import ROSS_SHA, digest

def verify(root):
    root=Path(root)
    manifest=json.loads((root/'authority.json').read_text())
    if manifest['commit'] != ROSS_SHA:
        raise ValueError('Wrong authority')
    schema_key='files_sha256' if 'files_sha256' in manifest else 'golden_sha256'
    files=manifest.get(schema_key,{})
    if not files:
        raise ValueError('Empty reference set')
    # A0-A4 reference sets contain paired JSON/NPZ data. A5 UCS freezes
    # deterministic JSON authority payloads only; accept that additive schema
    # without weakening the historical NPZ requirement.
    if schema_key=='files_sha256' and not any(p.endswith('.npz') for p in files):
        raise ValueError('Empty numerical reference set')
    if {p.name for p in root.iterdir()} != set(files)|{'authority.json'}:
        raise ValueError('Unexpected or missing reference file')
    for name,expected in files.items():
        if Path(name).name != name or digest(root/name)!=expected:
            raise ValueError(f'Integrity failure: {name}')
    for name in files:
        if name.endswith('.npz'):
            with np.load(root/name,allow_pickle=False) as data:
                if not data.files or any(not np.isfinite(data[k]).all() for k in data.files):
                    raise ValueError(f'Nonfinite or empty reference: {name}')
    return manifest

def compare(reference,candidate,rtol=1e-12,atol=1e-12):
    a=verify(reference); b=verify(candidate)
    ak='files_sha256' if 'files_sha256' in a else 'golden_sha256'
    bk='files_sha256' if 'files_sha256' in b else 'golden_sha256'
    if ak!=bk or a['source_sha256'] != b['source_sha256'] or set(a[ak]) != set(b[bk]):
        raise ValueError('Authority source or case set differs')
    for name in a[ak]:
        if name.endswith('.json'):
            if (Path(reference)/name).read_bytes() != (Path(candidate)/name).read_bytes():
                raise ValueError(f'Input mismatch: {name}')
        elif name.endswith('.npz'):
            with np.load(Path(reference)/name) as x,np.load(Path(candidate)/name) as y:
                if set(x.files)!=set(y.files): raise ValueError('Quantity set differs')
                for key in x.files:
                    if x[key].shape!=y[key].shape: raise ValueError(f'Shape mismatch: {name}:{key}')
                    np.testing.assert_allclose(x[key],y[key],rtol=rtol,atol=atol,equal_nan=False,err_msg=f'{name}:{key}')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('reference');p.add_argument('--candidate')
    args=p.parse_args();verify(args.reference)
    if args.candidate: compare(args.reference,args.candidate)
    print('PASS: reference integrity'+ (' and ROSS reproducibility' if args.candidate else ''))
