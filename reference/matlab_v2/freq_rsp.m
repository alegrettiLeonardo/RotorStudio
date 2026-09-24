function [response] = freq_rsp(model,Rotor_Spd)
%
%  function  freq_rsp.m
%
%   [Response] = freq_rsp(model,Rotor_Spd)
%
% Calculates the steady state forced response to unbalance and bends for
% the rotor system at a range of shaft speeds 
%
%    Rotor_Spd    is a vector of rotor speeds in rad/s
%
%    response     is the response output and is a 2 dimensional array
%                 The indices are DoFs and shaft speeds
%
%    model.force  is the force definition matrix
%                 the first column gives the type of forcing:
%
%                 1   is unbalance force
%                 2   is unbalance moment
%                 3   is a bent shaft
%
%
% This function is part of a MATLAB Toolbox to accompany the book
% 'Dynamics of Rotating Machinery' by MI Friswell, JET Penny, SD Garvey
% & AW Lees, published by Cambridge University Press, 2010
%

Node_Def = model.node;
Force_Def = model.force;

nspeed = length(Rotor_Spd);
[nforce,ncol_force] = size(Force_Def);

j = sqrt(-1);

% obtain model of rotor
[M0,C0,C1,K0,K1] = rotormtx(model);
[nnode,ncol_node] = size(Node_Def);
ndof = 4*nnode;

% sort out zeroed DoF - just use the first rotor speed to determine DoF
[Mb,Cb,Kb,zero_dof] = bearmtx(model,Rotor_Spd(1));
dof = 1:ndof;
dof(zero_dof) = [];


% determine the unbalance parts of the forcing
ubforce = zeros(ndof,1);
for iforce = 1:nforce
    if Force_Def(iforce,1) == 1  % unbalance force
        node = Force_Def(iforce,2);
        unbal_mag = Force_Def(iforce,3);
        unbal_phase = Force_Def(iforce,4);
        force_dof = [4*node-3; 4*node-2];
        ubforce(force_dof) = ubforce(force_dof) + unbal_mag*exp(j*unbal_phase)*[1; -j];
    end
    if Force_Def(iforce,1) == 2  % unbalance moment
        node = Force_Def(iforce,2);
        unbal_mag = Force_Def(iforce,3);
        unbal_phase = Force_Def(iforce,4);
        force_dof = [4*node-1; 4*node];
        ubforce(force_dof) = ubforce(force_dof) + unbal_mag*exp(j*unbal_phase)*[j; 1];
    end
end 
ubforce(zero_dof) = [];  % remove force from zeroed dof 


% determine the bend
% displacements at various nodes are defined and the Guyan transformation
% used to expand the deformations to the whole shaft
isbend = 0;
bend_force = zeros(ndof,1);
for iforce = 1:nforce
    if Force_Def(iforce,1) == 3, isbend = 1; end
end 
if isbend
    if isfield(model,'bend')
        Bend_Def = model.bend;
    else
        disp('>>>> Error - bend not specified in model - unable to calculate response due to bend')
    end
    [npts,ncol_bend] = size(Bend_Def);
    if ncol_bend == 1
        if npts == nnode
            Bend_Def = [(1:nnode).' Bend_Def zeros(nnode,1)];
        else
            disp('>>>> Error - insufficient columns in bend definition')
        end
    end
    if ncol_bend == 2
        Bend_Def = [Bend_Def zeros(npts,1)];
    end
    if ncol_bend > 3, disp('>>>> Error - too many columns in bend definition'), end
    masterdof = [];
    xmaster = [];
    for ibend = 1:npts
        inode = Bend_Def(ibend,1);
        masterdof = [masterdof 4*inode-3 4*inode-2];
        xnode = Bend_Def(ibend,2)*[1; -j] + Bend_Def(ibend,3)*[j; 1];
        xmaster = [xmaster; xnode];
    end
    slavedof = 1:ndof; slavedof(masterdof) = [];
    Kss = K0(slavedof,slavedof); 
    Ksm = K0(slavedof,masterdof);
    xslave = - Kss\(Ksm*xmaster);
    xbend = zeros(ndof,1); 
    xbend(slavedof) = xslave; 
    xbend(masterdof) = xmaster;
    bend_force = K0*xbend;
end
bend_force(zero_dof) = [];


% rotating moment that is not rotor spin speed dependent
% for example from PZT patches on shaft
% definition of moment is complex to give both planes
% two nodes are required - start and end of PZT patch
% hence model.force = [8 node_1 node_2 moment_mag moment_phase]
PZT_force = zeros(ndof,1);
for iforce = 1:nforce
    if Force_Def(iforce,1) == 8  % rotating moment
        node_1 = Force_Def(iforce,2);
        node_2 = Force_Def(iforce,3);
        moment_mag = Force_Def(iforce,4);
        moment_phase = Force_Def(iforce,5);
        force_dof = [4*node_1-1; 4*node_1];
        PZT_force(force_dof) = PZT_force(force_dof) + moment_mag*exp(j*moment_phase)*[j; 1];
        force_dof = [4*node_2-1; 4*node_2];
        PZT_force(force_dof) = PZT_force(force_dof) - moment_mag*exp(j*moment_phase)*[j; 1];        
    end
end 
PZT_force(zero_dof) = [];  % remove force from zeroed dof 



% calculate response
response = zeros(ndof,nspeed);
for ispeed = 1:nspeed
   [Mb,Cb,Kb,zero_dof] = bearmtx(model,Rotor_Spd(ispeed));
   M = M0 + Mb;
   K = K0 + Kb + Rotor_Spd(ispeed)*K1;
   C = C0 + Cb + Rotor_Spd(ispeed)*C1;
   force = bend_force + PZT_force + ubforce*(Rotor_Spd(ispeed)^2);
   response(dof,ispeed) = (-M(dof,dof)*(Rotor_Spd(ispeed)^2)+j*C(dof,dof)*Rotor_Spd(ispeed)+K(dof,dof))\force;
end
