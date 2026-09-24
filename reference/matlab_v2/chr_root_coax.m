function [eigenvalues,eigenvectors] = chr_root_coax(model,Rotor_Spd)
%
%  function  chr_root_coax.m
%
%   [eigenvalues,eigenvectors] = chr_root_coax(model,Rotor_Spd)
%
%  Coaxial rotors
%
% Calculates the characteristic roots for the rotor system at a constant speed
% Note that even for an undamped system the characteristic roots are complex (well
% purely imaginary)
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
Rotor_Def = model.rotors;
Bearing_Def = model.bearing;

nrotor = size(Rotor_Def,1);
nbearing = size(Bearing_Def,1);

% sort out the bearing definitions between the coaxial rotors
Bear_Speed_Ratio = ones(nbearing,1); % this defines the spin speed ratio 
nlink = 0;
Link_Def = [];  % this defines the coupling between rotors
for ibearing = nbearing:-1:1
    if Bearing_Def(ibearing,1) == 7 | Bearing_Def(ibearing,1) == 8
        Bearing_node = Bearing_Def(ibearing,2);
        for irotor = 1:nrotor
            if (Bearing_node>=Rotor_Def(irotor,1)) & (Bearing_node<=Rotor_Def(irotor,2))
                Bear_Speed_Ratio(ibearing) = Rotor_Def(irotor,3);
                if abs(Rotor_Def(irotor,3)-1)>1e-6
                    disp('>>>> error in chr_root_coax.m - the speed dependent bearing properties')
                    disp('>>>> are calculated at the reference speed only')
                end
            end
        end
    end
    if Bearing_Def(ibearing,1) == 20
        Link_Def = [Link_Def; Bearing_Def(ibearing,:)];
        Bearing_Def(ibearing,:) = [];
        nlink = nlink + 1;
    end
end

% obtain model of rotor - this is exactly the same as the single rotor case
% as the nodes are different for each rotor.
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

% sort out speeds for different shafts
RelSpd = zeros(ndof,ndof);
for irotor = 1:nrotor
    n1 = Rotor_Def(irotor,1);
    n2 = Rotor_Def(irotor,2);    
    ndof_rotor = 4*(n2-n1+1); % number of degrees of freedom in rotor
    RelSpd(4*n1-3:4*n2,4*n1-3:4*n2) = Rotor_Def(irotor,3)*eye(ndof_rotor,ndof_rotor);
end
 
% add in couplings between rotors
for ilink = 1:nlink
     n1 = Link_Def(ilink,2);
     n2 = Link_Def(ilink,3);
     dof_link = [4*n1-3 4*n2-3];
     K0(dof_link,dof_link) = K0(dof_link,dof_link) + Link_Def(ilink,4)*[1 -1; -1 1];
     C0(dof_link,dof_link) = C0(dof_link,dof_link) + Link_Def(ilink,6)*[1 -1; -1 1];
     dof_link = [4*n1-2 4*n2-2];
     K0(dof_link,dof_link) = K0(dof_link,dof_link) + Link_Def(ilink,5)*[1 -1; -1 1];
     C0(dof_link,dof_link) = C0(dof_link,dof_link) + Link_Def(ilink,7)*[1 -1; -1 1];
 end      

if nargout == 1          % eigenvalues only required
   for i = 1:nspeed
      [Mb,Cb,Kb,zero_dof] = bearmtx(model,Rotor_Spd(i));
      M = M0 + Mb;
      K = K0 + Kb + Rotor_Spd(i)*RelSpd*K1;
      C = C0 + Cb + Rotor_Spd(i)*RelSpd*C1;
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
      [Mb,Cb,Kb,zero_dof] = bearmtx(model,Rotor_Spd(i));
      M = M0 + Mb;
      K = K0 + Kb + Rotor_Spd(i)*RelSpd*K1;
      C = C0 + Cb + Rotor_Spd(i)*RelSpd*C1;
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



