function octave_runtime_probe(repo_root,outfile)
  if nargin<1,repo_root=pwd;end
  if nargin<2,outfile=fullfile(repo_root,'validation','reports','LEGACY_RUNTIME_OCTAVE_7_1.json');end
  addpath(fullfile(repo_root,'reference','matlab_v2'));results={};
  results{end+1}=expect_error('shftasym_8arg_default',@()shftasym(11,1,1,1,0,0,1,1),'AxialForce');
  results{end+1}=expect_error('shftasym_nonzero_axial',@()shftasym(11,1,1,1,0,0,1,1,10),'Kre');
  results{end+1}=expect_success('shftasym_zero_axial',@()shftasym(12,1,1,1,0.1,0.1,1,0.01,0));
  model.node=[1 0];model.shaft=zeros(0,11);model.disc=zeros(0,6);model.bearing=[4 1 10 10 20 20 1 1 2 2];
  results{end+1}=bearasym_probe(model);results{end+1}=foundation_predicate_probe();results{end+1}=runup_j_probe();
  payload.engine='GNU Octave';payload.version=version;payload.results=results;payload.overall='PASS';
  for i=1:numel(results),if ~results{i}.pass,payload.overall='FAIL';end,end
  fid=fopen(outfile,'w');fprintf(fid,'%s\n',jsonencode(payload));fclose(fid);disp(jsonencode(payload));
  if ~strcmp(payload.overall,'PASS'),error('LegacyProbe:Failure','one or more probes failed');end
end
function r=expect_error(name,fn,needle)
  r.name=name;r.pass=false;r.classification='OBSERVED_RUNTIME_DEFECT';r.message='';
  try,fn();r.message='expected an error but call returned';catch err,r.message=err.message;r.pass=~isempty(strfind(err.message,needle));r.identifier=err.identifier;end
end
function r=expect_success(name,fn)
  r.name=name;r.pass=false;r.classification='OBSERVED_RUNTIME_BEHAVIOR';r.message='';
  try,[a,b,c,d]=fn();r.pass=all(isfinite(a(:)))&&all(isfinite(b(:)))&&all(isfinite(c(:)))&&all(isfinite(d(:)));r.norms=[norm(a) norm(b) norm(c) norm(d)];catch err,r.message=err.message;r.identifier=err.identifier;end
end
function r=bearasym_probe(model)
  r.name='bearasym_type4_reverse_index';r.classification='OBSERVED_RUNTIME_DEFECT_AND_PRESERVED';r.pass=false;
  try,[Cb,Kb,K1b,zd]=bearasym(model);r.k12=K1b(1,2);r.k21=K1b(2,1);r.k34=K1b(3,4);r.k43=K1b(4,3);r.pass=(r.k12==-1 && r.k21==2 && r.k34==-2 && r.k43==0);r.zero_dof=zd;catch err,r.message=err.message;r.identifier=err.identifier;end
end
function r=foundation_predicate_probe()
  r.name='foundation_bearing_predicate';r.classification='OBSERVED_RUNTIME_TAUTOLOGY';types=-5:12;truth=false(size(types));for i=1:numel(types),truth(i)=(types(i)>2 | types(i)<9);end;r.types=types;r.truth=truth;r.pass=all(truth);
end
function r=runup_j_probe()
  r.name='runup_j_symbol';r.classification='OBSERVED_RUNTIME_BUILTIN_BEHAVIOR';r.pass=false;try,clear j;a=j;r.j_real=real(a);r.j_imag=imag(a);r.pass=(a==sqrt(-1));catch err,r.message=err.message;r.identifier=err.identifier;end
end
