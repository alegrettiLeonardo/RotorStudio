from examples.legacy_campaign import run_named
import argparse
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--full",action="store_true");p.add_argument("--outdir",default="example_campaign_out");p.add_argument("--case",type=int,default=1);p.add_argument("--lhcase",type=int,default=4);p.add_argument("--rhcase",type=int,default=4);p.add_argument("--id-case",type=int,default=1);a=p.parse_args();kw={}
    if "05_09_05" in ("06_03_01","06_03_02","06_03_03","06_05_01","07_09_01"):kw["case"]=a.case
    if "05_09_05"=="06_08_01":kw.update(lhcase=a.lhcase,rhcase=a.rhcase)
    if "05_09_05"=="07_07_01":kw.update(lhcase=a.lhcase,rhcase=a.rhcase,id_case=a.id_case)
    print(run_named("05_09_05",a.outdir,not a.full,**kw))
