"""Local PDF-to-Word pipeline. Automated output remains a draft until reviewed."""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
import pymupdf as fitz
from pipeline_config import PROJECT, ROOT, INPUT, WORK, profile, sha, source, word_path, render_path, require_external
from batch_layout import analyze, route
from batch_convert import build
from batch_check import check

def run(args, **kw):
    subprocess.run([str(a) for a in args], check=True, **kw)

def prepare(stem, mode='auto'):
    src=source(stem);settings=profile(stem);folder=WORK/stem
    folder.mkdir(parents=True,exist_ok=True)
    fingerprint=folder/'source.sha256'
    if fingerprint.exists() and fingerprint.read_text().strip()!=sha(src):
        raise ValueError(f'{stem}: source changed; use a new basename or clear its work folder after review')
    # Write before OCR so failed/interrupted runs cannot silently reuse stale images.
    fingerprint.write_text(sha(src)+'\n')
    pdf=fitz.open(src)
    methods=(settings.get('page_methods') or route(pdf)) if mode=='auto' else [mode]*len(pdf)
    if len(methods)!=len(pdf) or any(m not in {'native','ocr'} for m in methods):
        raise ValueError('page_methods must contain native/ocr for every source page')
    pending=[]
    for i,p in enumerate(pdf):
        if methods[i]!='ocr':continue
        img=folder/f'page-{i+1:03}.png'
        if not img.exists():p.get_pixmap(matrix=fitz.Matrix(2400/p.rect.width,2400/p.rect.width),alpha=False).save(img)
        if not img.with_suffix('.rapid.json').exists():pending.append(img)
    if pending:run([sys.executable,PROJECT/'scripts/ocr_batch.py',*pending])
    data=analyze(stem,methods);data['source_sha256']=sha(src)
    (folder/'layout.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
    (folder/'layout.txt').write_text('\n'.join(f"PAGE {p['page']} {p['method']}\n"+'\n'.join(f"{l['bbox'][1]:.1f} {l['text']}" for l in p['lines']) for p in data['pages']))
    print(stem,'prepared',len(pdf),'pages',methods,flush=True)

def render(stems):
    binary=os.environ.get('SOFFICE') or shutil.which('soffice') or '/Applications/LibreOffice.app/Contents/MacOS/soffice'
    if not Path(binary).is_file():raise FileNotFoundError('LibreOffice is required; set SOFFICE to its executable')
    out=WORK/'rendered';out.mkdir(parents=True,exist_ok=True)
    env=os.environ.copy();config=Path('/opt/homebrew/etc/fonts/fonts.conf')
    if config.exists():
        env.setdefault('FONTCONFIG_FILE',str(config));env.setdefault('FONTCONFIG_PATH',str(config.parent))
    for stem in stems:
        word=word_path(stem);dest=render_path(stem)
        if not word.is_file():raise FileNotFoundError(word)
        # LibreOffice can return success without writing a file. A fresh path
        # prevents an old preview from being mistaken for the current render.
        dest.unlink(missing_ok=True)
        run([binary,'-env:UserInstallation='+(ROOT/'work/lo-profile').as_uri(),'--headless','--convert-to','pdf','--outdir',out,word],env=env)
        if not dest.is_file():raise RuntimeError(f'{stem}: LibreOffice did not create a preview')
        (WORK/stem/'render.json').write_text(json.dumps({'word_sha256':sha(word),'pdf_sha256':sha(dest)},indent=2))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['prepare','build','render','check','all'])
    parser.add_argument('files',nargs='*',help='PDF basenames in input/; omit for all')
    parser.add_argument('--mode',choices=['auto','native','ocr'],default='auto')
    args=parser.parse_args()
    require_external(ROOT)
    stems=[Path(f).stem for f in args.files] or [p.stem for p in sorted(INPUT.glob('*.pdf'))]
    if not stems:parser.error('No PDFs in input/. Add PDFs before running the pipeline.')
    if len(stems)!=len(set(stems)):parser.error('Duplicate input basenames')
    for stem in stems:
        source(stem)
        if args.stage in ['prepare','all']:prepare(stem,args.mode)
        if args.stage in ['build','all']:build(stem)
    if args.stage in ['render','all']:render(stems)
    if args.stage in ['check','all']:
        failed=[]
        for stem in stems:
            c=check(stem)
            if not c['passed']:failed.append(stem)
        if failed:raise SystemExit('CHECK FAILED: '+', '.join(failed))
        print('Automated checks passed. OCR correctness and layout still require visual review.')

if __name__=='__main__':main()
