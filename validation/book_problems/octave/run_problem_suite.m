function run_problem_suite(repo_root, outdir)
  if nargin < 1, repo_root = pwd; end
  if nargin < 2, outdir = fullfile(repo_root,'validation','reports','book_problems'); end
  problem_dir = fullfile(repo_root,'reference','drm_problem_scripts');
  v2_dir = fullfile(repo_root,'reference','matlab_v2');
  plot_stub_dir = fullfile(repo_root,'validation','book_problems','octave','plot_stubs');
  if exist(outdir,'dir') ~= 7, mkdir(outdir); end
  capture_dir=fullfile(outdir,'workspaces'); if exist(capture_dir,'dir') ~= 7, mkdir(capture_dir); end
  addpath(problem_dir); addpath(v2_dir); addpath(plot_stub_dir);
  try, graphics_toolkit('gnuplot'); catch, end
  set(0,'defaultfigurevisible','off');
  files=dir(fullfile(problem_dir,'Problem_*.m')); [~,ix]=sort({files.name}); files=files(ix);
  fid=fopen(fullfile(outdir,'octave_runtime.csv'),'w'); fprintf(fid,'problem,status,identifier,message,elapsed_s\n');
  nfail=0;
  for k=1:numel(files)
    name=files(k).name; path=fullfile(problem_dir,name); t0=tic;
    try
      evalin('base','clear variables; close all;'); evalin('base',"set(0,'defaultfigurevisible','off');");
      if strcmp(name,'Problem_02_17.m'), evalin('base','Problem_02_17();');
      else, evalin('base',sprintf("run('%s');",strrep(path,"'","''"))); end
      cap=fullfile(capture_dir,[name(1:end-2) '.mat']);
      evalin('base',sprintf("save('-mat7-binary','%s');",strrep(cap,"'","''")));
      status='PASS';ident='';msg='';
    catch err
      status='FAIL';ident=err.identifier;msg=err.message;nfail=nfail+1;
    end
    msg=strrep(strrep(msg,sprintf('\n'),' '),',',';');ident=strrep(ident,',',';');
    fprintf(fid,'%s,%s,%s,%s,%.9g\n',name,status,ident,msg,toc(t0));fprintf('%s %s\n',status,name);
  end
  fclose(fid);sfid=fopen(fullfile(outdir,'octave_summary.txt'),'w');fprintf(sfid,'engine=GNU Octave\nversion=%s\nproblem_count=%d\nfail=%d\n',version,numel(files),nfail);fclose(sfid);
  if nfail ~= 0,error('G14:OctaveProblemFailures','%d book problem scripts failed',nfail);end
end
