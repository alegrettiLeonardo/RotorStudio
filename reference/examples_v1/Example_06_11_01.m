% File name:   Example_06_11_01.m
%
% Example 6.11.1
%
% Calculation of run up for the overhung rotor

clear
format short e
close all

set(0,'defaultaxesfontsize',12)
set(0,'defaultaxesfontname','Times New Roman')
set(0,'defaulttextfontsize',12)
set(0,'defaulttextfontname','Times New Roman')

E = 211e9;
Poisson = 0.3;
G = E/(2*(1+Poisson));
rho = 7810;
damping_factor = 0;

model.node = [1 0.0; 2 0.25; 3 0.5; 4 0.75; 5 1.0; 6 1.25; 7 1.50];

shaft_od = 0.025;
shaft_id = 0.0;
model.shaft = [2 1 2 shaft_od shaft_id rho E G damping_factor; ...
               2 2 3 shaft_od shaft_id rho E G damping_factor; ...
               2 3 4 shaft_od shaft_id rho E G damping_factor; ...
               2 4 5 shaft_od shaft_id rho E G damping_factor; ...
               2 5 6 shaft_od shaft_id rho E G damping_factor; ...
               2 6 7 shaft_od shaft_id rho E G damping_factor];

disk_od = 0.250;
disk_thick = 0.04;
model.disc = [1 7 rho disk_thick disk_od 0.0];

Bearing_cases = [1e7 1e7  0   0; ...
                 1e7 2e7  0   0; ...
                 1e7 2e7 6e4 6e4; ...
                 1e7 2e7 4e5 4e5; ...
                 2e5 4e5  0   0];
LHcase = 4;
RHcase = 4;
model.bearing = [3 1 Bearing_cases(LHcase,:); ...
                 3 5 Bearing_cases(RHcase,:)];

model.force = [1 7 1e-3 0];

figure(1), clf
picrotor(model)

Rotor_Spd_rpm = 0:40:3200;
Rotor_Spd = 2*pi*Rotor_Spd_rpm/60;
[eigenvalues,eigenvectors] = chr_root(model,Rotor_Spd);
figure(2), clf
NX = 1.8;
damped_NF = 1;
plotcamp(Rotor_Spd,eigenvalues,NX,damped_NF)

icase = menu('Example 6.11.1 - run up','Case 1 - acceleration = 0.10Hz/s',...
    'Case 2 - acceleration = 0.40Hz/s');
if icase == 1
    alpha = [0.05*2*pi 8*pi 0];
    tspan = [0 70];
else
    alpha = [0.20*2*pi 8*pi 0];
    tspan = [0 20] ;
end

nr = 4;
[time,response,speed] = runup(model,alpha,tspan,nr);

figure(3), clf
x_dof_disk = 25;
[AX,H1,H2] = plotyy(time,1000*response(x_dof_disk,:),time,speed/(2*pi));
xlabel('Time (s)')
ylabel(AX(1),'Response at disk (mm)')
ylabel(AX(2),'Rotor speed (Hz)')
