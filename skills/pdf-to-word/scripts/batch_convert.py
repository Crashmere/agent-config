"""Build reviewable hybrid DOCX from cached layout and explicit review overrides.

Text and reliable native tables are editable. Complex regions remain lossless
source crops. No external document conversion service is used.
"""
from pathlib import Path
import json,re,sys,hashlib,copy,math
import pymupdf as fitz
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.section import WD_SECTION_START
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ROW_HEIGHT_RULE, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from batch_layout import ROOT,WORK,normalize,clean,font_maps,native_lines,font_size_scale

from pipeline_config import OUT, source as source_path, profile, sha, word_path

def union(a,b):return [min(a[0],b[0]),min(a[1],b[1]),max(a[2],b[2]),max(a[3],b[3])]
def inside(span,rect):
    r=span['bbox'];x=(r[0]+r[2])/2;y=(r[1]+r[3])/2
    return rect[0]-.5<=x<=rect[2]+.5 and rect[1]-.5<=y<=rect[3]+.5

def font(run,size=10,bold=False,italic=False,sub=False,sup=False):
    run.font.name='Times New Roman';run.font.size=Pt(size);run.bold=bold;run.italic=italic
    run.font.subscript=sub;run.font.superscript=sup
    rf=run._element.get_or_add_rPr().rFonts
    for k,v in [('eastAsia','Heiti SC' if bold else 'Songti SC'),('ascii','Times New Roman'),('hAnsi','Times New Roman')]:rf.set(qn('w:'+k),v)

def setup(doc):
    for n in ['Normal','Header','Footer','Heading 1','Heading 2','Heading 3','Heading 4']:
        s=doc.styles[n];s.font.name='Times New Roman';s.font.size=Pt(10)
        s.font.color.rgb=RGBColor(0,0,0)
        s._element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'Songti SC')
        s.paragraph_format.space_before=Pt(0);s.paragraph_format.space_after=Pt(0)
        s.paragraph_format.keep_with_next=False;s.paragraph_format.keep_together=False
    doc.settings.element.find(qn('w:zoom')).set(qn('w:percent'),'100')
    doc.core_properties.author='';doc.core_properties.comments='正文及可靠文字表格可编辑；封面、复杂公式、扫描表格和低置信区域保留原图。保留范围见转换审计记录。'

def paragraph(doc,before=0,line=12):
    p=doc.add_paragraph();pf=p.paragraph_format
    pf.space_before=Pt(max(0,before));pf.space_after=Pt(0);pf.line_spacing=Pt(max(1,line))
    pf.widow_control=False;pf.keep_together=False;pf.keep_with_next=False
    return p

def anchor_picture(run,x=0,y=0):
    inline=run._r.xpath('.//wp:inline')[0]
    anchor=OxmlElement('wp:anchor')
    for k,v in [('distT','0'),('distB','0'),('distL','0'),('distR','0'),('simplePos','0'),('relativeHeight','0'),('behindDoc','0'),('locked','0'),('layoutInCell','1'),('allowOverlap','1')]:anchor.set(k,v)
    pos=OxmlElement('wp:simplePos');pos.set('x','0');pos.set('y','0');anchor.append(pos)
    for name,offset in [('positionH',x),('positionV',y)]:
        pos=OxmlElement('wp:'+name);pos.set('relativeFrom','page');off=OxmlElement('wp:posOffset');off.text=str(round(offset*12700));pos.append(off);anchor.append(pos)
    anchor.append(copy.deepcopy(inline.find(qn('wp:extent'))));anchor.append(OxmlElement('wp:wrapNone'))
    for name in ['wp:docPr','wp:cNvGraphicFramePr','a:graphic']:anchor.append(copy.deepcopy(inline.find(qn(name))))
    inline.getparent().replace(inline,anchor)

def image_region(doc,pdfpage,rect,folder,index,cursor,left=42):
    scale=pdfpage.rect.width/595.276
    r=fitz.Rect([v*scale for v in rect]) & pdfpage.rect
    path=folder/f'p{index:03}-region-{round(rect[0])}-{round(rect[1])}-{round(rect[3])}.png'
    pix=pdfpage.get_pixmap(matrix=fitz.Matrix(3/scale,3/scale),clip=r,alpha=False)
    pix.save(path)
    w=rect[2]-rect[0];h=rect[3]-rect[1]
    if rect[1]>pdfpage.rect.height/scale-24:
        # Small source footer outside the body area must not force a new page.
        p=paragraph(doc,line=1);run=p.add_run();font(run,size=1)
        run.add_picture(str(path),width=Pt(w),height=Pt(h));anchor_picture(run,rect[0],rect[1])
        return cursor
    p=paragraph(doc,rect[1]-cursor,h+1.5)
    p.paragraph_format.line_spacing=1
    p.paragraph_format.left_indent=Pt(max(0,rect[0]-left))
    run=p.add_run();font(run,size=1);run.add_picture(str(path),width=Pt(w),height=Pt(h))
    # Set description for assistive tools without adding duplicate OCR text.
    run._r.xpath('.//wp:docPr')[0].set('descr',f'原PDF第{index}页保留区域，公式、图示或扫描表格')
    return max(cursor,rect[1])+h+1.5

def text_line(doc,l,cursor,replace=None,body_left=42):
    spans=[s for s in l['spans'] if s['text']]
    if not spans:return cursor,''
    t=l['text']
    for a,b in (replace or {}).items():t=t.replace(a,b)
    sizes=[s['size'] for s in spans if s['text'].strip()]
    size=max(sizes or [10])
    isocr=spans[0]['font']=='OCR'
    if isocr:size=10.5
    else:size=min(size,16)
    # Native Chinese standards are single-column. Retain physical line breaks
    # for accurate cross-page references and predictable editing.
    y=l['bbox'][1];lineh=max(11.2,size*1.17)
    p=paragraph(doc,y-cursor,lineh)
    x=l['bbox'][0]; p.paragraph_format.left_indent=Pt(max(0,x-body_left))
    p.paragraph_format.right_indent=Pt(0)
    bold=any('HT' in s['font'] or 'XBS' in s['font'] or s.get('flags',0)&16 for s in spans)
    is_heading=bool(re.match(r'^(?:[A-Z]\.\d+(?:\.\d+)*|\d+(?:\.\d+)*)\s*[\u4e00-\u9fff]',t)) and len(t)<32 and x<110
    if is_heading:
        m=re.match(r'^([A-Z]?\.?\d+(?:\.\d+)*)',t)
        p.style=doc.styles[f'Heading {min(4,1+m[0].count("."))}'];bold=True
        p.paragraph_format.keep_with_next=False;p.paragraph_format.space_before=Pt(max(0,y-cursor));p.paragraph_format.line_spacing=Pt(lineh)
    width=595.276-42-max(body_left,x)
    if isocr or t!=l['text']:
        # Estimate widths before Word; allow a small amount of compression.
        units=sum(1 if ord(c)>255 else .5 for c in t)
        size=min(size,width/max(units,1)*.99)
        font(p.add_run(t),size=max(6.5,size),bold=bold)
    else:
        main=max(spans,key=lambda s:len(s['text'])*s['size'])
        origin=main.get('origin',[0,0])[1];prev=None
        units=sum((1 if ord(c)>255 else .5) for s in spans for c in s['text'])
        fit=min(1,width/max(1,units*size)*.995)
        for s in spans:
            text=s['text'];gap=s['bbox'][0]-(prev['bbox'][2] if prev else s['bbox'][0])
            if prev and gap>size*.6 and not prev['text'].endswith(' ') and not text.startswith(' '):
                font(p.add_run(' '),size=size*fit)
            sub=s.get('origin',[0,origin])[1]>origin+1.2 and s['size']<main['size']*.9
            sup=s.get('origin',[0,origin])[1]<origin-1.2 and s['size']<main['size']*.9
            font(p.add_run(text),size=(size if sub or sup else min(size,s['size']))*fit,bold=bold,italic=bool(s.get('flags',0)&2),sub=sub,sup=sup)
            prev=s
    return max(cursor,y)+lineh,p.text

def native_table(doc,page,table,mp,cursor,left=42):
    rect=table['bbox'];scale=595.276/page.rect.width
    size_scale=font_size_scale(page)
    source=next(t for t in page.find_tables().tables if abs(t.bbox[1]*scale-rect[1])<1)
    xs=sorted(set(round(c[k]*scale,2) for c in source.cells if c for k in (0,2)))
    ys=sorted(set(round(c[k]*scale,2) for c in source.cells if c for k in (1,3)))
    if rect[1]>cursor:
        paragraph(doc,0,max(.1,rect[1]-cursor))
    tbl=doc.add_table(rows=len(ys)-1,cols=len(xs)-1);tbl.style='Table Grid';tbl.autofit=False
    tbl.alignment=WD_TABLE_ALIGNMENT.LEFT
    pr=tbl._tbl.tblPr
    ind=OxmlElement('w:tblInd');ind.set(qn('w:w'),str(round((rect[0]-left)*20)));ind.set(qn('w:type'),'dxa');pr.insert_element_before(ind,'w:tblBorders','w:shd','w:tblLayout','w:tblCellMar','w:tblLook')
    mar=OxmlElement('w:tblCellMar')
    for k in ['top','left','bottom','right']:
        e=OxmlElement('w:'+k);e.set(qn('w:w'),'8');e.set(qn('w:type'),'dxa');mar.append(e)
    pr.insert_element_before(mar,'w:tblLook','w:tblCaption','w:tblDescription')
    for j,col in enumerate(tbl.columns):col.width=Pt(xs[j+1]-xs[j])
    for i,row in enumerate(tbl.rows):
        row.height=Pt(ys[i+1]-ys[i]);row.height_rule=WD_ROW_HEIGHT_RULE.AT_LEAST
        for j,c in enumerate(row.cells):c.width=Pt(xs[j+1]-xs[j])
    raw=[]
    for b in page.get_text('rawdict')['blocks']:
        if b['type']!=0:continue
        for l in b['lines']:
            for s in l['spans']:
                for c in s['chars']:
                    origin=c['origin'];bb=c['bbox']
                    raw.append({'text':clean(c['c'],s['font'],mp),'x':(bb[0]+bb[2])/2*scale,'y':(origin[1]-s['size']*size_scale*.3)*scale,
                        'origin':origin[1]*scale,'size':s['size']*scale*size_scale,'font':s['font']})
    audit=[]
    for cellrect in source.cells:
        if not cellrect:continue
        cr=[v*scale for v in cellrect]
        j0=min(range(len(xs)),key=lambda j:abs(xs[j]-cr[0]));j1=min(range(len(xs)),key=lambda j:abs(xs[j]-cr[2]))
        i0=min(range(len(ys)),key=lambda i:abs(ys[i]-cr[1]));i1=min(range(len(ys)),key=lambda i:abs(ys[i]-cr[3]))
        cell=tbl.cell(i0,j0)
        if i1>i0+1 or j1>j0+1:cell=cell.merge(tbl.cell(i1-1,j1-1))
        cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
        chars=[c for c in raw if cr[0]<=c['x']<cr[2] and cr[1]<=c['y']<cr[3]]
        # Group baselines, including small sub/superscript characters.
        groups=[]
        for c in sorted(chars,key=lambda c:(c['y'],c['x'])):
            g=next((g for g in groups if abs(g[0]['y']-c['y'])<max(3,c['size']*.45)),None)
            if g is None:groups.append([c])
            else:g.append(c)
        groups.sort(key=lambda g:sum(c['y'] for c in g)/len(g))
        celltexts=[]
        for k,g in enumerate(groups):
            g.sort(key=lambda c:c['x']);p=cell.paragraphs[0] if k==0 else cell.add_paragraph()
            p.paragraph_format.space_after=Pt(0);p.paragraph_format.space_before=Pt(0)
            size=min(9,max(c['size'] for c in g));text=''.join(c['text'] for c in g).strip()
            units=sum(1 if ord(c)>255 else .5 for c in text)
            size=min(size,(cr[2]-cr[0]-2)/max(1,units))
            p.paragraph_format.line_spacing=Pt(max(6,size*1.15));p.paragraph_format.widow_control=False
            p.alignment=WD_ALIGN_PARAGRAPH.CENTER if len(xs)>5 or j0==0 else WD_ALIGN_PARAGRAPH.LEFT
            base=max(g,key=lambda c:c['size'])['origin']
            for c in g:
                is_small=c['size']<max(cc['size'] for cc in g)*.85
                font(p.add_run(c['text']),size=max(5.5,size if is_small else min(size,c['size'])),bold=i0==0,
                    sub=is_small and c['origin']>base+1,sup=is_small and c['origin']<base-1)
            celltexts.append(text)
        audit.append({'bbox':cr,'text':'\n'.join(celltexts),'row':i0,'col':j0})
    return max(cursor,rect[1])+rect[3]-rect[1],audit

def merge_regions(regions):
    out=[]
    for r in sorted(regions,key=lambda r:r[1]):
        if out and r[1]<=out[-1][3]+1 and min(r[2],out[-1][2])>max(r[0],out[-1][0]):out[-1]=union(r,out[-1])
        else:out.append(list(r))
    return out

def build(stem):
    data=json.loads((WORK/stem/'layout.json').read_text());ov=profile(stem)
    source=source_path(stem)
    if data.get('source_sha256')!=sha(source):
        raise ValueError(f'{stem}: stale layout; prepare the current source first')
    pdf=fitz.open(source);maps=font_maps(pdf)
    OUT.mkdir(parents=True,exist_ok=True)
    doc=Document();setup(doc);doc.core_properties.title=stem+' PDF转换';folder=WORK/stem/'assets';folder.mkdir(exist_ok=True)
    audit={'source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'pages':[]}
    for idx,page in enumerate(data['pages']):
        height=page['height'];i=idx+1
        if idx:
            sec=doc.add_section(WD_SECTION_START.NEW_PAGE)
            # Section-break paragraph should not create a visible extra line.
            pp=doc.paragraphs[-1];pp.paragraph_format.line_spacing=Pt(1);pp.paragraph_format.space_after=Pt(0)
            pp.paragraph_format.space_before=Pt(0);font(pp.add_run(''),size=1)
        else:sec=doc.sections[0]
        sec.page_width=Pt(595.276);sec.page_height=Pt(height)
        sec.left_margin=sec.right_margin=Pt(42);sec.top_margin=Pt(20);sec.bottom_margin=Pt(18)
        sec.header_distance=sec.footer_distance=Pt(5)
        full_image=(i==1 and ov.get('cover_image',True)) or i in ov.get('full_image_pages',[])
        item={'page':i,'method':page['method'],'regions':[],'tables':[],'texts':[]}
        if full_image:
            # Page image extends into margins, using an inline image at 0 margin.
            sec.left_margin=sec.right_margin=sec.top_margin=Pt(0);sec.bottom_margin=Pt(1)
            image_region(doc,pdf[idx],[0,0,595.276,height],folder,i,0,left=0)
            pp=doc.paragraphs[-1];pp.paragraph_format.line_spacing=Pt(1)
            inline=pp._p.xpath('.//wp:inline')[0]
            anchor=OxmlElement('wp:anchor')
            for k,v in [('distT','0'),('distB','0'),('distL','0'),('distR','0'),('simplePos','0'),('relativeHeight','0'),('behindDoc','0'),('locked','0'),('layoutInCell','1'),('allowOverlap','1')]:anchor.set(k,v)
            pos=OxmlElement('wp:simplePos');pos.set('x','0');pos.set('y','0');anchor.append(pos)
            for name in ['positionH','positionV']:
                pos=OxmlElement('wp:'+name);pos.set('relativeFrom','page');off=OxmlElement('wp:posOffset');off.text='0';pos.append(off);anchor.append(pos)
            anchor.append(copy.deepcopy(inline.find(qn('wp:extent'))));anchor.append(OxmlElement('wp:wrapNone'))
            for name in ['wp:docPr','wp:cNvGraphicFramePr','a:graphic']:anchor.append(copy.deepcopy(inline.find(qn(name))))
            inline.getparent().replace(inline,anchor)
            item['method']='source-page-image';item['regions']=[[0,0,595.276,height]]
            audit['pages'].append(item);continue
        regions=[list(r) for r in ov.get('regions',{}).get(str(i),[])]
        regions+=page['scan_tables'] if page['method']=='ocr' else page['images']
        if page['method']=='native':
            for l in page['lines']:
                if any(0xe000<=ord(c)<=0xf8ff for c in l['text']):
                    r=l['bbox'];regions.append([max(40,r[0]-2),r[1]-2,min(555,r[2]+2),r[3]+2])
        if page['method']=='ocr':
            for l in page['lines']:
                # Complex scientific typography or damaged recognition is safer
                # as a source region than as plausible but incorrect plain text.
                if (l.get('confidence',1)<.90 or re.search(r'[$_{}]',l['text'])) and l['bbox'][1]>90:
                    r=l['bbox']
                    if r[0]<555:regions.append([max(40,r[0]-3),max(20,r[1]-2),min(555,r[2]+3),r[3]+2])
        regions=merge_regions(regions)
        # Any text removed from the editable layer must be fully inside its
        # retained image. Expand to complete spans, never crop trailing glyphs.
        for r in regions:
            for l in page['lines']:
                for s in l['spans']:
                    if inside(s,r):
                        b=s['bbox'];r[:]=union(r,[b[0]-2,b[1]-1,b[2]+2,b[3]+1])
            r[0]=max(0,r[0]);r[2]=min(595.276,r[2]);r[1]=max(0,r[1]);r[3]=min(height,r[3])
        regions=merge_regions(regions)
        tables=[t for t in page['tables'] if not any(inside({'bbox':t['bbox']},r) for r in regions)]
        exclude=regions+[t['bbox'] for t in tables]
        events=[]
        for l in page['lines']:
            if l['bbox'][1]>height-18 or l['bbox'][0]>565:continue
            spans=[s for s in l['spans'] if not any(inside(s,r) for r in exclude)]
            if not spans:continue
            n=copy.deepcopy(l);n['spans']=spans
            n['text']=(' ' if page['method']=='ocr' else '').join(s['text'] for s in spans).strip()
            if not n['text']:continue
            # Broken title fonts beyond the cover are retained exactly as seen.
            if any(s['font'].startswith('FzBookMaker') for s in spans):
                r=n['bbox'];regions.append([max(40,r[0]-2),r[1]-2,min(555,r[2]+2),r[3]+2]);continue
            events.append((n['bbox'][1],'text',n))
        events += [(r[1],'image',r) for r in regions]
        events += [(t['bbox'][1],'table',t) for t in tables]
        events.sort(key=lambda e:e[0]);cursor=20
        if not events:paragraph(doc,line=1)
        for y,kind,el in events:
            if kind=='image':cursor=image_region(doc,pdf[idx],el,folder,i,cursor);item['regions'].append(el)
            elif kind=='table':
                cursor,cs=native_table(doc,pdf[idx],el,maps,cursor);item['tables'].append({'bbox':el['bbox'],'cells':cs})
            else:
                cursor,t=text_line(doc,el,cursor,ov.get('replace'));item['texts'].append(t)
                item.setdefault('text_boxes',[]).append(el['bbox'])
        item['estimated_bottom']=cursor;audit['pages'].append(item)
    out=word_path(stem);doc.save(out)
    audit['word_sha256']=sha(out)
    (WORK/stem/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
    print(f'{out.name}: {len(pdf)} source pages, {sum(len(p["tables"]) for p in audit["pages"])} editable tables, {sum(len(p["regions"]) for p in audit["pages"])} retained regions',flush=True)

if __name__=='__main__':
    for arg in sys.argv[1:]:build(Path(arg).stem)
