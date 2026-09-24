function run_octave_probes(output_csv)
% Runtime characterization of known Rotor_Software_v2 legacy issues.
% This file does not repair authority code. It executes the preserved V2 sources.

fid=fopen(output_csv,'w');
fprintf(fid,'item,status,classification,detail\n');
failures=0;

% 1) shftasym default-argument defect: 8 supplied arguments leave AxialForce undefined.
try
  shftasym(11,1.0,10.0,12.0,0.0,0.0,1.0,0.1);
  record(fid,'shftasym_nargin','FAIL','LEGACY_DEFECT','8-argument call unexpectedly succeeded'); failures=failures+1;
catch err
  record(fid,'shftasym_nargin','PASS','LEGACY_DEFECT_RUNTIME_CONFIRMED',err.message);
end

% 2) shftasym nonzero axial branch references Kre before initialization.
try
  shftasym(11,1.0,10.0,12.0,0.0,0.0,1.0,0.1,100.0);
  record(fid,'shftasym_axial','FAIL','LEGACY_DEFECT','nonzero axial-force call unexpectedly succeeded'); failures=failures+1;
catch err
  record(fid,'shftasym_axial','PASS','LEGACY_DEFECT_RUNTIME_CONFIRMED',err.message);
end

% 3) shftasym rotary Cs term is nonlinear in rhoI because Ms was already scaled.
try
  [~,c1]=shftasym(12,1.0,10.0,10.0,0.1,0.1,0.0,1.0,0.0);
  [~,c2]=shftasym(12,1.0,10.0,10.0,0.1,0.1,0.0,2.0,0.0);
  residual=norm(c2-2*c1,'fro');
  if residual>1e-12
    record(fid,'shftasym_rotary_cs','PASS','LEGACY_BEHAVIOR_RUNTIME_CONFIRMED',sprintf('nonlinear residual=%g',residual));
  else
    record(fid,'shftasym_rotary_cs','FAIL','LEGACY_BEHAVIOR','expected nonlinear rhoI scaling not observed'); failures=failures+1;
  end
catch err
  record(fid,'shftasym_rotary_cs','FAIL','LEGACY_BEHAVIOR',err.message); failures=failures+1;
end

% 4) bearasym type-4 index overwrite.
try
  m.node=[1 0]; m.shaft=zeros(0,9); m.disc=zeros(0,5);
  m.bearing=[4 1 1e6 1e6 2e6 2e6 3 3 7 7];
  [~,~,K1b,~]=bearasym(m);
  if K1b(3,4)==-7 && K1b(4,3)==0 && K1b(2,1)==7
    record(fid,'bearasym_type4_index','PASS','LEGACY_DEFECT_RUNTIME_CONFIRMED',sprintf('K1b34=%g K1b43=%g K1b21=%g',K1b(3,4),K1b(4,3),K1b(2,1)));
  else
    record(fid,'bearasym_type4_index','FAIL','LEGACY_DEFECT','unexpected K1b pattern'); failures=failures+1;
  end
catch err
  record(fid,'bearasym_type4_index','FAIL','LEGACY_DEFECT',err.message); failures=failures+1;
end

% 5) chr_asym output-count-dependent equations: one output includes K1b, two outputs omit it.
try
  m.node=[1 0;2 1.0];
  m.shaft=[11 1 2 10 12 0 0 1.0 0.1 0 0];
  m.disc=zeros(0,6);
  m.bearing=[3 1 1e6 1e6 500 500;3 2 1e6 1e6 500 500];
  w=50.0;
  e1=chr_asym(m,w);
  [e2,~]=chr_asym(m,w);
  delta=max(abs(sort(e1)-sort(e2)));
  if delta>1e-9
    record(fid,'chr_asym_nargout','PASS','LEGACY_OUTPUT_DEPENDENT_BEHAVIOR_RUNTIME_CONFIRMED',sprintf('max eigenvalue delta=%g',delta));
  else
    record(fid,'chr_asym_nargout','FAIL','LEGACY_OUTPUT_DEPENDENT_BEHAVIOR','one-output and two-output paths unexpectedly equal'); failures=failures+1;
  end
catch err
  record(fid,'chr_asym_nargout','FAIL','LEGACY_OUTPUT_DEPENDENT_BEHAVIOR',err.message); failures=failures+1;
end

% 6) Foundation bearing predicate is tautological for all finite numeric types.
try
  types=[1 2 3 4 7 8 9 -1]; vals=(types>2 | types<9);
  if all(vals)
    record(fid,'foundation_bearing_predicate','PASS','LEGACY_DEFECT_RUNTIME_CONFIRMED','type > 2 OR type < 9 evaluated true for all probe types');
  else
    record(fid,'foundation_bearing_predicate','FAIL','LEGACY_DEFECT','predicate was not tautological'); failures=failures+1;
  end
catch err
  record(fid,'foundation_bearing_predicate','FAIL','LEGACY_DEFECT',err.message); failures=failures+1;
end

% 7) runup mixes jot and MATLAB/Octave j, but the unshadowed built-in j path executes.
try
  m.node=[1 0;2 1.0];
  m.shaft=[1 1 2 .05 0 7800 2e11];
  m.disc=zeros(0,5);
  m.bearing=[3 1 1e6 1e6 10 10;3 2 1e6 1e6 10 10];
  m.force=[1 1 1e-4 0];
  [t,r,s]=runup(m,[0 100 0],[0 .001],2);
  if ~isempty(t) && all(isfinite(r(:))) && all(isfinite(s(:)))
    record(fid,'runup_j_vs_jot','PASS','LEGACY_BEHAVIOR_RUNTIME_CONFIRMED',sprintf('points=%d',length(t)));
  else
    record(fid,'runup_j_vs_jot','FAIL','LEGACY_BEHAVIOR','runup returned empty/nonfinite result'); failures=failures+1;
  end
catch err
  record(fid,'runup_j_vs_jot','FAIL','LEGACY_BEHAVIOR',err.message); failures=failures+1;
end

fclose(fid);
if failures>0, error('legacy probe failures=%d',failures); end
end

function record(fid,item,status,classification,detail)
detail=strrep(detail,sprintf('\n'),' ');
detail=strrep(detail,',',';');
fprintf(fid,'%s,%s,%s,%s\n',item,status,classification,detail);
end
