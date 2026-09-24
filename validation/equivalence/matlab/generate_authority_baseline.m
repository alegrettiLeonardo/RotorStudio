function generate_authority_baseline(root_dir,out_dir,src)
if nargin < 1, error('root_dir required'); end
if nargin < 2, out_dir = fullfile(root_dir,'validation','baseline','matlab_authority'); end
if nargin < 3 || isempty(src), src = fullfile(root_dir,'reference','matlab_v2'); end
if ~exist(out_dir,'dir'), mkdir(out_dir); end
addpath(src);
meta_version=version;meta_computer=computer;meta_date=datestr(now,30);meta_source_dir=src;

circ_M=zeros(8,8,8);circ_C1=zeros(8,8,8);circ_K0=zeros(8,8,8);circ_K1=zeros(8,8,8);
for t=1:8,[circ_M(:,:,t),circ_C1(:,:,t),circ_K0(:,:,t),circ_K1(:,:,t)]=shftelem(t,.31,.08,.02,2.1e11,8.1e10,7800,2.5e4,1.2e3);end
[taper_M,taper_C1,taper_K0,taper_K1]=taper(22,.31,.08,.071,.02,.012,2.1e11,8.1e10,7800,2.5e4);
[asym_M,asym_C1,asym_K0,asym_K2]=shftasym(12,.31,1.25e5,1.05e5,.07,.09,11.5,.0042,0);

st=build_stationary(0);st_matrix_speed=300;[M0,C0,C1,K0,K1]=rotormtx(st);[Mb,Cb,Kb,zero_dof,st_ecc_matrix]=bearmtx(st,st_matrix_speed);
st_M=M0+Mb;st_C=C0+Cb+st_matrix_speed*C1;st_K=K0+Kb+st_matrix_speed*K1;st_G=C1;st_Mb=Mb;st_Cb=Cb;st_Kb=Kb;
st_modal_speeds=[0 100 300];[st_modal_eig,st_modal_vec,st_modal_kappa,st_modal_ecc]=chr_root(st,st_modal_speeds);
crit_n=4;crit_direct=crit_spd(st,1,1,crit_n);fluid=build_stationary(1);crit_fluid_n=2;crit_fluid=crit_spd(fluid,1,1,crit_fluid_n,20,1e-6);

rspm=build_response();rsp_speeds=[70 150 310];rsp_response=freq_rsp(rspm,rsp_speeds);
auxm=build_auxiliary();aux_rotor_speed=2*pi*3000/60;aux_omega=2*pi*[5 20 45];aux_direction=1;aux_response=freq_aux(auxm,aux_rotor_speed,aux_omega,aux_direction);
fdnm=build_foundation_freq();fdn_rotor_speed=2*pi*3000/60;fdn_omega=2*pi*[1 10 35];fdn_response=freq_fdn(fdnm,fdn_rotor_speed,fdn_omega);

coax=build_coax();coax_modal_speed=210;[coax_eig,coax_vec]=chr_root_coax(coax,coax_modal_speed);coax_rsp_speeds=[80 190 330];coax_response=freq_rsp_coax(coax,coax_rsp_speeds);

asym=build_asym();asym_speed=200;asym_eig_only=chr_asym(asym,asym_speed);[asym_eig_vec,asym_vec]=chr_asym(asym,asym_speed);asym_rsp_speeds=[0 120 260];asym_response=freq_asym(asym,asym_rsp_speeds);

ft=build_foundation_time();time_rotor_speed=2*pi*3000/60;time_dt=2e-4;time_npts=601;time_nr=10;[time_response,time_force,time_time]=time_fdn(ft,time_rotor_speed,time_dt,time_npts,time_nr);
ru=build_runup();runup_alpha=[.20*2*pi 8*pi 0];runup_t0=0;runup_tf=3;runup_nr=4;[runup_time,runup_response,runup_speed]=runup(ru,runup_alpha,[runup_t0 runup_tf],runup_nr);

outfile=fullfile(out_dir,'authority_baseline.mat');save(outfile,'-v7');
fid=fopen(fullfile(out_dir,'MATLAB_AUTHORITY_METADATA.txt'),'w');fprintf(fid,'version=%s\ncomputer=%s\ndate=%s\nsource=%s\n',meta_version,meta_computer,meta_date,meta_source_dir);fclose(fid);
fprintf('AUTHORITY_BASELINE_WRITTEN %s\n',outfile);
end

function m=build_stationary(fluid)
E=211e9;G=81.2e9;rho=7810;df=2e-5;m.node=[1 0;2 .25;3 .5;4 .75;5 1;6 1.25;7 1.5];
m.shaft=[2 1 2 .05 0 rho E G df;2 2 3 .05 0 rho E G df;2 3 4 .05 0 rho E G df;2 4 5 .05 0 rho E G df;2 5 6 .05 0 rho E G df;2 6 7 .05 0 rho E G df];
m.disc=[1 3 rho .07 .28 .05;1 5 rho .07 .35 .05];
if fluid,m.bearing=[7 1 525 .1 .03 1e-4 .1;7 7 525 .1 .03 1e-4 .1];else,m.bearing=[3 1 1e6 1e6 100 100;3 7 1e6 1e6 100 100];end
m.force=[];
end
function m=build_response(),m=build_stationary(0);m.force=[1 3 2.2e-4 .37 0;2 5 1.3e-5 -.21 0;3 0 0 0 0;8 2 6 8.5 .12];m.bend=[1 2e-5 -1e-5;7 -1.5e-5 .5e-5];end
function m=build_auxiliary(),m=build_stationary(0);m.force=[6 4 1e-4 .25];end
function m=build_foundation_freq(),m=build_stationary(0);m.force=[4 0 1e-5 0 2e-5];end
function m=build_foundation_time(),m=build_stationary(0);m.shaft(:,9)=0;m.force=[5 0 1e-3 0 1e-3 .025];end
function m=build_coax()
E=2.07e11;G=79.6e9;rho=8300;m.node=[1 0;2 .22;3 .46;4 0;5 .20;6 .44];
m.shaft=[2 1 2 .04 0 rho E G 0;2 2 3 .04 0 rho E G 0;2 4 5 .035 0 rho E G 0;2 5 6 .035 0 rho E G 0];m.disc=[2 2 7 .025 .05 0;2 5 5 .018 .036 0];
m.bearing=[3 1 7e6 7e6 80 80 0;3 3 7e6 7e6 80 80 0;3 4 6e6 6e6 70 70 0;3 6 6e6 6e6 70 70 0;20 2 5 1.2e6 1.1e6 100 90];m.rotors=[1 3 1;4 6 -.7];m.force=[1 5 1.1e-4 .3];
end
function m=build_asym()
m.node=[1 0;2 .3;3 .6];m.shaft=[12 1 2 1.2e5 1e5 .08 .09 12 .004 0 0;12 2 3 1.2e5 1e5 .08 .09 12 .004 0 0];m.disc=[5 2 8 .03 .04 .05];m.bearing=[4 1 1e6 1e6 2e4 2e4 100 100 5 5;4 3 1e6 1e6 2e4 2e4 100 100 5 5];m.force=[1 2 1e-4 .2;2 2 2e-5 -.1];
end
function m=build_runup()
E=211e9;G=E/(2*(1+.3));rho=7810;m.node=[1 0;2 .25;3 .5;4 .75;5 1;6 1.25;7 1.5];m.shaft=[2 1 2 .025 0 rho E G 0;2 2 3 .025 0 rho E G 0;2 3 4 .025 0 rho E G 0;2 4 5 .025 0 rho E G 0;2 5 6 .025 0 rho E G 0;2 6 7 .025 0 rho E G 0];m.disc=[1 7 rho .04 .25 0];m.bearing=[3 1 1e7 2e7 4e5 4e5;3 5 1e7 2e7 4e5 4e5];m.force=[1 7 1e-3 0];
end
