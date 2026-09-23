function [response] = freq_fdn(model,Rotor_Spd,omega)
%
%  function  freq_fdn.m
%
%   [Response] = freq_fdn(model,Rotor_Spd,omega)
%
% Calculates the steady state forced response to foundation excitation of
% the rotor system at a single shaft speed in the frequency domain 
%
%    Rotor_Spd    is a single rotor speed in rad/s
%
%    response     is the response output and is a 2 dimensional array
%                 The indices are DoFs and frequency
%
%    Force_Def    = model.force
%                 gives the force definition. For foundation excitation this
%                 must be 4 in the first column. The remainder of the row
%                 gives the relative amplitude of the forcing at each
%                 bearing DoF (must be zero for short or long bearings) -
%                 and this can be complex to allow for a phase relationship
%
%    omega        frequencies where response is calculated
%
%
% This function is part of a MATLAB Toolbox to accompany the book
% 'Dynamics of Rotating Machinery' by MI Friswell, JET Penny, SD Garvey
% & AW Lees, published by Cambridge University Press, 2010
%

Node_Def = model.node;
Force_Def = model.force;
Bearing_Def = model.bearing;

if length(Rotor_Spd) > 1
    disp('>>>> Error - only a single shaft speed must be defined for foundation excitation')
    disp('             using the first shaft speed only')
    Rotor_Spd = Rotor_Spd(1);
end

jot = sqrt(-1);

% obtain model of rotor
[M0,C0,C1,K0,K1] = rotormtx(model);
[nnode,ncol_node] = size(Node_Def);
ndof = 4*nnode;

% sort out zeroed DoF and determine bearing model
[Mb,Cb,Kb,zero_dof] = bearmtx(model,Rotor_Spd);
dof = 1:ndof;
dof(zero_dof) = [];

% sort out forcing
[nforce,ncol_force] = size(Force_Def);
for iforce = nforce:-1:1
    if Force_Def(iforce,1) ~= 4, Force_Def(iforce,:) = []; end
end
[nforce,ncol_force] = size(Force_Def);
if nforce > 1
    disp('>>>> Error - foundation forcing not specified uniquely')
    disp('>>>>         using first row specified')
    Force_Def = Force_Def(1,:);
end
if nforce == 0
    disp('>>>> Error - no foundation force specified')
    response = [];
    return
end

% check forcing through the bearings
qf = zeros(ndof,1);
[nbearing,ncol_bearing] = size(Bearing_Def);
if ncol_force < 2*nbearing + 1
    disp('>>>> Error - insufficient foundation force amplitudes defined')
    response = [];
    return
end
for ibearing = 1:nbearing
    if Bearing_Def(ibearing,1) > 2 | Bearing_Def(ibearing,1) < 9
        ibnode = Bearing_Def(ibearing,2);
        qf(4*ibnode-3) = Force_Def(2*ibearing);
        qf(4*ibnode-2) = Force_Def(2*ibearing+1);
    end
end

% calculate machine model
M = M0 + Mb;
K = K0 + Kb + Rotor_Spd*K1;
C = C0 + Cb + Rotor_Spd*C1;
Mf = Mb*qf; Mf(zero_dof) = [];
Cf = Cb*qf; Cf(zero_dof) = [];
Kf = Kb*qf; Kf(zero_dof) = [];
if length(zero_dof) > 0
    M = M(dof,dof);
    C = C(dof,dof);
    K = K(dof,dof);
end

% calculate response
nfreq = length(omega);
response = zeros(ndof,nfreq);
for ifreq = 1:nfreq
   om = jot*omega(ifreq);
   om2 = om*om;
   response(dof,ifreq) = (M*om2+C*om+K)\(Mf*om2+Cf*om+Kf);
end
