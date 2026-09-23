function generate_octave_baseline(repo_root, outfile)
% Deterministic Rotor_Software_v2 qualification baseline.
% This file does not modify the legacy functions. It calls them directly.
addpath(fullfile(repo_root,'reference','matlab_v2'));

% Environment / semantic compatibility evidence.
is_octave = exist('OCTAVE_VERSION','builtin') ~= 0;
if is_octave
  engine_name = ['GNU Octave ' OCTAVE_VERSION];
else
  engine_name = ['MATLAB ' version];
end
semantic_checks = zeros(8,1);
semantic_checks(1) = norm((eye(3)\[1;2;3])-[1;2;3]);
rtest=roots([1 -3 2]);
semantic_checks(2) = abs(prod(rtest)-2);
semantic_checks(3) = abs(1i*1i+1);
semantic_checks(4) = norm(eig(diag([2 3]))-[2;3]);
semantic_checks(5) = norm(sort([3+4i 1i -1i])-sort([3+4i 1i -1i]));
semantic_checks(6) = abs(pi-acos(-1));
semantic_checks(7) = double(exist('ode45','file')>0);
semantic_checks(8) = double(exist('roots','file')>0);

%% G5 — element matrices, all legacy shaft-type switches.
L=.23; do=.067; di=.013; E=2.07e11; G=7.95e10; rho=7830; axial=12000; torque=350;
elem_circular_M=zeros(8,8,8); elem_circular_C1=zeros(8,8,8); elem_circular_K0=zeros(8,8,8); elem_circular_K1=zeros(8,8,8);
for t=1:8
  [M,C1,K0,K1]=shftelem(t,L,do,di,E,G,rho,axial,torque);
  elem_circular_M(:,:,t)=M;elem_circular_C1(:,:,t)=C1;elem_circular_K0(:,:,t)=K0;elem_circular_K1(:,:,t)=K1;
end

Lt=.31; doj=.080; dok=.065; dij=.020; dik=.014; axial_t=8000;
elem_taper_M=zeros(8,8,8); elem_taper_C1=zeros(8,8,8); elem_taper_K0=zeros(8,8,8); elem_taper_K1=zeros(8,8,8);
for k=1:8
  t=20+k;[M,C1,K0,K1]=taper(t,Lt,doj,dok,dij,dik,E,G,rho,axial_t);
  elem_taper_M(:,:,k)=M;elem_taper_C1(:,:,k)=C1;elem_taper_K0(:,:,k)=K0;elem_taper_K1(:,:,k)=K1;
end

EIx=1.31e5; EIy=1.07e5; Phix=.08; Phiy=.11; rhoA=12.2; rhoI=.0046;
elem_asym_M=zeros(8,8,8); elem_asym_C1=zeros(8,8,8); elem_asym_K0=zeros(8,8,8); elem_asym_K2=zeros(8,8,8);
for k=1:8
  t=10+k;[M,C1,K0,K2]=shftasym(t,L,EIx,EIy,Phix,Phiy,rhoA,rhoI,0);
  elem_asym_M(:,:,k)=M;elem_asym_C1(:,:,k)=C1;elem_asym_K0(:,:,k)=K0;elem_asym_K2(:,:,k)=K2;
end

%% G6 — global stationary assembly and bearing matrices.
model=struct();model.node=[1 0;2 .20;3 .45;4 .75];
model.shaft=[2 1 2 .060 .010 rho E G 2e-5 5000 120; ...
             22 2 3 .060 .052 .010 .006 rho E G 3000; ...
             2 3 4 .052 .006 rho E G 1e-5 -2000 -80];
model.disc=[1 2 rho .04 .22 .06;2 3 7.5 .025 .047 0];model.bearing=[];model.force=[];
[global_M0,global_C0,global_C1,global_K0,global_K1]=rotormtx(model);

bm=struct();bm.node=[(1:8)' (0:7)'];bm.shaft=[];bm.disc=[];bm.force=[];
bm.bearing=zeros(8,34);
bm.bearing(1,1:2)=[1 1];bm.bearing(2,1:2)=[2 2];
bm.bearing(3,1:6)=[3 3 11e6 12e6 101 102];
bm.bearing(4,1:10)=[4 4 21e6 22e6 31e3 32e3 201 202 301 302];
bm.bearing(5,1:10)=[5 5 41e6 4.2e6 -4.3e6 44e6 401 402 -403 404];
bm.bearing(6,1:34)=[6 6 (1:16)*1e5 (101:116)*10];
bm.bearing(7,1:8)=[7 7 1200 .06 .025 60e-6 .018 0];
bm.bearing(8,1:8)=[8 8 2.1e5 .04 .08 .00025 12 .08];
[bear_M,bear_C,bear_K,bear_zero_dof,bear_ecc]=bearmtx(bm,320);
bear_zero_mask=zeros(32,1);bear_zero_mask(bear_zero_dof)=1;

%% G7 — stationary modal/eigenvector/kappa/eccentricity.
sm=standard_model(); modal_speed=4000*2*pi/60;
[modal_eig,modal_vec,modal_kappa,modal_ecc]=chr_root(sm,modal_speed);
fm=standard_model();fm.bearing=[7 1 525 .1 .03 1e-4 .1 0;7 7 525 .1 .03 1e-4 .1 0];
fluid_modal_speed=3000*2*pi/60;[fluid_modal_eig,fluid_modal_vec,fluid_modal_kappa,fluid_modal_ecc]=chr_root(fm,fluid_modal_speed);

%% G8 — harmonic response families.
fr=standard_model();fr.force=[1 3 1.7e-4 .31;2 5 2.4e-5 -.22];
fr_speeds=[300 1200 2500 4000]*2*pi/60;fr_rsp=freq_rsp(fr,fr_speeds);
aux=standard_model();aux.force=[6 4 1e-4 .27];aux_rotor_speed=3000*2*pi/60;aux_omega=[500 1600 3300]*2*pi/60;aux_rsp=freq_aux(aux,aux_rotor_speed,aux_omega,1);
fdn=standard_model();fdn.force=[4 0 1e-5 0 1.5e-5];fdn_rotor_speed=3000*2*pi/60;fdn_omega=2*pi*[5 20 45];fdn_rsp=freq_fdn(fdn,fdn_rotor_speed,fdn_omega);

%% G9 — critical speeds, direct and fluid-bearing iterative.
[crit_direct,crit_direct_modes]=crit_spd(sm,1,1,4);
[crit_iter,crit_iter_modes]=crit_spd(fm,1,1,2,30,1e-8);
initial_estimates=[80;350];[crit_initial,crit_initial_modes]=crit_spd(sm,1,1,2,30,1e-9,initial_estimates);

%% G11 — coaxial rotor.
coax=coaxial_model();coax_speed=4000*2*pi/60;[coax_eig,coax_vec]=chr_root_coax(coax,coax_speed);
coax.force=[1 2 1e-4 0];coax_rsp_speeds=[1000 3000 6000]*2*pi/60;coax_rsp=freq_rsp_coax(coax,coax_rsp_speeds);

%% G12 — rotating/asymmetric rotor.
am=asym_model();asym_speed=2200*2*pi/60;
[asym_eig_only]=chr_asym(am,asym_speed);[asym_eig_vec,asym_vec]=chr_asym(am,asym_speed);
am.force=[1 3 .001 pi/6];asym_rsp_speeds=[500 1600 3200]*2*pi/60;asym_rsp=freq_asym(am,asym_rsp_speeds);
[asym_M0,asym_C0,asym_C1,asym_K0,asym_K1,asym_K2]=rotorasym(am);[asym_Cb,asym_Kb,asym_K1b,asym_zero_dof]=bearasym(am);

%% G10 — transient authority execution using V2 ode45.
tm=standard_model();tm.force=[5 0 1e-3 0 1e-3 .025];transient_rotor_speed=3000*2*pi/60;
transient_dt=2e-4;transient_npts=1001;transient_nr=10;
[time_fdn_rsp,time_fdn_force,time_fdn_time]=time_fdn(tm,transient_rotor_speed,transient_dt,transient_npts,transient_nr);
rm=runup_model();runup_alpha=[.20*2*pi 8*pi 0];runup_tspan=[0 3];runup_nr=4;
[runup_time,runup_rsp,runup_speed]=runup(rm,runup_alpha,runup_tspan,runup_nr);

if is_octave
  save('-mat7-binary',outfile);
else
  save(outfile,'-v7');
end
end

function m=standard_model()
E=211e9;G=81.2e9;rho=7810;d=0;m=struct();
m.node=[1 0;2 .25;3 .5;4 .75;5 1;6 1.25;7 1.5];
m.shaft=[2 1 2 .05 0 rho E G d;2 2 3 .05 0 rho E G d;2 3 4 .05 0 rho E G d;2 4 5 .05 0 rho E G d;2 5 6 .05 0 rho E G d;2 6 7 .05 0 rho E G d];
m.disc=[1 3 rho .07 .28 .05;1 5 rho .07 .35 .05];
m.bearing=[3 1 1e6 1e6 100 100;3 7 1e6 1e6 100 100];m.force=[];
end

function m=coaxial_model()
E=2.07e11;G=E/(2*(1+.3));rho=8300;d=0;m=struct();
m.node=[1 0;2 .076;3 .159;4 .254;5 .324;6 .406;7 .457;8 .508;9 .152;10 .203;11 .279;12 .356;13 .406];
m.shaft=[2 1 2 .030 0 rho E G d;2 2 3 .030 0 rho E G d;2 3 4 .030 0 rho E G d;2 4 5 .030 0 rho E G d;2 5 6 .030 0 rho E G d;2 6 7 .030 0 rho E G d;2 7 8 .030 0 rho E G d;2 9 10 .060 .050 rho E G d;2 10 11 .060 .050 rho E G d;2 11 12 .060 .050 rho E G d;2 12 13 .060 .050 rho E G d];
m.disc=[2 2 10.5 .043 .086;2 7 7 .034 .068;2 10 7 .021 .042;2 12 3.5 .013 .026];m.rotors=[1 8 1;9 13 1.5];
m.bearing=[3 1 26e6 52e6 20 20 0;3 8 18e6 36e6 20 20 0;3 9 18e6 36e6 20 20 0;20 6 13 9e6 9e6 20 20];m.force=[];
end

function m=asym_model()
E=211e9;rho=7810;A=.002;Ix=4.2043e-7;Iy=2.4112e-7;EIx=E*Ix;EIy=E*Iy;rhoA=rho*A;rhoI=rho*(Ix+Iy)/2;m=struct();
m.node=[1 0;2 .25;3 .5;4 .75;5 1;6 1.25;7 1.5];
m.shaft=[11 1 2 EIx EIy 0 0 rhoA rhoI 0;11 2 3 EIx EIy 0 0 rhoA rhoI 0;11 3 4 EIx EIy 0 0 rhoA rhoI 0;11 4 5 EIx EIy 0 0 rhoA rhoI 0;11 5 6 EIx EIy 0 0 rhoA rhoI 0;11 6 7 EIx EIy 0 0 rhoA rhoI 0];
shaft_od=2*sqrt(A/pi);m.disc=[1 3 rho .07 .28 shaft_od;1 5 rho .07 .35 shaft_od];m.bearing=[3 1 1e6 1e6 5e3 5e3;3 7 1e6 1e6 5e3 5e3];m.force=[];
end

function m=runup_model()
E=211e9;G=E/(2*(1+.3));rho=7810;m=struct();m.node=[1 0;2 .25;3 .5;4 .75;5 1;6 1.25;7 1.5];
m.shaft=[2 1 2 .025 0 rho E G 0;2 2 3 .025 0 rho E G 0;2 3 4 .025 0 rho E G 0;2 4 5 .025 0 rho E G 0;2 5 6 .025 0 rho E G 0;2 6 7 .025 0 rho E G 0];m.disc=[1 7 rho .04 .25 0];m.bearing=[3 1 1e7 2e7 4e5 4e5;3 5 1e7 2e7 4e5 4e5];m.force=[1 7 1e-3 0];
end
