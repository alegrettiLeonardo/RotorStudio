from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

TRACE_FUNCTIONS = ("chr_root", "crit_spd", "freq_rsp", "chr_asym", "whirl")
PLOT_NOOP_NAMES = ("picrotor", "plotcamp", "plotresp", "plotmode", "plot", "semilogy")

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
  inventory_data = jsondecode(fileread(fullfile(problem_dir,'inventory_runtime.json')));
  problems = inventory_data.problems;
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
      captured_output = evalc('run_book_problem(script_path);');
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
  script_text = fileread(script_path);
  eval(script_text);
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

def sanitize_script(text: str, name: str) -> str:
    # Preserve the original script's clear/close semantics now that each problem
    # executes inside its own function workspace. Only apply explicit, documented
    # Octave lexical compatibility substitutions that do not alter mathematics.
    if name == 'Problem_03_12.m':
        # MATLAB permits `do` as an identifier; GNU Octave reserves it for do/until.
        text = re.sub(r"\\bdo\\b", "do_octave", text)
    return text if text.endswith("\\n") else text+"\\n"

