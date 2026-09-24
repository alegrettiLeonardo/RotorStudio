function [M0,C0,C1,K0,K1,K2] = rotorasym(model)
%
%  function rotorasym.m
%
%     [M0,C0,C1,K0,K1,K2] = rotorasym(model)
%
% calculates the mass, stiffness and other matrices for the shaft
% and discs - for an asymmetric shaft
%
%
% This function is part of a MATLAB Toolbox to accompany the book
% 'Dynamics of Rotating Machinery' by MI Friswell, JET Penny, SD Garvey
% & AW Lees, published by Cambridge University Press, 2010
%

Node_Def = model.node;
Shaft_Def = model.shaft;
Disc_Def = model.disc;

% determine the number of degrees of freedom and initialise matrices

[nnode,ncol_node] = size(Node_Def);
ndof = 4*nnode;
if ncol_node == 1
   Node_Def = [(1:nnode)' zeros(nnode,2) Node_Def];
end
if ncol_node == 2
   Node_Def = [Node_Def(:,1) zeros(nnode,2) Node_Def(:,2)];
end

M0 = zeros(ndof,ndof);
K0 = zeros(ndof,ndof);
K1 = zeros(ndof,ndof);
K2 = zeros(ndof,ndof);
C0 = zeros(ndof,ndof);
C1 = zeros(ndof,ndof);

[nshaft,ncol_shaft] = size(Shaft_Def);
[ndisc,ncol_disc] = size(Disc_Def);


% add shaft elements into matrices

for i = 1:nshaft
   Shaft_Type = round(Shaft_Def(i,1));
   if (Shaft_Type>10.5) & (Shaft_Type<18.5)    % asymmetric shaft
      n1 = Shaft_Def(i,2);
      n2 = Shaft_Def(i,3);
      dof = [4*n1-3:4*n1 4*n2-3:4*n2];
      Le = Node_Def(n2,4) - Node_Def(n1,4);
      EIx = Shaft_Def(i,4);
      EIy = Shaft_Def(i,5);
      Phix = Shaft_Def(i,6);
      Phiy = Shaft_Def(i,7);
      rhoA = Shaft_Def(i,8);
      rhoI = Shaft_Def(i,9);
      if ncol_shaft < 10
         damping_factor = 0;  % proportional damping
      else
         damping_factor = Shaft_Def(i,10);
      end   
      if ncol_shaft < 11
         Axial_Force = 0;  % Axial Force
      else
         Axial_Force = Shaft_Def(i,11);
      end   
   elseif (Shaft_Type>0.5) & (Shaft_Type<8.5)    % circular shaft
      n1 = Shaft_Def(i,2);
      n2 = Shaft_Def(i,3);
      dof = [4*n1-3:4*n1 4*n2-3:4*n2];
      Le = Node_Def(n2,4) - Node_Def(n1,4);
      outer_diameter = Shaft_Def(i,4);
      inner_diameter = Shaft_Def(i,5);
      rho = Shaft_Def(i,6);
      E = Shaft_Def(i,7);
      inertia = 0.015625*pi*(outer_diameter^4-inner_diameter^4);
      rhoI = rho*inertia;
      EIx = E*inertia;
      EIy = E*inertia;
      A = 0.25*pi*(outer_diameter^2-inner_diameter^2);
      rhoA = rho*A;
      if ncol_shaft < 8  % shear effects not included
         Phix = 0;
         Phiy = 0;
      else
         G = Shaft_Def(i,8);
         Poisson = 0.5*(E/G) - 1;
         r = inner_diameter/outer_diameter;
         r2 = r*r; r12 = (1+r2)^2;
         Kappa = 6*r12*(1+Poisson)/(r12*(7+6*Poisson)+r2*(20+12*Poisson));  % see Cowper, J. Applied Mechanics, Vol. 33, pp. 335-340, 1966
         Phix = 12*E*inertia/(G*Kappa*A*Le*Le);
         Phiy = Phix;
      end   
      if ncol_shaft < 9
         damping_factor = 0;  % proportional damping
      else
         damping_factor = Shaft_Def(i,9);
      end   
      if ncol_shaft < 10
         Axial_Force = 0;  % Axial Force
      else
         Axial_Force = Shaft_Def(i,10);
      end   
      Shaft_Type = Shaft_Type + 10;
   else
      error_msg = ['>>>>  error in shaft element type - shaft element number ' num2str(i) ' ignored']
      disp(error_msg)
   end
   [M0e,C1e,K0e,K2e] = shftasym(Shaft_Type,Le,EIx,EIy,Phix,Phiy,rhoA,rhoI,Axial_Force);
   M0(dof,dof) = M0(dof,dof) + M0e;
   C0(dof,dof) = C0(dof,dof) + damping_factor*K0e;  % proportional damping
   C1(dof,dof) = C1(dof,dof) + C1e;
   K0(dof,dof) = K0(dof,dof) + K0e;
   K2(dof,dof) = K2(dof,dof) + K2e;
end


% add contributions from the discs

if ndisc == 0, return, end

for i = 1:ndisc
   Disk_Type = round(Disc_Def(i,1));
   if Disk_Type == 1 | Disk_Type == 3     
      n1 = Disc_Def(i,2);
      rho = Disc_Def(i,3);
      thickness = Disc_Def(i,4);
      outer_diameter = Disc_Def(i,5);
      if ncol_disc == 6
         inner_diameter = Disc_Def(i,6);  
      else
         inner_diameter = 0;  
      end   
      Mdisc = 0.25*rho*pi*thickness*(outer_diameter^2-inner_diameter^2);
      Idx = 0.015625*rho*pi*thickness*(outer_diameter^4-inner_diameter^4) + Mdisc*(thickness^2)/12;
      Idy = Idx;
      Ip = 0.03125*rho*pi*thickness*(outer_diameter^4-inner_diameter^4);
   end
   if Disk_Type == 2 | Disk_Type == 4
      n1 = Disc_Def(i,2);
      Mdisc = Disc_Def(i,3);
      Idx = Disc_Def(i,4);
      Idy = Idx;
      if Disk_Type == 2, Ip = Disc_Def(i,5); end
   end
   if Disk_Type == 5 | Disk_Type == 6
      n1 = Disc_Def(i,2);
      Mdisc = Disc_Def(i,3);
      Idx = Disc_Def(i,4);
      Idy = Disc_Def(i,5);
      if Disk_Type == 5, Ip = Disc_Def(i,6); end
   end   
   if Disk_Type == 1 | Disk_Type == 2 | Disk_Type == 5 
      dof = (4*n1-3):4*n1;
      M0(dof,dof) = M0(dof,dof) + diag( [Mdisc Mdisc Idx Idy] );
      K2(dof,dof) = K2(dof,dof) - diag( [Mdisc Mdisc Idx Idy] );
      C1(dof,dof) = C1(dof,dof) + 2*[0 -Mdisc 0 0; Mdisc 0 0 0; 0 0 0 -Idx; 0 0 Idy 0];
      dof1 = [4*n1-1 4*n1];
      C1(dof1,dof1) = C1(dof1,dof1) + [0 Ip; -Ip 0];  %CHECK SIGNS FOR GYRO TERMS
      K2(dof1,dof1) = K2(dof1,dof1) + [Ip 0; 0 Ip];
   elseif Disk_Type == 3 | Disk_Type == 4 | Disk_Type == 6   % gyroscopic effects ignored
      dof = (4*n1-3):4*n1;
      M0(dof,dof) = M0(dof,dof) + diag( [Mdisc Mdisc Idx Idy] );
      K2(dof,dof) = K2(dof,dof) - diag( [Mdisc Mdisc Idx Idy] );
      C1(dof,dof) = C1(dof,dof) + 2*[0 -Mdisc 0 0; Mdisc 0 0 0; 0 0 0 -Idx; 0 0 Idy 0];
   else
      error_msg = ['>>>>  error in disc type - disc number ' num2str(i) ' ignored']
      disp(error_msg)
   end
end
