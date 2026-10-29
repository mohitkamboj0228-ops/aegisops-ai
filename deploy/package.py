"""Create a minimal, reproducible deploy ZIP from built source; excludes local data."""
import argparse, hashlib, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def package(destination):
    paths=[ROOT/'backend/server.py',ROOT/'backend/ai.py',ROOT/'backend/remediation.py',ROOT/'backend/requirements-ai.txt',ROOT/'deploy/install.sh']
    assets=sorted((ROOT/'frontend/dist').rglob('*'))
    if not (ROOT/'frontend/dist/index.html').is_file(): raise ValueError('Build frontend first: npm run build --prefix frontend')
    paths+= [p for p in assets if p.is_file()]
    digest=hashlib.sha256()
    for p in paths:
        digest.update(p.relative_to(ROOT).as_posix().encode()+b'\0'+p.read_bytes())
    release=digest.hexdigest()
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
        for p in paths:
            info=zipfile.ZipInfo(p.relative_to(ROOT).as_posix(),date_time=(2026,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16
            archive.writestr(info,p.read_bytes())
        info=zipfile.ZipInfo('RELEASE_ID',date_time=(2026,1,1,0,0,0))
        info.compress_type=zipfile.ZIP_DEFLATED
        info.external_attr=0o100644<<16
        archive.writestr(info,release)
    return release

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('output');args=parser.parse_args()
    print(package(args.output))
