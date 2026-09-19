"""Use an independent OCR engine to surface disagreements for visual review.

This does not decide which engine is correct and never changes source text.
"""
import json, re, argparse
from pathlib import Path
from difflib import SequenceMatcher
from batch_layout import WORK, normalize
from pipeline_config import assert_audit_current

def norm(t):
    return re.sub(r'[^\wμµ%℃≤≥<>+\-]', '', normalize(t)).replace('—','-')

def numbers(t):
    return re.findall(r'\d+(?:\.\d+)?', re.sub(r'\s+', '', normalize(t)))

def overlap(a,b):
    return max(0,min(a[2],b[2])-max(a[0],b[0]))

def review(stem):
    folder=WORK/stem
    audit=assert_audit_current(stem)
    layout=json.loads((folder/'layout.json').read_text())
    flags=[];checked=0;uncovered=[]
    for page,lay in zip(audit['pages'],layout['pages']):
        if page['method']=='source-page-image' or lay['method']!='ocr':continue
        n=page['page'];height=lay['height']
        vision=json.loads((folder/f'page-{n:03}.ocr.json').read_text())['lines']
        for v in vision:
            v['box']=[v['bbox'][0]*595.276,v['bbox'][1]*height,v['bbox'][2]*595.276,v['bbox'][3]*height]
        for text,box in zip(page['texts'],page.get('text_boxes',[])):
            candidates=[]
            for v in vision:
                b=v['box']
                if abs((b[1]+b[3]-box[1]-box[3])/2)<max(b[3]-b[1],box[3]-box[1])*.55 and overlap(b,box)>min(b[2]-b[0],box[2]-box[0])*.45:
                    candidates.append(v)
            vt=' '.join(v['text'] for v in sorted(candidates,key=lambda v:v['box'][0]))
            similarity=SequenceMatcher(None,norm(text),norm(vt)).ratio()
            checked+=1
            if numbers(text)!=numbers(vt) or similarity<.87:
                flags.append({'page':n,'bbox':box,'rapid':text,'vision':vt,'similarity':round(similarity,3),'numeric_disagreement':numbers(text)!=numbers(vt)})
        for v in vision:
            b=v['box'];cx=(b[0]+b[2])/2;cy=(b[1]+b[3])/2
            if any(r[0]-3<=cx<=r[2]+3 and r[1]-3<=cy<=r[3]+3 for r in page['regions']+page.get('text_boxes',[])):continue
            if len(norm(v['text']))>=2:uncovered.append({'page':n,'bbox':b,'text':v['text']})
    result={'stem':stem,'source_sha256':audit['sha256'],'word_sha256':audit['word_sha256'],
        'editable_lines_checked':checked,'disagreements':flags,'uncovered_vision_regions':uncovered}
    (folder/'scan-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(stem,'lines',checked,'disagreements',len(flags),'uncovered',len(uncovered))
    for f in flags:print(f"  p{f['page']} y={f['bbox'][1]:.1f}: {f['rapid']}\n    Vision: {f['vision']}")
    for v in uncovered:print('  UNCOVERED',v)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files',nargs='*',help='Prepared PDF basenames; omit for all OCR documents')
    args=parser.parse_args()
    stems=[Path(s).stem for s in args.files] or [p.parent.name for p in WORK.glob('*/layout.json') if any(x['method']=='ocr' for x in json.loads(p.read_text())['pages'])]
    if not stems:parser.error('No prepared OCR documents found')
    for stem in stems:review(stem)
