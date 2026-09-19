"""Independent native-glyph and table-cell accounting against original PDFs."""
from pathlib import Path
from collections import Counter
import json,re,argparse
import pymupdf as fitz
from docx import Document
from batch_layout import ROOT,WORK,clean,font_maps,font_size_scale
from pipeline_config import assert_audit_current, source, word_path

def norm(t):return re.sub(r'\s+','',t)
def inrect(x,y,r):return r[0]-.1<=x<=r[2]+.1 and r[1]-.1<=y<=r[3]+.1

def check_coverage(stem):
    folder=WORK/stem
    audit=assert_audit_current(stem);layout=json.loads((folder/'layout.json').read_text())
    pdf=fitz.open(source(stem));maps=font_maps(pdf)
    doc=Document(word_path(stem))
    result={'native_pages':[],'table_cells_checked':0,'table_numeric_errors':[],'table_text_errors':[]}
    table_idx=0
    for idx,p in enumerate(pdf):
        a=audit['pages'][idx];method=layout['pages'][idx]['method']
        if a['method']=='source-page-image' or method!='native':continue
        scale=595.276/p.rect.width;ss=font_size_scale(p);chars=[]
        for block in p.get_text('rawdict')['blocks']:
            if block['type']!=0:continue
            for line in block['lines']:
                for s in line['spans']:
                    for c in s['chars']:
                        x=(c['bbox'][0]+c['bbox'][2])/2*scale;y=(c['origin'][1]-s['size']*ss*.3)*scale
                        chars.append((x,y,clean(c['c'],s['font'],maps)))
        regions=a['regions'];table_regions=[t['bbox'] for t in a['tables']]
        source_text=''.join(c for x,y,c in chars if not any(inrect(x,y,r) for r in regions+table_regions))
        actual=''.join(a['texts'])
        missing=Counter(norm(source_text))-Counter(norm(actual))
        result['native_pages'].append({'page':idx+1,'source_chars_outside_images_tables':len(norm(source_text)),
            'editable_chars':len(norm(actual)),'missing':dict(missing)})
        for tab in a['tables']:
            actual_table=doc.tables[table_idx];table_idx+=1
            for cell in tab['cells']:
                result['table_cells_checked']+=1
                # Native character positions independently establish cell membership.
                cc=[(x,y,t) for x,y,t in chars if inrect(x,y,cell['bbox'])]
                expected=Counter(norm(''.join(t for x,y,t in cc)))
                got=Counter(norm(actual_table.cell(cell['row'],cell['col']).text))
                if expected!=got:
                    result['table_text_errors'].append({'page':idx+1,'row':cell['row'],'col':cell['col'],
                        'missing':dict(expected-got),'extra':dict(got-expected)})
                nums=lambda t:Counter(re.findall(r'\d+(?:\.\d+)?',norm(t)))
                # Compare audit tokens, whose source baselines were reconstructed;
                # this checks table serialization including merged cell positions.
                if nums(cell['text'])!=nums(actual_table.cell(cell['row'],cell['col']).text):
                    result['table_numeric_errors'].append({'page':idx+1,'row':cell['row'],'col':cell['col']})
    result['passed']=not any(p['missing'] for p in result['native_pages']) and not result['table_text_errors'] and not result['table_numeric_errors']
    result['source_sha256']=audit['sha256'];result['word_sha256']=audit['word_sha256']
    (folder/'coverage.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(folder.name,'missing',[(x['page'],x['missing']) for x in result['native_pages'] if x['missing']],
        'cells',result['table_cells_checked'],'errors',len(result['table_text_errors']),len(result['table_numeric_errors']))

    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files',nargs='*',help='PDF basenames; omit for all generated audits')
    args=parser.parse_args()
    stems=[Path(s).stem for s in args.files] or [p.parent.name for p in WORK.glob('*/audit.json')]
    if not stems:parser.error('No generated document audits found')
    results=[check_coverage(stem) for stem in stems]
    if any(not r['passed'] for r in results):raise SystemExit('Source coverage checks failed')
