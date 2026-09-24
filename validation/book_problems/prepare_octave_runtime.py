from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

TRACE_FUNCTIONS = ("chr_root", "crit_spd", "freq_rsp", "chr_asym", "whirl")
PLOT_NOOP_NAMES = ("picrotor", "plotcamp", "plotresp", "plotmode")

WRAPPERS = {
"chr_root": r'''function varargout = chr_root(model,Rotor_Spd)
  nout = max(nargout,1);
  tmp = cell(1,nout);
  [tmp{:}] = authority_chr_root(model,Rotor_Spd);
  trace_file = drm_trace_file('chr_root');
  nargout_requested = nargout;
  save('-mat7-binary', trace_file, 'model', 'Rotor_Spd', 'nargout_requested', 'tmp');
  if nargout>0, varargout = tmp(1:nargout); else, varargout = {}; end
end
''',
"freq_rsp": r'''function varargout = freq_rsp(model,Rotor_Spd)
  nout = max(nargout,1);
  tmp = cell(1,nout);
  [tmp{:}] = authority_freq_rsp(model,Rotor_Spd);
  trace_file = drm_trace_file('freq_rsp');
  nargout_requested = nargout;
  save('-mat7-binary', trace_file, 'model', 'Rotor_Spd', 'nargout_requested', 'tmp');
  if nargout>0, varargout = tmp(1:nargout); else, varargout = {}; end
end
''',
"chr_asym": r'''function varargout = chr_asym(model,Rotor_Spd)
  nout = max(nargout,1);
  tmp = cell(1,nout);
  [tmp{:}] = authority_chr_asym(model,Rotor_Spd);
  trace_file = drm_trace_file('chr_asym');
  nargout_requested = nargout;
  save('-mat7-binary', trace_file, 'model', 'Rotor_Spd', 'nargout_requested', 'tmp');
  if nargout>0, varargout = tmp(1:nargout); else, varargout = {}; end
end
''',
"whirl": r'''function varargout = whirl(u,v)
  nout = max(nargout,1);
  tmp = cell(1,nout);
  [tmp{:}] = authority_whirl(u,v);
  trace_file = drm_trace_file('whirl');
  nargout_requested = nargout;
  save('-mat7-binary', trace_file, 'u', 'v', 'nargout_requested', 'tmp');
  if nargout>0, varargout = tmp(1:nargout); else, varargout = {}; end
end
''',
"crit_spd": r'''function varargout = crit_spd(varargin)
  nout = max(nargout,1);
  tmp = cell(1,nout);
  [tmp{:}] = authority_crit_spd(varargin{:});
  trace_file = drm_trace_file('crit_spd');
  nargout_requested = nargout;
  nargin_requested = nargin;
  model = varargin{1};
  NX=[]; damped_NF=[]; number_criticals=[]; max_iterations=[]; convergence_tol=[]; initial_estimates=[];
  if nargin>=2, NX=varargin{2}; end
  if nargin>=3, damped_NF=varargin{3}; end
  if nargin>=4, number_criticals=varargin{4}; end
  if nargin>=5, max_iterations=varargin{5}; end
  if nargin>=6, convergence_tol=varargin{6}; end
  if nargin>=7, initial_estimates=varargin{7}; end
  save('-mat7-binary', trace_file, 'model', 'NX', 'damped_NF', 'number_criticals', 'max_iterations', 'convergence_tol', 'initial_estimates', 'nargin_requested', 'nargout_requested', 'tmp');
  if nargout>0, varargout = tmp(1:nargout); else, varargout = {}; end
end
'''
}

TRACE_HELPER = r'''function path = drm_trace_file(kind)
  persistent counters;
  if isempty(counters), counters = struct(); end
  if ~isfield(counters,kind), counters.(kind)=0; end
  counters.(kind)=counters.(kind)+1;
  trace_dir = getenv('DRM_TRACE_DIR');
  problem = getenv('DRM_TRACE_PROBLEM');
  if isempty(trace_dir), trace_dir='.'; end
  if isempty(problem), problem='UNKNOWN'; end
  if exist(trace_dir,'dir')~=7, mkdir(trace_dir); end
  path = fullfile(trace_dir, sprintf('%s__%03d__%s.mat', problem, counters.(kind), kind));
end
'''

RUNNER = r'''function run_book_problem_suite(problem_dir, trace_dir, status_file)
  inv = jsondecode(fileread(fullfile(problem_dir,'inventory_runtime.json')));
  problems = inv.problems;
  fid = fopen(status_file,'w');
  fprintf(fid,'problem,status,message\n');
  fclose(fid);
  set(0,'defaultfigurevisible','off');
  for i=1:numel(problems)
    name = problems(i).problem;
    setenv('DRM_TRACE_PROBLEM',name);
    setenv('DRM_TRACE_DIR',trace_dir);
    script_path = fullfile(problem_dir,[name '.m']);
    status='PASS'; msg='';
    try
      run(script_path);
    catch err
      status='FAIL';
      msg=strrep(strrep(err.message, sprintf('\n'),' '),',',';');
    end
    fid=fopen(status_file,'a');
    fprintf(fid,'%s,%s,%s\n',name,status,msg);
    fclose(fid);
    close all;
  end
end

function run_book_problem(script_path)
  run(script_path);
end
'''

def rename_function(text: str, old: str, new: str) -> str:
    pat = re.compile(r"(^\s*function\b[^\n=]*=\s*)" + re.escape(old) + r"(\s*\()", re.M)
    out, n = pat.subn(r"\1" + new + r"\2", text, count=1)
    if n == 0:
        pat = re.compile(r"(^\s*function\s+)" + re.escape(old) + r"(\s*\()", re.M)
        out, n = pat.subn(r"\1" + new + r"\2", text, count=1)
    if n != 1:
        raise RuntimeError(f"could not rename function {old}")
    return out

def sanitize_script(text: str) -> str:
    lines=[]
    for line in text.splitlines():
        if re.match(r"^\s*(clear(?:\s+all)?|clearvars|close(?:\s+all)?)\s*;?\s*$", line, re.I):
            lines.append("% harness-disabled: " + line)
        else:
            lines.append(line)
    return "\n".join(lines)+"\n"

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--software-dir',required=True)
    ap.add_argument('--problem-dir',required=True)
    ap.add_argument('--inventory',required=True)
    ap.add_argument('--runtime-dir',required=True)
    args=ap.parse_args()
    software=Path(args.software_dir);problems=Path(args.problem_dir);runtime=Path(args.runtime_dir)
    wrappers=runtime/'wrappers';sanitized=runtime/'problems'
    shutil.rmtree(runtime,ignore_errors=True);wrappers.mkdir(parents=True);sanitized.mkdir(parents=True)
    inv=json.loads(Path(args.inventory).read_text())
    (sanitized/'inventory_runtime.json').write_text(json.dumps({'problems':[{'problem':p['problem']} for p in inv['problems']]}))
    for fn in TRACE_FUNCTIONS:
        src=(software/f'{fn}.m').read_text(errors='replace')
        (wrappers/f'authority_{fn}.m').write_text(rename_function(src,fn,f'authority_{fn}'))
        (wrappers/f'{fn}.m').write_text(WRAPPERS[fn])
    (wrappers/'drm_trace_file.m').write_text(TRACE_HELPER)
    (wrappers/'run_book_problem_suite.m').write_text(RUNNER)
    for name in PLOT_NOOP_NAMES:
        (wrappers/f'{name}.m').write_text(f"function varargout = {name}(varargin)\nvarargout=cell(1,nargout);\nend\n")
    for entry in inv['problems']:
        p=problems/f"{entry['problem']}.m"
        (sanitized/p.name).write_text(sanitize_script(p.read_text(errors='replace')))
    helper=problems/'bnpr.m'
    if helper.exists():shutil.copy2(helper,sanitized/'bnpr.m')
    print(json.dumps({'runtime_dir':str(runtime),'problems':len(inv['problems']),'wrappers':list(TRACE_FUNCTIONS),'plot_noops':list(PLOT_NOOP_NAMES)}))
    return 0

if __name__=='__main__': raise SystemExit(main())
