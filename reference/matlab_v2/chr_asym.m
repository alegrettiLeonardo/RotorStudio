function [eigenvalues,eigenvectors] = chr_asym(model,Rotor_Spd)
%
%  function  chr_asym.m
%
%   [eigenvalues,eigenvectors] = chr_asym(model,Rotor_Spd)
%
% Calculates the characteristic roots for the asymmetric rotor system at a constant
% speed. Note that even for an undamped system the characteristic roots are 
% complex (well purely imaginary)
%
%    Rotor_Spd    is a vector of rotor speeds in rad/s
%
% This may be used to plot Campbell diagrams
%
% Note that with more than rotor speed eigenvalues ends up a matrix and
% eigenvectors a 3 dimensional tensor. 
%
%
% This function is part of a MATLAB Toolbox to accompany the book
% 'Dynamics of Rotating Machinery' by MI Friswell, JET Penny, SD Garvey
% & AW Lees, published by Cambridge University Press, 2010
%


Node_Def = model.node;

% obtain model of rotor

[M0,C0,C1,K0,K1,K2] = rotorasym(model);
[nnode,ncol_node] = size(Node_Def);
ndof = 4*nnode;

% calculate eigensystem
% note there is no sorting for when the eigenvalues cross

nspeed = length(Rotor_Spd);

% sort out zeroed DoF and bearing matrix
% note fluid bearing are not allowed (since then both the
% bearing and the rotor would be asymmetric)
[Cb,Kb,K1b,zero_dof] = bearasym(model);
dof = 1:ndof;
dof(zero_dof) = [];
nzero = length(zero_dof);
ncdof = ndof - nzero;
eigenvalues = zeros(2*ncdof,nspeed);

M = M0;

if nargout == 1          % eigenvalues only required
   for i = 1:nspeed
      K = K0 + Kb + Rotor_Spd(i)*(K1+K1b) + Rotor_Spd(i)^2*K2;
      C = C0 + Cb + Rotor_Spd(i)*C1;
      AA = [zeros(ncdof,ncdof) eye(ncdof,ncdof); -M(dof,dof)\K(dof,dof) -M(dof,dof)\C(dof,dof)];
      eigenvalues_Spd = eig(AA);
      [eigenvalues_Spd,isort] = sort(eigenvalues_Spd);
      eigenvalues(:,i) = eigenvalues_Spd;
   end
end

if nargout == 2         % eigenvalues and eigenvectors required
   if nspeed==1
      eigenvectors = zeros(ndof,2*ncdof);
   else
      eigenvectors = zeros(ndof,2*ncdof,nspeed);      
   end
   for i = 1:nspeed
      K = K0 + Kb + Rotor_Spd(i)*K1 + Rotor_Spd(i)^2*K2;
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



