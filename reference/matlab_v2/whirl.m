function [kappa,amplitude] = whirl(u,v)
%
% function whirl.m
%
%   [kappa,amplitude] = whirl(u,v)
%
%  to determine the direction of whirl for different speeds
%
%  u and v    are vectors of the response at different speeds
% 
%  kappa      is the whirl direction and shape of the orbit
%             as given in the book
%
%  amplitude  is the length of the semimajor axis
%
%
% This function is part of a MATLAB Toolbox to accompany the book
% 'Dynamics of Rotating Machinery' by MI Friswell, JET Penny, SD Garvey
% & AW Lees, published by Cambridge University Press, 2010
%


if length(u) ~= length(v)
    disp('>>>> error in whirl.m, the vectors must be equal length')
    kappa = [];
    return
end

npts = length(u);
u_abs = abs(u);
v_abs = abs(v);
u_ang = angle(u);
v_ang = angle(v);
kappa = zeros(1,npts);
amplitude = zeros(1,npts);
for i=1:npts
    if u_abs(i)*v_abs(i) < 1e-16
        kappa(i) = 0;
        amplitude(i) = 0;
    else
        H12 = u_abs(i)*v_abs(i)*cos(u_ang(i)-v_ang(i));
        Hinv = [u_abs(i)^2 H12; H12 v_abs(i)^2];
        eigH = eig(Hinv);
        kappa(i) = sqrt(min(eigH)/max(eigH));
        ang_diff = mod(v_ang(i)-u_ang(i),2*pi);
        if ang_diff > 0 & ang_diff < pi
            kappa(i) = - kappa(i);
        end
        amplitude(i) = sqrt(max(eigH));
    end
end