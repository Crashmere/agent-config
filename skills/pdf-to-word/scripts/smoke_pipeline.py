"""Exercise the pipeline with synthetic pages; no real documents or artifacts remain."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import argparse
import shutil
from pathlib import Path
import pymupdf as fitz
from docx import Document
from docx.oxml.ns import qn

PROJECT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(PROJECT/'scripts'))
from batch_layout import route
from word_math import append_equation, text, fraction, subscript, superscript
from pipeline_config import VALIDATOR

def invoke(script,*args,env,success=True):
    result=subprocess.run([sys.executable,str(PROJECT/'scripts'/script),*args],env=env,capture_output=True,text=True)
    if (result.returncode==0)!=success:
        raise AssertionError(result.stdout+'\n'+result.stderr)
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--with-vision',action='store_true',help='Compile and exercise Apple Vision on macOS')
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='pdf-word-smoke-') as tmp:
        workspace=Path(tmp);(workspace/'input').mkdir();(workspace/'config').mkdir()
        doc=fitz.open()
        cover=doc.new_page(width=595.276,height=841.89)
        cover.insert_text((70,150),'Synthetic document for local pipeline verification.',fontsize=16)
        page=doc.new_page(width=595.276,height=841.89)
        page.insert_text((60,110),'Editable text and numeric table. No source document content is used.',fontsize=11)
        for y in [200,230,260,290]:page.draw_line((60,y),(420,y))
        for x in [60,240,420]:page.draw_line((x,200),(x,290))
        for y,left,right in [(220,'Item','Value'),(250,'Alpha','12.50'),(280,'Beta','0.25')]:
            page.insert_text((70,y),left,fontsize=11);page.insert_text((250,y),right,fontsize=11)
        raster=fitz.open();scan=raster.new_page(width=595.276,height=841.89)
        scan.insert_text((70,130),'Synthetic scanned paragraph for local OCR verification.',fontsize=16)
        scan.insert_text((70,170),'Reference value 123.45 mL, sample 2.',fontsize=16)
        scan.insert_text((70,220),'这是临时生成的中文识别测试。',fontname='china-s',fontsize=16)
        png=scan.get_pixmap(matrix=fitz.Matrix(3,3),alpha=False).tobytes('png')
        page=doc.new_page(width=595.276,height=841.89);page.insert_image(page.rect,stream=png)
        doc.new_page(width=595.276,height=841.89)
        source=workspace/'input/synthetic.pdf';doc.save(source);doc.close()
        with fitz.open(source) as pdf:assert route(pdf)==['native','native','ocr','native']
        digest=hashlib.sha256(source.read_bytes()).hexdigest()
        (workspace/'config/overrides.json').write_text(json.dumps({'synthetic':{'source_sha256':digest,'cover_image':True}}))
        env=os.environ.copy();env.update(PDF_WORD_WORKSPACE=str(workspace),PYTHONDONTWRITEBYTECODE='1')
        invoke('convert_batch.py','all',env=env)
        invoke('batch_coverage.py',env=env)
        audit=json.loads((workspace/'work/batch/synthetic/audit.json').read_text())
        checks=json.loads((workspace/'work/batch/synthetic/checks.json').read_text())
        coverage=json.loads((workspace/'work/batch/synthetic/coverage.json').read_text())
        assert checks['passed'] and checks['source_pages']==4 and checks['tables']==1
        assert coverage['passed'] and coverage['table_cells_checked']==6
        assert '123.45' in ''.join(audit['pages'][2]['texts'])
        if args.with_vision:
            if sys.platform!='darwin' or not shutil.which('swiftc'):
                raise RuntimeError('--with-vision requires macOS and swiftc')
            binary=workspace/'vision_ocr'
            subprocess.run(['swiftc',str(PROJECT/'scripts/vision_ocr.swift'),'-o',str(binary)],check=True,capture_output=True)
            image=workspace/'work/batch/synthetic/page-003.png'
            subprocess.run([str(binary),str(image)],env=env,check=True,capture_output=True)
            invoke('batch_scan_review.py','synthetic',env=env)
        invoke('package_results.py',env=env)
        packaged=json.loads((workspace/'output/quality-report.json').read_text())
        assert packaged['files'][0]['manual_review']=={'status':'not_recorded'}
        # A changed source must not reuse the existing OCR cache or crop settings.
        source.write_bytes(source.read_bytes()+b'\n')
        rejected=invoke('convert_batch.py','prepare','synthetic',env=env,success=False)
        assert 'source SHA-256' in rejected.stderr
        # Test reusable editable formula helpers using unrelated synthetic math.
        word=Document();word.settings.element.find(qn('w:zoom')).set(qn('w:percent'),'100');p=word.add_paragraph()
        append_equation(p,[subscript('x','i'),' = ',fraction([text('1')],[superscript('y','2')])])
        formula=workspace/'formula.docx';word.save(formula)
        result=subprocess.run([sys.executable,str(VALIDATOR),str(formula)],capture_output=True,text=True)
        assert result.returncode==0,result.stdout+result.stderr
        print('PASS: native text, editable table, local OCR, blank page, render, XSD, coverage, package, source hash guard, editable formula.')
        print('Vision comparison: '+('PASS' if args.with_vision else 'not requested'))
    print('Temporary PDFs, Word files, OCR results and previews removed.')

if __name__=='__main__':main()
