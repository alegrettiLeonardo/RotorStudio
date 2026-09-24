from __future__ import annotations
import argparse,hashlib,json,re,shutil,zipfile
from pathlib import Path

SOLVER_CALLS=['shftelem','taper','shftasym','rotormtx','rotorasym','bearmtx','bearasym','chr_root','chr_asym','chr_root_coax','crit_spd','freq_rsp','freq_aux','freq_fdn','freq_rsp_coax','freq_asym','time_fdn','runup','whirl']

def sha256_bytes(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--zip',required=True)
    ap.add_argument('--source-manifest',default='validation/book_problems/problem_source_manifest.json')
    ap.add_argument('--outdir',required=True)
    ap.add_argument('--inventory',required=True)
    a=ap.parse_args()

    manifest=json.loads(Path(a.source_manifest).read_text())
    original_archive_sha=manifest['original_archive_sha256']
    expected_files=manifest['files']

    zp=Path(a.zip)
    repo_archive_sha=sha256_bytes(zp.read_bytes())
    out=Path(a.outdir);shutil.rmtree(out,ignore_errors=True);out.mkdir(parents=True)

    with zipfile.ZipFile(zp) as z:
        entries={}
        for n in z.namelist():
            if n.endswith('/') or '/._' in n or '__MACOSX' in n: continue
            if not n.startswith('rb_prob_solns/'): continue
            data=z.read(n); base=Path(n).name
            entries[base]=data
            (out/base).write_bytes(data)

    actual_names=set(entries)
    expected_names=set(expected_files)
    if actual_names!=expected_names:
        raise SystemExit(f'problem source set mismatch missing={sorted(expected_names-actual_names)} extra={sorted(actual_names-expected_names)}')

    bad={}
    for name,wanted in expected_files.items():
        got=sha256_bytes(entries[name])
        if got!=wanted: bad[name]={'expected':wanted,'actual':got}
    if bad:
        raise SystemExit('problem source content mismatch against original archive manifest: '+json.dumps(bad,sort_keys=True))

    probs=[]
    for p in sorted(out.glob('Problem_*.m')):
        txt=p.read_text(errors='replace')
        calls=[k for k in SOLVER_CALLS if re.search(r'\b'+re.escape(k)+r'\s*\(',txt,re.I)]
        probs.append({
            'problem':p.stem,
            'sha256':sha256_bytes(p.read_bytes()),
            'class':'A_SOLVER' if calls else 'B_ANALYTICAL',
            'solver_calls':calls,
        })

    inv={
        'schema_version':2,
        'authority':'DRM_problem_scripts.zip',
        'original_archive_sha256':original_archive_sha,
        'repository_archive_sha256':repo_archive_sha,
        'source_equivalent_to_original':True,
        'source_manifest':str(a.source_manifest),
        'problem_count':len(probs),
        'classification':{
            'A_SOLVER':sum(x['class']=='A_SOLVER' for x in probs),
            'B_ANALYTICAL':sum(x['class']=='B_ANALYTICAL' for x in probs),
        },
        'helper_files':{'bnpr.m':sha256_bytes((out/'bnpr.m').read_bytes())},
        'problems':probs,
    }
    Path(a.inventory).parent.mkdir(parents=True,exist_ok=True)
    Path(a.inventory).write_text(json.dumps(inv,indent=2)+'\n')

    if len(probs)!=83 or inv['classification']!={'A_SOLVER':19,'B_ANALYTICAL':64}:
        raise SystemExit(f'unexpected problem inventory {inv["classification"]} count={len(probs)}')

    print(json.dumps({
        'original_archive_sha256':original_archive_sha,
        'repository_archive_sha256':repo_archive_sha,
        'source_equivalent_to_original':True,
        'problem_count':len(probs),
        **inv['classification'],
    }))
if __name__=='__main__':
    main()
