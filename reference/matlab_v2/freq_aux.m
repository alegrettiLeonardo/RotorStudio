function [response] = freq_aux(model,Rotor_Spd,omega,direction)
%
%  function  freq_aux.m
%
%   [Response] = freq_aux(model,Rotor_Spd,omega,direction)
%
% Calculates the steady state forced response to forcing via auxiliary
% bearings at a single shaft speeds
%
%    Rotor_Spd    is a single rotor speed in rad/s
%
%    Response     is the response output and is a 2 dimensional array
%                 The indices are DoFs and frequency
%
%    omega        frequencies where response is calculated
%
%    direction    is positive for the spinner rotating forward, and
%                 negative for backwards
%
%    Force_Def    the first column gives the type of forcing:
%                 6   is a spinner (remaining columns are aux_node,
%                            unbal_mag, unbal_phase)
%                 7   is a vibrator (remaining columns are aux_node,
%                            f_x, f_y)
%
%
% This function is part of a MATLAB Toolbox to accompany the book
% 'Dynamics of Rotating Machinery' by MI Friswell, JET Penny, SD Garvey
% & AW Lees, published by Cambridge University Press, 2010
%

if nargin < 4
    direction = 1;
end

Node_Def = model.node;
Force_Def = model.force;

if length(Rotor_Spd) > 1
    disp('>>>> Error - only a single shaft speed must be defined for excitation through')
    disp('             auxiliary bearings - using the first shaft speed only')
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

% calculate machine model
M = M0 + Mb;
K = K0 + Kb + Rotor_Spd*K1;
C = C0 + Cb + Rotor_Spd*C1;
if length(zero_dof) > 0
    M = M(dof,dof);
    C = C(dof,dof);
    K = K(dof,dof);
end


% sort out forcing
[nforce,ncol_force] = size(Force_Def);
for iforce = nforce:-1:1
    if Force_Def(iforce,1) ~= 6 & Force_Def(iforce,1) ~= 7
        Force_Def(iforce,:) = []; 
    end
end
[nforce,ncol_force] = size(Force_Def);
if nforce > 1
    disp('>>>> Error - forcing through auxiliary bearing not specified uniquely')
    disp('>>>>         using first of Force Type 6 or 7')
    Force_Def = Force_Def(1,:);
end
if nforce == 0
    disp('>>>> Error - no forcing through auxiliary bearing specified')
    response = [];
    return
end



force = zeros(ndof,1);
nfreq = length(omega);
response = zeros(ndof,nfreq);

% calculate spinner unbalance forcing and the response
if Force_Def(1,1) == 6  % spinner
    aux_node = Force_Def(1,2);
    unbal_mag = Force_Def(1,3);
    unbal_phase = Force_Def(1,4);
    force_dof = [4*aux_node-3; 4*aux_node-2];
    if direction > 0
        force(force_dof) = force(force_dof) + unbal_mag*exp(j*unbal_phase)*[1; -jot];
    else
        force(force_dof) = force(force_dof) + unbal_mag*exp(j*unbal_phase)*[1; jot];
    end
    force(zero_dof) = [];  % remove force from zeroed dof 
    for ifreq = 1:nfreq % calculate response
        om = omega(ifreq);
        om2 = om*om;
        response(dof,ifreq) = (-M*om2+C*jot*om+K)\(om2*force);
    end
end

% calculate vibrator forcing and the response
if Force_Def(1,1) == 7  % spinner
    aux_node = Force_Def(1,2);
    f_x = Force_Def(1,3);
    f_y = Force_Def(1,4);
    force_dof = [4*aux_node-3; 4*aux_node-2];
    force(force_dof) = force(force_dof) + [f_x; f_y];
    force(zero_dof) = [];  % remove force from zeroed dof 
    for ifreq = 1:nfreq % calculate response
        om = omega(ifreq);
        om2 = om*om;
        response(dof,ifreq) = (-M*om2+C*jot*om+K)\force;
    end
end
