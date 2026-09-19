"""Validate package structure, page count, text transfer and render geometry."""
from pathlib import Path
import json,re,sys,subprocess,hashlib
from collections import Counter
import pymupdf as fitz
from docx import Document
from PIL import Image,ImageDraw
from batch_layout import ROOT,WORK
from pipeline_config import VALIDATOR, assert_audit_current, word_path, render_path, sha

def norm(t):return re.sub(r'\s+','',t)
def check(stem):
    audit=assert_audit_current(stem)
    path=word_path(stem);doc=Document(path)
    rendered=render_path(stem)
    record=json.loads((WORK/stem/'render.json').read_text())
    if record!={'word_sha256':sha(path),'pdf_sha256':sha(rendered)}:
        raise ValueError(f'{stem}: preview is stale; render the current Word first')
    pdf=fitz.open(rendered)
    wanted=''.join(''.join(p['texts'])+''.join(c['text'] for t in p['tables'] for c in t['cells']) for p in audit['pages'])
    actual=''.join(doc.element.xpath('.//w:t/text()'))
    counts={'source_pages':len(audit['pages']),'rendered_pages':len(pdf),'editable_characters':len(norm(actual)),
        'tables':len(doc.tables),'retained_regions':sum(len(p['regions']) for p in audit['pages']),
        'pua':[c for c in set(actual) if 0xe000<=ord(c)<=0xf8ff],
        'missing_in_docx':dict(Counter(norm(wanted))-Counter(norm(actual))),
        'render_missing':dict(Counter(norm(actual))-Counter(norm(''.join(p.get_text() for p in pdf))))}
    counts['out_of_bounds']=[]
    counts['page_text_missing']=[]
    counts['text_out_of_bounds']=[]
    for i,p in enumerate(pdf):
        if i<len(audit['pages']):
            a=audit['pages'][i]
            expected=''.join(a['texts'])+''.join(c['text'] for t in a['tables'] for c in t['cells'])
            missing=Counter(norm(expected))-Counter(norm(p.get_text()))
            if missing:counts['page_text_missing'].append({'page':i+1,'missing':dict(missing)})
        for word in p.get_text('words'):
            if word[0]<-1 or word[1]<-1 or word[2]>p.rect.width+1 or word[3]>p.rect.height+1:
                counts['text_out_of_bounds'].append({'page':i+1,'text':word[4],'bbox':list(word[:4])})
        for im in p.get_image_info():
            b=im['bbox']
            if b[0]<-1 or b[1]<-1 or b[2]>p.rect.width+1 or b[3]>p.rect.height+1:counts['out_of_bounds'].append({'page':i+1,'image':b})
    if not VALIDATOR.is_file():raise FileNotFoundError(f'DOCX validator missing: {VALIDATOR}; set DOCX_VALIDATOR to the installed skill script')
    result=subprocess.run([sys.executable,str(VALIDATOR),str(path)],capture_output=True,text=True)
    counts['xsd_pass']=result.returncode==0
    counts['passed']=counts['source_pages']==counts['rendered_pages'] and counts['xsd_pass'] and not any(counts[k] for k in ['pua','missing_in_docx','render_missing','out_of_bounds','page_text_missing','text_out_of_bounds'])
    counts.update(source_sha256=audit['sha256'],word_sha256=sha(path),preview_sha256=sha(rendered))
    (WORK/stem/'validation.log').write_text(result.stdout+result.stderr)
    (WORK/stem/'checks.json').write_text(json.dumps(counts,ensure_ascii=False,indent=2))
    for start in range(0,len(pdf),12):
        count=min(12,len(pdf)-start);sheet=Image.new('RGB',(1600,470*((count+3)//4)),'#ddd');draw=ImageDraw.Draw(sheet)
        for i in range(count):
            p=pdf[start+i];pix=p.get_pixmap(matrix=fitz.Matrix(.65,.65));im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
            im.thumbnail((385,442));x=i%4*400+8;y=i//4*470+22
            sheet.paste(im,(x,y));draw.text((x,y-17),str(start+i+1),fill='black')
        sheet.save(WORK/stem/f'output-contact-{start+1:03}.jpg')
    print(stem,json.dumps(counts,ensure_ascii=False),flush=True)
    return counts

if __name__=='__main__':
    for arg in sys.argv[1:]:check(Path(arg).stem)
