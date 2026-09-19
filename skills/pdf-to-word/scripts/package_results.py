"""Package current checked artifacts; never infer that human review occurred."""
import argparse
import json
import zipfile
from pipeline_config import ROOT, WORK, OUT, sha, word_path, render_path, assert_audit_current

def package():
    audits=sorted(WORK.glob('*/audit.json'))
    if not audits:raise ValueError('No converted documents to package')
    rows=[];files=[]
    for path in audits:
        stem=path.parent.name;folder=path.parent;audit=assert_audit_current(stem)
        checks=json.loads((folder/'checks.json').read_text())
        fingerprints={'source_sha256':audit['sha256'],'word_sha256':sha(word_path(stem)),'preview_sha256':sha(render_path(stem))}
        if not checks.get('passed') or any(checks.get(k)!=v for k,v in fingerprints.items()):
            raise ValueError(f'{stem}: current artifacts must pass checks before packaging')
        manual_path=folder/'manual-review.json'
        manual=json.loads(manual_path.read_text()) if manual_path.exists() else None
        if manual and any(manual.get(k)!=v for k,v in fingerprints.items()):
            raise ValueError(f'{stem}: manual review record is stale')
        rows.append({'file':stem,**checks,'manual_review':manual or {'status':'not_recorded'},
                     'image_pages':[p['page'] for p in audit['pages'] if p['regions']],
                     'full_image_pages':[p['page'] for p in audit['pages'] if p['method']=='source-page-image']})
        files.extend([(word_path(stem),'word/'+word_path(stem).name),(render_path(stem),'preview/'+render_path(stem).name)])
        for name in ['audit.json','checks.json','validation.log','coverage.json','scan-review.json','manual-review.json']:
            p=folder/name
            if not p.exists():continue
            if name=='coverage.json':
                c=json.loads(p.read_text())
                if not c.get('passed') or any(c.get(k)!=fingerprints[k] for k in ['source_sha256','word_sha256']):
                    raise ValueError(f'{stem}: coverage record failed or is stale')
            if name=='scan-review.json':
                review=json.loads(p.read_text())
                if any(review.get(k)!=fingerprints[k] for k in ['source_sha256','word_sha256']):
                    raise ValueError(f'{stem}: OCR comparison record is stale')
            files.append((p,'checks/'+stem+'/'+name))
    report={'documents':len(rows),'pages':sum(r['source_pages'] for r in rows),'files':rows,
            'limitations':'Automated checks do not certify OCR accuracy or visual layout. Source image regions are not editable text.'}
    OUT.mkdir(parents=True,exist_ok=True)
    summary=OUT/'quality-report.json';summary.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    archive=OUT/'delivery.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        z.write(summary,'quality-report.json')
        for path,name in files:z.write(path,name)
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:raise RuntimeError('Archive integrity check failed')
    print(archive, len(rows),'documents; human review status is recorded separately')

if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    package()
