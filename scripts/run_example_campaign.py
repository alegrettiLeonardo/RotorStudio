from __future__ import annotations
import argparse,csv,json,traceback,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from examples.legacy_campaign import run_named
from examples.chapter05.example_05_08_01 import main as ex50801
from examples.chapter06.example_06_06_01 import main as ex60601
from examples.chapter07.example_07_06_01 import main as ex70601
from examples.graphics import render_campaign_graphics

REMAINING=['05_08_03','05_09_01','05_09_02','05_09_03','05_09_04','05_09_05','05_09_06','05_09_07','05_09_09','05_09_10','06_03_01','06_03_02','06_03_03','06_05_01','06_08_01','06_10_01','06_11_01','07_07_01','07_09_01']

def run(outdir,smoke=True,variants=True):
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True);rows=[]
    def rec(example,variant,status,detail=''):
        rows.append({'example':example,'variant':variant,'status':status,'detail':detail})
    for ex,fn,args in [('05_08_01',ex50801,{}),('06_06_01',ex60601,{'case':1,'smoke':True,'outdir':str(out/'example_06_06_01')}),('07_06_01',ex70601,{'case':1,'phase':0.,'smoke':True,'outdir':str(out/'example_07_06_01')})]:
        try:
            if ex=='05_08_01': fn(str(out/'example_05_08_01'))
            else: fn(**args)
            rec(ex,'baseline','PASS_IMPLEMENTED_SCOPE')
        except Exception as e:rec(ex,'baseline','FAIL',repr(e))
    plan=[(n,{}) for n in REMAINING]
    if variants:
        plan += [('06_03_01',{'case':2}),('06_03_02',{'case':2}),('06_03_02',{'case':3}),('06_03_03',{'case':2}),('06_03_03',{'case':3}),('06_05_01',{'case':2}),('06_11_01',{'case':2}),('06_08_01',{'lhcase':1,'rhcase':5}),('06_08_01',{'lhcase':5,'rhcase':1}),('07_07_01',{'lhcase':3,'rhcase':3,'id_case':2}),('07_09_01',{'case':2})]
    for n,kw in plan:
        variant=','.join(f'{k}={v}' for k,v in sorted(kw.items())) or 'default'
        try:
            d=run_named(n,str(out),smoke,**kw);rec(n,variant,d['status'],json.dumps(d,sort_keys=True))
        except Exception as e:
            rec(n,variant,'FAIL',repr(e));traceback.print_exc()
    with (out/'campaign_status.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['example','variant','status','detail']);w.writeheader();w.writerows(rows)
    summary={'runs':len(rows),'pass':sum(r['status'].startswith('PASS') for r in rows),'blocked':sum(r['status'].startswith('BLOCKED') for r in rows),'fail':sum(r['status']=='FAIL' for r in rows),'unique_examples':len(set(r['example'] for r in rows)),'rows':rows}
    (out/'campaign_summary.json').write_text(json.dumps(summary,indent=2))
    graphics=render_campaign_graphics(out)
    print(json.dumps({k:summary[k] for k in ('runs','pass','blocked','fail','unique_examples')},indent=2))
    print(json.dumps({'graphics_complete':graphics['complete_examples'],'graphics_missing':graphics['missing']},indent=2))
    if summary['fail'] or graphics['unique_examples']!=22 or graphics['complete_examples']!=22:
        return 1
    return 0
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--outdir',default='validation/reports/example_campaign_M4');p.add_argument('--full',action='store_true');p.add_argument('--no-variants',action='store_true');a=p.parse_args();raise SystemExit(run(a.outdir,not a.full,not a.no_variants))
