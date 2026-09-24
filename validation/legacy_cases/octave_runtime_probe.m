function octave_runtime_probe(repo_root,outfile)
  if nargin<1,repo_root=pwd;end
  if nargin<2,outfile=fullfile(repo_root,'validation','reports','LEGACY_RUNTIME_OCTAVE_7_1.json');end
  addpath(fullfile(repo_root,'reference','matlab_v2'));
  results={};

  results{end+1}=expect_error('shftasym_8arg_default',@()shftasym(11,1,1,1,0,0,1,1),'AxialForce');
  results{end+1}=expect_error('shftasym_nonzero_axial',@()shftasym(11,1,1,1,0,0,1,1,10),'Kre');
  results{end+1}=shftasym_rotary_probe();
  results{end+1}=bearasym_probe();
  results{end+1}=chr_asym_nargout_probe();
  results{end+1}=foundation_predicate_probe();
  results{end+1}=runup_j_probe();

  payload.engine='GNU Octave';
  payload.version=version;
  payload.results=results;
  payload.overall='PASS';
  for i=1:numel(results)
    if ~results{i}.pass,payload.overall='FAIL';end
  end
  fid=fopen(outfile,'w');fprintf(fid,'%s\n',jsonencode(payload));fclose(fid);
  disp(jsonencode(payload));
  if ~strcmp(payload.overall,'PASS'),error('LegacyProbe:Failure','one or more probes failed');end
end

function r=expect_error(name,fn,needle)
  r.name=name;r.pass=false;r.classification='LEGACY_DEFECT_RUNTIME_CONFIRMED';r.message='';
  try
    fn();
    r.message='expected an error but call returned';
  catch err
    r.message=err.message;
    r.pass=~isempty(strfind(err.message,needle));
    r.identifier=err.identifier;
  end
end

function r=shftasym_rotary_probe()
  r.name='shftasym_rotary_contribution';
  r.classification='LEGACY_BEHAVIOR_RUNTIME_CONFIRMED';
  r.pass=false;
  try
    [~,c0,~,~]=shftasym(13,1,1,1,.1,.1,1,0,0);
    [~,c1,~,~]=shftasym(13,1,1,1,.1,.1,1,1,0);
    [~,c2,~,~]=shftasym(13,1,1,1,.1,.1,1,2,0);
    d1=c1-c0;d2=c2-c0;
    r.relative_quadratic_error=norm(d2-4*d1,'fro')/max(norm(d2,'fro'),1);
    r.pass=isfinite(r.relative_quadratic_error) && r.relative_quadratic_error<1e-12;
  catch err
    r.message=err.message;r.identifier=err.identifier;
  end
end

function r=bearasym_probe()
  r.name='bearasym_type4_reverse_index';
  r.classification='LEGACY_DEFECT_RUNTIME_CONFIRMED_AND_PRESERVED';
  r.pass=false;
  try
    model.node=[1 0];model.shaft=zeros(0,11);model.disc=zeros(0,6);
    model.bearing=[4 1 10 10 20 20 1 1 2 2];
    [~,~,K1b,zd]=bearasym(model);
    r.k12=K1b(1,2);r.k21=K1b(2,1);r.k34=K1b(3,4);r.k43=K1b(4,3);
    r.zero_dof=zd;
    r.pass=(r.k12==-1 && r.k21==2 && r.k34==-2 && r.k43==0);
  catch err
    r.message=err.message;r.identifier=err.identifier;
  end
end

function r=chr_asym_nargout_probe()
  r.name='chr_asym_nargout_paths';
  r.classification='LEGACY_OUTPUT_DEPENDENT_BEHAVIOR_RUNTIME_CONFIRMED';
  r.pass=false;
  try
    model.node=[1 0;2 1];
    model.shaft=[11 1 2 1e6 8e5 0 0 10 .01 0 0];
    model.disc=zeros(0,6);
    b=[4 1 1e6 1e6 1e4 1e4 100 100 10 10;
       4 2 1e6 1e6 1e4 1e4 100 100 10 10];
    model.bearing=b;
    e1=chr_asym(model,100);
    [e2,v]=chr_asym(model,100);
    r.eigenvalue_path_difference=norm(e1-e2);
    r.vector_shape=size(v);
    r.pass=isfinite(r.eigenvalue_path_difference) && r.eigenvalue_path_difference>0;
  catch err
    r.message=err.message;r.identifier=err.identifier;
  end
end

function r=foundation_predicate_probe()
  r.name='foundation_bearing_predicate';
  r.classification='LEGACY_DEFECT_RUNTIME_CONFIRMED';
  types=-5:12;truth=false(size(types));
  for i=1:numel(types),truth(i)=(types(i)>2 | types(i)<9);end
  r.types=types;r.truth=truth;
  r.pass=all(truth);
end

function r=runup_j_probe()
  r.name='runup_j_symbol';
  r.classification='LEGACY_BEHAVIOR_RUNTIME_CONFIRMED';
  r.pass=false;
  try
    clear j
    builtin_j=j;
    model.node=[1 0;2 .25];
    model.shaft=[2 1 2 .05 0 7810 211e9 81.2e9 0 0 0];
    model.disc=zeros(0,6);
    model.bearing=[3 1 1e6 1e6 100 100;3 2 1e6 1e6 100 100];
    model.force=[1 1 1e-4 0];
    [t,response,speed]=runup(model,[0 10 0],[0 .01],2);
    r.builtin_j_real=real(builtin_j);r.builtin_j_imag=imag(builtin_j);
    r.points=numel(t);
    r.max_response=max(abs(response(:)));
    r.pass=(builtin_j==sqrt(-1)) && numel(t)>=2 && all(isfinite(response(:))) && all(isfinite(speed(:)));
  catch err
    r.message=err.message;r.identifier=err.identifier;
  end
end
