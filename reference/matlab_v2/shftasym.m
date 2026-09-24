function [M0e,C1e,K0e,K2e] = shftasym(Shaft_Type,L,EIx,EIy,Phix,Phiy,rhoA,rhoI,AxialForce)
%
%  function shftasym.m
%
%     [M0e,C1e,K0e,K2e] = shftasym(Shaft_Type,L,EIx,EIy,Phix,Phiy,rhoA,inertia,AxialForce)
%
%  This function generates the element matrices for an asymmetric shaft
%  element in rotating co-ordinates.
%
%  Both Euler and	Timoshenko beam theory included
%
%    K0e  is the returned stiffness matrix
%    M0e  is the returned mass matrix
%    C1e  is the returned gyroscopic matrix
%         (also contributions from transformed mass matrix)
%    K2e  is the returned speed squared contribution to the 
%         stiffness matrix (from transformed mass and
%         gyroscopic matrices)
%
%    Shaft_Type    determines which effects are modelled 
%    L             is the length of the element
%    EIx           is the flexural rigidity in the x plane
%    EIy           is the flexural rigidity in the y plane
%    Phix          is the non-dimensional shear constant = 12*E*I/(kappa*G*A*L^2)
%    Phiy          is the non-dimensional shear constant = 12*E*I/(kappa*G*A*L^2)
%    rhoA          is the mass density X area = mass/unit length
%    rhoI          is the product of mass density and second moment of area of
%                  the element for mass and gyroscopic matrix calculations - 
%                  this is assumed to be equal in both directions
%    AxialForce    is the axial load on the shaft element
%
% The shaft type determines which effects are modelled, as below
%
%     Shaft_Type         Shear   Rotary Inertia   Gyroscopic
%        11 (Euler)                                   X
%        12                X           X              X
%        13                X           X
%        14                X                          X
%        15                            X              X
%        16                X
%        17                            X
%        18
%
% This function is part of a MATLAB Toolbox to accompany the book
% 'Dynamics of Rotating Machinery' by MI Friswell, JET Penny, SD Garvey
% & AW Lees, published by Cambridge University Press, 2010
%

% Currently it is assumed that the principle axis for the
% element stiffness is the same for all elements.

% determine effects to include

if nargin < 8, AxialForce = 0; end   % no axial force

include_shear_effects = 1;
if (Shaft_Type==11) | (Shaft_Type==15) | (Shaft_Type==17) | (Shaft_Type==18)
   include_shear_effects = 0; 
end
include_rotary_inertia = 1;
if (Shaft_Type==11) | (Shaft_Type==14) | (Shaft_Type==16) | (Shaft_Type==18)
   include_rotary_inertia = 0; 
end
include_gyroscopic = 1;
if (Shaft_Type==13) | (Shaft_Type==16) | (Shaft_Type==17) | (Shaft_Type==18)
   include_gyroscopic = 0; 
end

if (include_shear_effects==0)
   Phix = 0; 
   Phiy = 0; 
end

% stiffness element
K0xe = [12          6*L   -12           6*L;
       6*L (4+Phix)*L*L  -6*L  (2-Phix)*L*L;
       -12         -6*L    12          -6*L;
       6*L (2-Phix)*L*L  -6*L  (4+Phix)*L*L];
K0xe = EIx*K0xe/( (1+Phix)*L^3 );
K0ye = [12         -6*L   -12          -6*L;
      -6*L (4+Phiy)*L*L   6*L  (2-Phiy)*L*L;
       -12          6*L    12           6*L;
      -6*L (2-Phiy)*L*L   6*L  (4+Phiy)*L*L];
K0ye = EIy*K0ye/( (1+Phiy)*L^3 );
K0e = zeros(8,8);
K0e([1 4 5 8],[1 4 5 8]) = K0xe;
K0e([2 3 6 7],[2 3 6 7]) = K0ye;

% element stiffness matrix due to an axial load
if AxialForce ~= 0
   k1 = 72 + 120*Phix + 60*Phix^2;
   k2 = 6*L;
   k3 = (8 + 10*Phix + 5*Phix^2)*L^2;
   k4 = (-2 - 10*Phix - 5*Phix^2)*L^2;
   KFxe = [k1  k2 -k1  k2;
           k2  k3 -k2  k4;
          -k1 -k2  k1 -k2; 
           k2  k4 -k2  k3];
   KFxe = AxialForce*KFxe/(60*L*(1+Phix)^2);
   k1 = 72 + 120*Phiy + 60*Phiy^2;
   k2 = 6*L;
   k3 = (8 + 10*Phiy + 5*Phiy^2)*L^2;
   k4 = (-2 - 10*Phiy - 5*Phiy^2)*L^2;
   KFye = [k1 -k2 -k1 -k2;
          -k2  k3  k2  k4;
          -k1  k2  k1  k2;
          -k2  k4  k2  k3];
   KFye = AxialForce*KFye/(60*L*(1+Phiy)^2);
   Kre([1 4 5 8],[1 4 5 8]) = Kre([1 4 5 8],[1 4 5 8]) + KFxe;
   Kre([2 3 6 7],[2 3 6 7]) = Kre([2 3 6 7],[2 3 6 7]) + KFye;
end

% element mass matrix
% note that Phix must equal Phiy, otherwise the time dependence
% due to the transformation between the rotating and stationary
% frames remains - leading to an equation with parametric excitation.
% Here we neglect shear in the element mass matrix
% Note we also get a contribution to the C1 matrix
m1 = 156;
m2 = 22*L;
m3 = 54;
m4 = -13*L;
m5 = 4*L^2;
m6 = -3*L^2;
M0e = [ m1    0    0   m2   m3    0    0   m4;
         0   m1  -m2    0    0   m3  -m4    0;
         0  -m2   m5    0    0   m4   m6    0;
        m2    0    0   m5  -m4    0    0   m6;
        m3    0    0  -m4   m1    0    0  -m2; 
         0   m3   m4    0    0   m1   m2    0;
         0  -m4   m6    0    0   m2   m5    0;
        m4    0    0   m6  -m2    0    0   m5];
M0e = rhoA*L*M0e/420;
K2e = -M0e;
C1e = [0 -m1  m2   0   0 -m3  m4   0;
      m1   0   0  m2  m3   0   0  m4;
     -m2   0   0 -m5  m4   0   0 -m6;
       0 -m2  m5   0   0  m4  m6   0;
       0 -m3 -m4   0   0 -m1 -m2   0;
      m3   0   0 -m4  m1   0   0 -m2;
     -m4   0   0 -m6  m2   0   0 -m5;
       0 -m4  m6   0   0  m2  m5   0];
C1e = rhoA*L*C1e/210;
 
% include the rotary inertia effects in the mass matrix
% note there is also a contribution to the C1e matrix
if (include_rotary_inertia~=0)
   m7 = 36;
   m8 = 3*L;
   m9 = 4*L^2;
   m10 = -L^2;
   Ms =  [ m7    0    0   m8  -m7    0    0   m8;
            0   m7  -m8    0    0  -m7  -m8    0;
            0  -m8   m9    0    0   m8  m10    0;
           m8    0    0   m9  -m8    0    0  m10;
          -m7    0    0  -m8   m7    0    0  -m8;
            0  -m7   m8    0    0   m7   m8    0;
            0  -m8  m10    0    0   m8   m9    0;
           m8    0    0  m10  -m8    0    0   m9];
   Ms = rhoI*Ms/(30*L);
   M0e = M0e + Ms;
   Cs =  [0 -m7  m8    0   0  m7  m8    0;
         m7   0   0   m8 -m7   0   0   m8;
        -m8   0   0  -m9  m8   0   0 -m10;
          0 -m8  m9    0   0  m8 m10    0;
          0  m7 -m8    0   0 -m7 -m8    0;
        -m7   0   0  -m8  m7   0   0  -m8;
        -m8   0   0 -m10  m8   0   0  -m9;
          0 -m8 m10    0   0  m8  m9    0];
   Cs = rhoI*Ms/(15*L);
   C1e = C1e + Cs;
end

% element gyroscopic matrix
% shear and rotary inrtia effects neglected in gyroscopic matrix
if (include_gyroscopic==1)
   k1 = 36;
   k2 = 3*L;
   k3 = 4*L^2;
   k4 = -L^2;
   Ge =  [  0  -k1   k2    0    0   k1   k2    0;
           k1    0    0   k2  -k1    0    0   k2;   
          -k2    0    0  -k3   k2    0    0  -k4;
            0  -k2   k3    0    0   k2   k4    0;
            0   k1  -k2    0    0  -k1  -k2    0;
          -k1    0    0  -k2   k1    0    0  -k2;
          -k2    0    0  -k4   k2    0    0  -k3;
            0  -k2   k4    0    0   k2   k3    0];
   C1e = C1e - rhoI*Ge/(15*L);
   G1e = [ k1    0    0   k2  -k1    0    0   k2;
            0   k1  -k2    0    0  -k1  -k2    0;
            0  -k2   k3    0    0   k4   k4    0;
           k2    0    0   k3  -k4    0    0   k4;
          -k1    0    0  -k2   k1    0    0  -k2; 
            0  -k1   k2    0    0   k1   k2    0;
            0  -k2   k4    0    0   k2   k3    0;
           k2    0    0   k4  -k2    0    0   k3];
   K2e = K2e + 2*rhoI*G1e/(15*L);
end
   


