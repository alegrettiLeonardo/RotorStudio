function [response] = freq_asym(model,Rotor_Spd)
%
%  function  freq_asym.m
%
%   [response] = freq_asym(model,Rotor_Spd)
%
% Calculates the steady state forced response of a machine with an 
% asymmetric rotor to unbalance force only at a range of shaft speeds 
% in the rotating frame
%
%    Rotor_Spd    is a vector of rotor speeds in rad/s
%
%    response     is the response output and is a 2 dimensional array
%                 The indices are DoFs and shaft speeds
%
%    model.force  is the force definition matrix - only unbalance allowed
%                 the first column gives the type of forcing:
%
%                 1   is unbalance force
%                 2   is unbalance moment
%
% This function is part of a MATLAB Toolbox to accompany the book
% 'Dynamics of Rotating Machinery' by MI Friswell, JET Penny, SD Garvey
% & AW Lees, published by Cambridge University Press, 2010
%


Node_Def = model.node;
Force_Def = model.force;
nforce = size(Force_Def,1);

nspeed = length(Rotor_Spd);
j = sqrt(-1);


% obtain model of rotor

[M0,C0,C1,K0,K1,K2] = rotorasym(model);
[nnode,ncol_node] = size(Node_Def);
ndof = 4*nnode;

% sort out zeroed DoF and bearing matrix
% note fluid bearing are not allowed (since then both the
% bearing and the rotor would be asymmetric)
[Cb,Kb,K1b,zero_dof] = bearasym(model);
dof = 1:ndof;
dof(zero_dof) = [];
nzero = length(zero_dof);
ncdof = ndof - nzero;

% determine the unbalance parts of the forcing
ubforce = zeros(ndof,1);
for iforce = 1:nforce
    if Force_Def(iforce,1) == 1  % unbalance force
        node = Force_Def(iforce,2);
        unbal_mag = Force_Def(iforce,3);
        unbal_phase = Force_Def(iforce,4);
        force_dof = [4*node-3; 4*node-2];
        ubforce(force_dof) = ubforce(force_dof) + unbal_mag*[cos(unbal_phase); sin(unbal_phase)];
    end
    if Force_Def(iforce,1) == 2  % unbalance moment
        node = Force_Def(iforce,2);
        unbal_mag = Force_Def(iforce,3);
        unbal_phase = Force_Def(iforce,4);
        force_dof = [4*node-1; 4*node];
        ubforce(force_dof) = ubforce(force_dof) + unbal_mag*[-sin(unbal_phase); cos(unbal_phase)];
    end
end 
ubforce(zero_dof) = [];  % remove force from zeroed dof 


% calculate response
response = zeros(ndof,nspeed);
for ispeed = 1:nspeed
   K = K0 + Kb + Rotor_Spd(ispeed)*(K1+K1b) + (Rotor_Spd(ispeed)^2)*K2;
   response(dof,ispeed) = (Rotor_Spd(ispeed)^2)*(K(dof,dof)\ubforce);
end




