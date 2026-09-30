"""Extract a newly-built package and verify every recorded payload hash."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import zipfile


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dist',type=Path,required=True); p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():
        raise FileExistsError('Refusing to reuse an existing extraction directory.')
    data=json.loads((a.dist/'PACKAGE.json').read_text(encoding='utf-8'))
    if Path(data['archive']).name != data['archive']:
        raise ValueError('Archive must be a file within the distribution directory.')
    archive=a.dist/data['archive']
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=data['sha256']:
        raise ValueError('Archive hash mismatch.')
    a.out.mkdir(parents=True)
    def check_name(name):
        target=(a.out/name).resolve()
        if not target.is_relative_to(a.out.resolve()):
            raise ValueError('Archive member escapes the extraction directory.')
    if archive.suffix=='.zip':
        with zipfile.ZipFile(archive) as z:
            for item in z.infolist():
                check_name(item.filename)
                if (item.external_attr>>16)&0o170000 == 0o120000:
                    raise ValueError('ZIP symbolic links are not supported.')
            z.extractall(a.out)
    else:
        with tarfile.open(archive) as t:
            for item in t.getmembers():check_name(item.name)
            t.extractall(a.out,filter='data')
    root=a.out/'RotorStudioFlet'
    manifest=json.loads((root/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    if manifest['source_head']!=data['source_head']:
        raise ValueError('Package source identity mismatch.')
    for name,expected in manifest['files'].items():
        check_name('RotorStudioFlet/'+name)
        target=(root/name).resolve()
        if not target.is_relative_to(root.resolve()):raise ValueError('Manifest entry escapes package.')
        if hashlib.sha256(target.read_bytes()).hexdigest()!=expected:
            raise ValueError('Extracted file hash mismatch: '+name)
    print(json.dumps({'status':'EXTRACTION_HASHES_PASS','source_head':data['source_head'],
                      'files':len(manifest['files']),'root':str(root.resolve())}))


if __name__=='__main__':main()
