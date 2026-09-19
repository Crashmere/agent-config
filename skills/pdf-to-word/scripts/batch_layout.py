"""Reusable PDF layout extraction. Coordinates normalized to an A4-width page.

Automatic extraction is deliberately separated from review overrides. An OCR
score is a routing signal, not a proof of accuracy. Source PDFs are read only.
"""
from pathlib import Path
import re, json
import pymupdf as fitz
import numpy as np
import cv2

from pipeline_config import ROOT, WORK, source

def route(pdf):
    """Initial routing only; plausible but corrupt text still needs review."""
    methods=[]
    for page in pdf:
        text=page.get_text();n=len(text.strip())
        bad=sum(c=='�' or 0xe000<=ord(c)<=0xf8ff for c in text)
        blank=n==0 and not page.get_images() and not page.get_drawings()
        methods.append('native' if blank or (n>=40 and bad/max(1,n)<.03) else 'ocr')
    return methods

def normalize(t):
    return ''.join(chr(ord(c)-0xfee0) if 0xff01<=ord(c)<=0xff5e else c for c in t).replace('　',' ').replace('','-')

def font_maps(pdf):
    maps={}
    for page in pdf:
        for f in page.get_fonts():
            if not f[3].startswith('E-'):continue
            m=re.search(r'/ToUnicode (\d+)',pdf.xref_object(f[0])); mp={}
            if m:
                data=pdf.xref_stream(int(m[1])).decode(errors='replace')
                for a,b,c in re.findall(r'<([0-9a-f]+)>\s*<([0-9a-f]+)>\s*<([0-9a-f]+)>',data,re.I):
                    if a==b and 0x7280<=int(c,16)<=0x72ff and 0x42<=int(a,16)<=0x7b:
                        mp[chr(int(c,16))]=chr(int(a,16)-1)
            maps.setdefault(f[3],{}).update(mp)
            maps.setdefault(f[3].replace('-Identity-H',''),{}).update(mp)
    return maps

def clean(t,font,maps):
    mp=maps.get(font,{})
    return normalize(''.join(mp.get(c,c) for c in t))

def font_size_scale(page):
    ratios=[]
    for b in page.get_text('dict')['blocks']:
        if b['type']!=0:continue
        for l in b['lines']:
            for s in l['spans']:
                t=s['text'].strip()
                if len(t)>=4 and all('\u4e00'<=c<='\u9fff' for c in t):
                    ratios.append((s['bbox'][2]-s['bbox'][0])/len(t)/s['size'])
    ratio=float(np.median(ratios)) if ratios else 1
    return ratio/1.08 if ratio<.75 else 1

def native_lines(page,maps):
    scale=595.276/page.rect.width
    size_scale=font_size_scale(page)
    lines=[]
    for b in page.get_text('dict')['blocks']:
        if b['type']!=0:continue
        for l in b['lines']:
            spans=[]
            for s in l['spans']:
                r=[v*scale for v in s['bbox']]
                r[1]=(s['origin'][1]-s['size']*size_scale*.86)*scale
                r[3]=(s['origin'][1]+s['size']*size_scale*.18)*scale
                spans.append({'text':clean(s['text'],s['font'],maps),'bbox':r,
                    'size':s['size']*scale*size_scale,'font':s['font'],'flags':s['flags'],'origin':[v*scale for v in s['origin']]})
            if spans:lines.append({'bbox':[min(s['bbox'][0] for s in spans),min(s['bbox'][1] for s in spans),max(s['bbox'][2] for s in spans),max(s['bbox'][3] for s in spans)],'spans':spans})
    # PDF often emits superscripts, Latin and Chinese on separate lines.
    groups=[]
    for l in sorted(lines,key=lambda l:(l['bbox'][1],l['bbox'][0])):
        r=l['bbox'];cy=(r[1]+r[3])/2
        match=None
        for g in reversed(groups[-6:]):
            b=g['bbox']; overlap=min(r[3],b[3])-max(r[1],b[1])
            if overlap>min(r[3]-r[1],b[3]-b[1])*.55 and abs(cy-(b[1]+b[3])/2)<7:
                match=g;break
        if match is None:groups.append(l)
        else:
            match['spans']+=l['spans'];match['bbox']=[min(r[0],b[0]),min(r[1],b[1]),max(r[2],b[2]),max(r[3],b[3])]
    for g in groups:
        g['spans'].sort(key=lambda s:s['bbox'][0]); g['text']=''.join(s['text'] for s in g['spans']).strip()
    return sorted(groups,key=lambda l:(l['bbox'][1],l['bbox'][0]))

def ocr_lines(stem,page_index,height):
    path=WORK/stem/f'page-{page_index+1:03}.rapid.json'
    d=json.loads(path.read_text());lines=[]
    for l in d['lines']:
        x0,y0,x1,y1=l['bbox'];r=[x0*595.276,y0*height,x1*595.276,y1*height]
        t=normalize(l['text']);size=min(20,max(6,(r[3]-r[1])*.85))
        lines.append({'text':t,'bbox':r,'confidence':l['confidence'],'spans':[{'text':t,'bbox':r,'size':size,'font':'OCR','flags':0}]})
    groups=[]
    for l in sorted(lines,key=lambda a:(a['bbox'][1],a['bbox'][0])):
        r=l['bbox'];cy=(r[1]+r[3])/2
        g=next((g for g in reversed(groups[-5:]) if abs(cy-(g['bbox'][1]+g['bbox'][3])/2)<min(4,(r[3]-r[1])*.3)),None)
        if g is None:groups.append(l)
        else:
            b=g['bbox'];g['spans']+=l['spans'];g['bbox']=[min(r[0],b[0]),min(r[1],b[1]),max(r[2],b[2]),max(r[3],b[3])]
            g['confidence']=min(g['confidence'],l['confidence'])
    for g in groups:
        g['spans'].sort(key=lambda s:s['bbox'][0]);g['text']=' '.join(s['text'] for s in g['spans'])
    return sorted(groups,key=lambda l:(l['bbox'][1],l['bbox'][0]))

def scan_tables(stem,i,height):
    im=cv2.imread(str(WORK/stem/f'page-{i+1:03}.png'),0)
    bw=cv2.threshold(im,170,255,cv2.THRESH_BINARY_INV)[1]
    h,w=im.shape
    hor=cv2.morphologyEx(bw,cv2.MORPH_OPEN,np.ones((1,max(40,w//12)),np.uint8))
    ver=cv2.morphologyEx(bw,cv2.MORPH_OPEN,np.ones((max(40,h//40),1),np.uint8))
    mask=cv2.dilate(hor|ver,np.ones((5,5),np.uint8))
    rects=[]
    for c in cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)[0]:
        x,y,rw,rh=cv2.boundingRect(c)
        if rw>w*.35 and rh>h*.045:
            rects.append([max(20,x/w*595.276-3),max(0,y/h*height-3),min(575,(x+rw)/w*595.276+3),min(height,(y+rh)/h*height+3)])
    return rects

def analyze(stem,page_methods=None):
    pdf=fitz.open(source(stem));mp=font_maps(pdf);pages=[]
    page_methods=page_methods or route(pdf)
    if len(page_methods)!=len(pdf) or any(m not in {'native','ocr'} for m in page_methods):
        raise ValueError('page_methods must contain native/ocr for every source page')
    for i,p in enumerate(pdf):
        scale=595.276/p.rect.width;height=p.rect.height*scale
        scan=page_methods[i]=='ocr'
        lines=ocr_lines(stem,i,height) if scan else native_lines(p,mp)
        tables=[]
        if not scan:
            for t in p.find_tables().tables:
                tables.append({'bbox':[v*scale for v in t.bbox],'rows':t.row_count,'cols':t.col_count,
                    'cells':[[v*scale for v in c] if c else None for c in t.cells]})
        pages.append({'page':i+1,'width':595.276,'height':height,'method':'ocr' if scan else 'native',
            'lines':lines,'tables':tables,'scan_tables':scan_tables(stem,i,height) if scan else [],
            'images':[[v*scale for v in b['bbox']] for b in p.get_image_info()] if not scan else []})
    return {'file':f'{stem}.pdf','pages':pages,'font_maps':mp}

if __name__=='__main__':
    raise SystemExit('Use convert_batch.py prepare to create source-bound layout caches.')
