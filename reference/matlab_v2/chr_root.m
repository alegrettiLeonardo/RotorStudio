function [eigenvalues,eigenvectors,kappa,eccentricity] = chr_root(model,Rotor_Spd)
%
%  function  chr_root.m
%
%   [eigenvalues,eigenvectors,kappa] = chr_root(model,Rotor_Spd)
%
% Calculates the characteristic roots for the rotor system at a constant speed
% Note that even for an undamped system the characteristic roots are complex (well
% purely imaginary)
%
%    Rotor_Spd    is a vector of rotor speeds in rad/s
%
% This may be used to plot Campbell diagrams
%
% Note that with more than one rotor speed eigenvalues ends up a matrix and
% eigenvectors a 3 dimensional tensor.
%
% kappa   gives the orbit shape (ratio of ellipse semi-axes) and is positive
%         for forward whirl and negative for backward whirl
%
% eccentricity  gives the eccentricity of the fluid bearings at all spin
%               speeds. Each row represents a bearing, in the order given 
%               in the bearing definition and bearing that are not fluid
%               bearings have a zero eccentricity
%
%
% This function is part of a MATLAB Toolbox to accompany the book
% 'Dynamics of Rotating Machinery' by MI Friswell, JET Penny, SD Garvey
% & AW Lees, published by Cambridge University Press, 2010
%

Node_Def = model.node;
Bearing_Def = model.bearing;
[nbearing,ncol_bearing] = size(Bearing_Def);

% obtain model of rotor

[M0,C0,C1,K0,K1] = rotormtx(model);
[nnode,ncol_node] = size(Node_Def);
ndof = 4*nnode;

% calculate eigensystem
% note no sorting when the eigenvalues cross - we need sorting based on the MAC
% or similar

nspeed = length(Rotor_Spd);

% sort out zeroed DoF
[Mb,Cb,Kb,zero_dof] = bearmtx(model,Rotor_Spd(1));
dof = 1:ndof;
dof(zero_dof) = [];
nzero = length(zero_dof);
ncdof = ndof - nzero;
eigenvalues = zeros(2*ncdof,nspeed);

if nargout == 1          % eigenvalues only required
   for i = 1:nspeed
      [Mb,Cb,Kb,zero_dof] = bearmtx(model,Rotor_Spd(i));
      M = M0 + Mb;
      K = K0 + Kb + Rotor_Spd(i)*K1;
      C = C0 + Cb + Rotor_Spd(i)*C1;
      AA = [zeros(ncdof,ncdof) eye(ncdof,ncdof); -M(dof,dof)\K(dof,dof) -M(dof,dof)\C(dof,dof)];
      eigenvalues_Spd = eig(AA);
      [eigenvalues_Spd,isort] = sort(eigenvalues_Spd);
      eigenvalues(:,i) = eigenvalues_Spd;
   end
end

if nargout >= 2         % eigenvalues and eigenvectors required
   if nspeed==1
      eigenvectors = zeros(ndof,2*ncdof);
   else
      eigenvectors = zeros(ndof,2*ncdof,nspeed);      
   end
   eccentricity = zeros(nbearing,nspeed);
   for i = 1:nspeed
      [Mb,Cb,Kb,zero_dof,eccentricity_i] = bearmtx(model,Rotor_Spd(i));
      eccentricity(:,i) = eccentricity_i;
      M = M0 + Mb;
      K = K0 + Kb + Rotor_Spd(i)*K1;
      C = C0 + Cb + Rotor_Spd(i)*C1;
      AA = [zeros(ncdof,ncdof) eye(ncdof,ncdof); -M(dof,dof)\K(dof,dof) -M(dof,dof)\C(dof,dof)];
      [eigenvectors_Spd,eigenvalues_Spd] = eig(AA);
      [eigenvalues_Spd,isort] = sort(diag(eigenvalues_Spd));
      eigenvectors_Spd = eigenvectors_Spd(:,isort);
      eigenvalues(:,i) = eigenvalues_Spd;
      if nspeed == 1
         eigenvectors(dof,:) = eigenvectors_Spd(1:ncdof,:);
      else
         eigenvectors(dof,:,i) = eigenvectors_Spd(1:ncdof,:);
      end
   end
end

if nargout >= 3         % kappa also required
    if nspeed==1
        kappa = zeros(ndof,2*ncdof);
    else
        kappa = zeros(ndof,2*ncdof,nspeed);
    end
    for i = 1:nspeed        % for each speed
        for id = 1:2*ncdof  % for each eigenvector
            if nspeed == 1
                evector = eigenvectors(:,id);
            else
                evector = eigenvectors(:,id,i);
            end
            kk = whirl(evector(1:2:ndof),evector(2:2:ndof));
            if imag(eigenvalues(id,i)) < 0
                kk = -kk;
            end
            if nspeed == 1
                kappa(1:2:ndof,id) = kk;
                kappa(2:2:ndof,id) = kk;
            else
                kappa(1:2:ndof,id,i) = kk;
                kappa(2:2:ndof,id,i) = kk;
            end
        end
    end
end
