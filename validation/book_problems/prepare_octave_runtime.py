from __future__ import annotations
import argparse,json,re,shutil
from pathlib import Path

TRACE_FUNCTIONS=("chr_root","crit_spd","freq_rsp","chr_asym","whirl")

WRAPPERS={
"chr_root":"""function varargout = chr_root(model,Rotor_Spd)
 nout=max(nargout,1); tmp=cell(1,nout); [tmp{:}]=authority_chr_root(model,Rotor_Spd);
 trace_file=drm_trace_file('chr_root'); nargout_requested=nargout;
 save('-mat7-binary',trace_file,'model','Rotor_Spd','nargout_requested','tmp');
 if nargout>0,varargout=tmp(1:nargout);else,varargout={};end
end
""",
"freq_rsp":"""function varargout = freq_rsp(model,Rotor_Spd)
 nout=max(nargout,1); tmp=cell(1,nout); [tmp{:}]=authority_freq_rsp(model,Rotor_Spd);
 trace_file=drm_trace_file('freq_rsp'); nargout_requested=nargout;
 save('-mat7-binary',trace_file,'model','Rotor_Spd','nargout_requested','tmp');
 if nargout>0,varargout=tmp(1:nargout);else,varargout={};end
end
""",
"chr_asym":"""function varargout = chr_asym(model,Rotor_Spd)
 nout=max(nargout,1); tmp=cell(1,nout); [tmp{:}]=authority_chr_asym(model,Rotor_Spd);
 trace_file=drm_trace_file('chr_asym'); nargout_requested=nargout;
 save('-mat7-binary',trace_file,'model','Rotor_Spd','nargout_requested','tmp');
 if nargout>0,varargout=tmp(1:nargout);else,varargout={};end
end
""",
"whirl":"""function varargout = whirl(u,v)
 nout=max(nargout,1); tmp=cell(1,nout); [tmp{:}]=authority_whirl(u,v);
 trace_file=drm_trace_file('whirl'); nargout_requested=nargout;
 save('-mat7-binary',trace_file,'u','v','nargout_requested','tmp');
 if nargout>0,varargout=tmp(1:nargout);else,varargout={};end
end
""",
"crit_spd":"""function varargout = crit_spd(varargin)
 nout=max(nargout,1); tmp=cell(1,nout); [tmp{:}]=authority_crit_spd(varargin{:});
 trace_file=drm_trace_file('crit_spd'); nargout_requested=nargout; nargin_requested=nargin; model=varargin{1};
 NX=[];damped_NF=[];number_criticals=[];max_iterations=[];convergence_tol=[];initial_estimates=[];
 if nargin>=2,NX=varargin{2};end;if nargin>=3,damped_NF=varargin{3};end;if nargin>=4,number_criticals=varargin{4};end
 if nargin>=5,max_iterations=varargin{5};end;if nargin>=6,convergence_tol=varargin{6};end;if nargin>=7,initial_estimates=varargin{7};end
 save('-mat7-binary',trace_file,'model','NX','damped_NF','number_criticals','max_iterations','convergence_tol','initial_estimates','nargin_requested','nargout_requested','tmp');
 if nargout>0,varargout=tmp(1:nargout);else,varargout={};end
end
"""}

TRACE_HELPER="""function path = drm_trace_file(kind)
 persistent counters;if isempty(counters),counters=struct();end
 if ~isfield(counters,kind),counters.(kind)=0;end;counters.(kind)=counters.(kind)+1;
 trace_dir=getenv('DRM_TRACE_DIR');problem=getenv('DRM_TRACE_PROBLEM');
 if isempty(trace_dir),trace_dir='.';end;if isempty(problem),problem='UNKNOWN';end
 if exist(trace_dir,'dir')~=7,mkdir(trace_dir);end
 path=fullfile(trace_dir,sprintf('%s__%03d__%s.mat',problem,counters.(kind),kind));
end
"""

RUNNER="""function run_book_problem_suite(problem_dir,trace_dir,status_file)
 inv=jsondecode(fileread(fullfile(problem_dir,'inventory_runtime.json')));problems=inv.problems;
 fid=fopen(status_file,'w');fprintf(fid,'problem,status,message\\n');fclose(fid);set(0,'defaultfigurevisible','off');
 for i=1:numel(problems)
  name=problems(i).problem;setenv('DRM_TRACE_PROBLEM',name);setenv('DRM_TRACE_DIR',trace_dir);
  status='PASS';msg='';
  try,run_book_problem(fullfile(problem_dir,[name '.m']));catch err,status='FAIL';msg=strrep(strrep(err.message,sprintf('\\n'),' '),',',';');end
  fid=fopen(status_file,'a');fprintf(fid,'%s,%s,%s\\n',name,status,msg);fclose(fid);close all;
 end
end
function run_book_problem(script_path),run(script_path);end
"""

def rename_function(text,old,new):
 p=re.compile(r"(^\s*function\b[^\n=]*=\s*)"+re.escape(old)+r"(\s*\()",re.M);out,n=p.subn(r"\1"+new+r"\2",text,count=1)
 if n==0:
  p=re.compile(r"(^\s*function\s+)"+re.escape(old)+r"(\s*\()",re.M);out,n=p.subn(r"\1"+new+r"\2",text,count=1)
 if n!=1:raise RuntimeError(f"could not rename function {old}")
 return out

def sanitize(text):
 return "\n".join("% harness-disabled: "+ln if re.match(r"^\s*(clear|close\s+all)\s*;?\s*$",ln,re.I) else ln for ln in text.splitlines())+"\n"

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--software-dir',required=True);ap.add_argument('--problem-dir',required=True);ap.add_argument('--inventory',required=True);ap.add_argument('--runtime-dir',required=True);a=ap.parse_args()
 software=Path(a.software_dir);problems=Path(a.problem_dir);runtime=Path(a.runtime_dir);wrappers=runtime/'wrappers';sanitized=runtime/'problems'
 shutil.rmtree(runtime,ignore_errors=True);wrappers.mkdir(parents=True);sanitized.mkdir(parents=True);inv=json.loads(Path(a.inventory).read_text())
 (sanitized/'inventory_runtime.json').write_text(json.dumps({'problems':[{'problem':p['problem']} for p in inv['problems']]}))
 for fn in TRACE_FUNCTIONS:
  src=(software/f'{fn}.m').read_text(errors='replace');(wrappers/f'authority_{fn}.m').write_text(rename_function(src,fn,f'authority_{fn}'));(wrappers/f'{fn}.m').write_text(WRAPPERS[fn])
 (wrappers/'drm_trace_file.m').write_text(TRACE_HELPER);(wrappers/'run_book_problem_suite.m').write_text(RUNNER)
 for e in inv['problems']:
  p=problems/f"{e['problem']}.m";(sanitized/p.name).write_text(sanitize(p.read_text(errors='replace')))
 if (problems/'bnpr.m').exists():shutil.copy2(problems/'bnpr.m',sanitized/'bnpr.m')
 print(json.dumps({'runtime_dir':str(runtime),'problems':len(inv['problems']),'wrappers':list(TRACE_FUNCTIONS)}))
if __name__=='__main__':main()
