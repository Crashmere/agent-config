"""Local Chinese OCR with cached, reviewable bounding-box output."""
from pathlib import Path
import json, sys, time
from rapidocr import RapidOCR, ModelType, OCRVersion
from PIL import Image

from pipeline_config import MODELS, require_external
require_external(MODELS, 'OCR model cache')
engine = RapidOCR(params={
    'Det.ocr_version': OCRVersion.PPOCRV5,
    'Det.model_type': ModelType.SERVER,
    'Rec.ocr_version': OCRVersion.PPOCRV5,
    'Rec.model_type': ModelType.SERVER,
    'Global.model_root_dir': str(MODELS),
    'Global.max_side_len': 3200,
    'Global.use_cls': False,
    'Global.text_score': 0.35,
    'Det.limit_side_len': 1600,
    'Det.limit_type': 'max',
    'EngineConfig.onnxruntime.intra_op_num_threads': 4,
    'EngineConfig.onnxruntime.inter_op_num_threads': 2,
})
for arg in sys.argv[1:]:
    p=Path(arg); out=p.with_suffix('.rapid.json')
    if out.exists(): continue
    start=time.monotonic(); result=engine(str(p))
    w,h=Image.open(p).size
    lines=[]
    if result.txts is not None:
        for box,t,score in zip(result.boxes,result.txts,result.scores):
            x0,y0=box.min(axis=0);x1,y1=box.max(axis=0)
            lines.append({'text':t,'confidence':float(score),'bbox':[float(x0/w),float(y0/h),float(x1/w),float(y1/h)]})
    out.write_text(json.dumps({'source':str(p),'width':w,'height':h,'engine':'RapidOCR PP-OCRv5 server','lines':lines},ensure_ascii=False,indent=2))
    print(f'{p}: {len(lines)} lines, {time.monotonic()-start:.1f}s',flush=True)
