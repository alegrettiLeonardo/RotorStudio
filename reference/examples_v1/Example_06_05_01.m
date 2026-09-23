% File name:   Example_06_05_01.m
%
% Example 6.5.1
%
% Response to foundation excitation with constant stiffness bearings.
% The models are the same as 5.9.1 and 5.9.2 apart from some damping in the
% bearings
%
% (a) is the frequency response
% (b) is the time response to a pulse

clear
format short e
close all

set(0,'defaultaxesfontsize',12)
set(0,'defaultaxesfontname','Times New Roman')
set(0,'defaulttextfontsize',12)
set(0,'defaulttextfontname','Times New Roman')

icase = menu('Example 6.5.1 - forcing through the foundations',...
    'case (a) - frequency response',...
    'case (b) - time response');

E = 211e9;
G = 81.2e9;
rho = 7810;
damping_factor = 0;

model.node = [1 0.0; 2 0.25; 3 0.5; 4 0.75; 5 1.0; 6 1.25; 7 1.50];
shaft_od = 0.05;
shaft_id = 0.0;
model.shaft = [2 1 2 shaft_od shaft_id rho E G damping_factor; ...
               2 2 3 shaft_od shaft_id rho E G damping_factor; ...
               2 3 4 shaft_od shaft_id rho E G damping_factor; ...
               2 4 5 shaft_od shaft_id rho E G damping_factor; ...
               2 5 6 shaft_od shaft_id rho E G damping_factor; ...
               2 6 7 shaft_od shaft_id rho E G damping_factor];

disk1_od = 0.28;
disk2_od = 0.35;
disk_thick = 0.07;
model.disc = [1 3 rho disk_thick disk1_od shaft_od; ...
              1 5 rho disk_thick disk2_od shaft_od];

model.bearing = [3 1 1e6 1e6 100 100; ...
                 3 7 1e6 1e6 100 100];

if icase == 1
    force_mag = 1e-5;
    model.force = [4 0 force_mag 0 force_mag];
else
    force_mag = 1e-3;
    pulse_duration = 0.025;
    model.force = [5 0 force_mag 0 force_mag pulse_duration];
end

figure(1), clf
picrotor(model)

Rotor_Spd_rpm = 0:100:4500.0;
Rotor_Spd = 2*pi*Rotor_Spd_rpm/60;
[eigenvalues,eigenvectors,kappa] = chr_root(model,Rotor_Spd);
figure(2), clf
NX = 1.2;
damped_NF = 1;
plotcamp(Rotor_Spd,eigenvalues,NX,damped_NF,kappa)

Rotor_Spd_rpm = 3000.0;
Rotor_Spd = 2*pi*Rotor_Spd_rpm/60;

if icase==1
    omega_Hz = 0:0.05:55;
    omega = 2*pi*omega_Hz;
    [response] = freq_fdn(model,Rotor_Spd,omega);
    figure(3), clf
    outnode = [3.1; 3.2];
    plotfrf(omega,response,outnode)
    figure(4), clf
    outnode = [5.1; 5.2];
    plotfrf(omega,response,outnode)
else
    dt = 0.00006;
    npts = 65536;
    [response,force,time] = time_fdn(model,Rotor_Spd,dt,npts);
    figure(3), clf
    plot(time,force)
    xlabel('Time (s)')
    ylabel('Foundation displacement pulse')
    figure(4), clf
    outdof = [10 18];
    plot(time,1000*response(outdof,:))
    xlabel('Time (s)')
    ylabel('Response displacement (mm)')
    legend('Node 3, {ity}','Node 5, {ity}')
    dt = 0.001;
    npts = 16384;
    nr = 10;
    [response,force,time] = time_fdn(model,Rotor_Spd,dt,npts,nr);
    [fft_out,omega_fft] = fftscale(response,time);
    [fft_force,omega_force] = fftscale(force,time);
    figure(5), clf
    semilogy(omega_fft,abs(fft_out(outdof,:)))
    xlabel('Frequency (Hz)')
    ylabel('Response amplitude (m)')
    legend('Node 3, {ity}','Node 5, {ity}')
    axis([0 55 1e-8 1e-3])
    figure(6), clf
    semilogy(omega_force,1e-3*abs(fft_force))
    xlabel('Frequency (Hz)')
    ylabel('Foundation displacement amplitude (m)')
    axis([0 55 1e-7 1e-5])
    figure(7), clf
    outputnode = [3 5];
    subplot(221), ifreq = 225;
    plotorbit(fft_out(:,ifreq),outputnode,['Orbit at ' num2str(omega_fft(ifreq)) 'Hz'])
    subplot(222), ifreq = 235;
    plotorbit(fft_out(:,ifreq),outputnode,['Orbit at ' num2str(omega_fft(ifreq)) 'Hz'])
    subplot(223), ifreq = 672;
    plotorbit(fft_out(:,ifreq),outputnode,['Orbit at ' num2str(omega_fft(ifreq)) 'Hz'])
    subplot(224), ifreq = 767;
    plotorbit(fft_out(:,ifreq),outputnode,['Orbit at ' num2str(omega_fft(ifreq)) 'Hz'])
end
