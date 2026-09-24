function run_problem_suite(repo_root, outdir, save_workspaces)
  if nargin < 1, repo_root = pwd; end
  if nargin < 2, outdir = fullfile(repo_root,'validation','reports','book_problems','octave_run'); end
  if nargin < 3, save_workspaces = 1; end

  problem_dir = fullfile(repo_root,'reference','drm_problem_scripts');
  v2_dir = fullfile(repo_root,'reference','matlab_v2');
  plot_stub_dir = fullfile(repo_root,'validation','book_problems','octave','plot_stubs');
  if exist(outdir,'dir') ~= 7, mkdir(outdir); end
  stdout_dir = fullfile(outdir,'stdout'); if exist(stdout_dir,'dir') ~= 7, mkdir(stdout_dir); end
  probe_dir = fullfile(outdir,'numeric_probes'); if exist(probe_dir,'dir') ~= 7, mkdir(probe_dir); end
  capture_dir = fullfile(outdir,'workspaces');
  if save_workspaces && exist(capture_dir,'dir') ~= 7, mkdir(capture_dir); end

  addpath(problem_dir); addpath(v2_dir); addpath(plot_stub_dir);
  try, graphics_toolkit('gnuplot'); catch, end
  set(0,'defaultfigurevisible','off');

  product_cases = {'04_06','04_07','04_08','04_12','05_04', ...
                   '05_01','05_02','05_03','05_08','05_09','05_11', ...
                   '06_10','06_11','06_11e','06_12','07_10','07_11', ...
                   '08_11','08_12','08_14'};

  files = dir(fullfile(problem_dir,'Problem_*.m'));
  [~,ix] = sort({files.name}); files = files(ix);
  fid = fopen(fullfile(outdir,'octave_runtime.csv'),'w');
  fprintf(fid,'problem,status,identifier,message,elapsed_s,stdout_truncated\n');
  nfail = 0; npass = 0; nna = 0;

  for k = 1:numel(files)
    name = files(k).name; path = fullfile(problem_dir,name); t0 = tic;
    cid = name(9:end-2); captured = ''; truncated = 0;
    status = 'FAIL'; ident = ''; msg = '';
    try
      evalin('base','clear variables; close all;');
      evalin('base',"set(0,'defaultfigurevisible','off');");
      if strcmp(name,'Problem_02_17.m')
        cmd = 'Problem_02_17();';
      else
        escaped = strrep(path,"'","''");
        cmd = sprintf("run('%s');",escaped);
      end
      captured = evalc("evalin('base',cmd);");

      maxchars = 1000000;
      if length(captured) > maxchars
        captured = captured(1:maxchars); truncated = 1;
      end
      sfid = fopen(fullfile(stdout_dir,[name(1:end-2) '.txt']),'w');
      fprintf(sfid,'%s',captured); fclose(sfid);

      write_numeric_probe(probe_dir, name(1:end-2));

      if save_workspaces && any(strcmp(cid, product_cases))
        cap = fullfile(capture_dir,[name(1:end-2) '.mat']);
        evalin('base',sprintf("save('-mat7-binary','%s');",strrep(cap,"'","''")));
      end
      status = 'PASS'; npass = npass + 1;
    catch err
      msg = err.message; ident = err.identifier;
      if strcmp(name,'Problem_03_12.m') && ~isempty(strfind(msg,'syntax error')) && ~isempty(strfind(msg,'do = 0.060'))
        status = 'NOT_APPLICABLE'; ident = 'OCTAVE_7_1_RESERVED_DO';
        msg = 'Original MATLAB script uses variable name do; GNU Octave 7.1.0 parses do as a keyword. Source-derived B_ANALYTICAL runner is used; no Octave baseline is claimed.';
        nna = nna + 1;
      else
        nfail = nfail + 1;
      end
      sfid = fopen(fullfile(stdout_dir,[name(1:end-2) '.txt']),'w');
      fprintf(sfid,'%s',captured); fclose(sfid);
    end
    msg = strrep(strrep(msg,sprintf('\n'),' '),',',';'); ident = strrep(ident,',',';');
    fprintf(fid,'%s,%s,%s,%s,%.9g,%d\n',name,status,ident,msg,toc(t0),truncated);
    fprintf('%s %s\n',status,name);
  end
  fclose(fid);

  sfid = fopen(fullfile(outdir,'octave_summary.txt'),'w');
  fprintf(sfid,'engine=GNU Octave\nversion=%s\nproblem_count=%d\npass=%d\nnot_applicable=%d\nfail=%d\n',version,numel(files),npass,nna,nfail);
  fclose(sfid);
  if numel(files) ~= 83, error('G14:ProblemCount','expected 83 book problems, found %d',numel(files)); end
  if npass ~= 82 || nna ~= 1 || nfail ~= 0
    error('G14:OctaveProblemFailures','expected 82 PASS + Problem_03_12 NOT_APPLICABLE; observed PASS=%d N/A=%d FAIL=%d',npass,nna,nfail);
  end
end

function write_numeric_probe(probe_dir, stem)
  vars = evalin('base','whos');
  fid = fopen(fullfile(probe_dir,[stem '.csv']),'w');
  fprintf(fid,'name,numel,sum_real,sum_imag,sum_abs,sum_abs2,first_real,first_imag,last_real,last_imag\n');
  for i = 1:numel(vars)
    nm = vars(i).name;
    if vars(i).global, continue; end
    try
      val = evalin('base',nm);
    catch
      continue
    end
    if ~(isnumeric(val) || islogical(val)) || isempty(val), continue; end
    x = val(:); xr = real(x); xi = imag(x);
    if any(~isfinite(xr)) || any(~isfinite(xi)), continue; end
    fprintf(fid,'%s,%d,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g\n', ...
      nm,numel(x),sum(xr),sum(xi),sum(abs(x)),sum(abs(x).^2),xr(1),xi(1),xr(end),xi(end));
  end
  fclose(fid);
end
