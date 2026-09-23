function [time,response,speed] = runup(model,alpha,tspan,nr)
%
%  function  runup.m
%
%   [time, response, speed] = runup(model, alpha, tspan)
%
% Calculates the response during a runup using time integration 
%
%    time         is time vector
%
%    response     is the response output and is a 2 dimensional array
%                 The indices are DoFs and frequency
%
%    speed        gives the instantaneous rotor speed during runup
%
%    alpha        [a2 a1 a0], rotor angle = a2*t^2 + a1*t + a0
%
%    tspan        the time span vector for ode45
%
%    nr           is the number of degrees of freedom in the reduced model
%
%    Force_Def    gives the force definition. Unbalance only.
%
% This function is part of a MATLAB Toolbox to accompany the book
% 'Dynamics of Rotating Machinery' by MI Friswell, JET Penny, SD Garvey
% & AW Lees, published by Cambridge University Press, 2010
%

% NOTE - NO FLUID BEARINGS FOR THIS SCRIPT
% NOTE - NO SHAFT DAMPING

if nargin < 4
    nr = 0;
end

Node_Def = model.node;
Force_Def = model.force;
Bearing_Def = model.bearing;

nbearing = size(Bearing_Def,1);
const_bearing = 1;
for ib=1:nbearing
    if Bearing_Def(ib,1) > 6.5
        const_bearing = 0;
    end
end
if ~const_bearing
    disp(['>>>> Error in runup.m - only constant stiffness bearings implemented'])
    time = [];
    response = [];
    speed = [];
    return
end
    
[M0,C0,C1,K0,K1] = rotormtx(model);
[nnode,ncol_node] = size(Node_Def);
ndof = 4*nnode;

[Mb,Cb,Kb,zero_dof] = bearmtx(model,0.0);
dof = 1:ndof;
dof(zero_dof) = [];

M = M0 + Mb;
K = K0 + Kb;
C = C0 + Cb;

[nforce,ncol_force] = size(Force_Def);
ubforce = zeros(ndof,1);
jot = sqrt(-1);
for iforce = 1:nforce
    if Force_Def(iforce,1) == 1
        node = Force_Def(iforce,2);
        unbal_mag = Force_Def(iforce,3);
        unbal_phase = Force_Def(iforce,4);
        force_dof = [4*node-3; 4*node-2];
        ubforce(force_dof) = ubforce(force_dof) + unbal_mag*exp(jot*unbal_phase)*[1; -j];
    end
    if Force_Def(iforce,1) == 2
        node = Force_Def(iforce,2);
        unbal_mag = Force_Def(iforce,3);
        unbal_phase = Force_Def(iforce,4);
        force_dof = [4*node-1; 4*node];
        ubforce(force_dof) = ubforce(force_dof) + unbal_mag*exp(jot*unbal_phase)*[j; 1];
    end
end 
ubforce(zero_dof) = [];

[ndofz,junk] = size(M);
nr = round(nr);
if nr > 0 & nr < ndofz
    [eigvec,eigval] = eig(K,M);
    [eigval,isort] = sort(diag(eigval));
    eigvec = eigvec(:,isort);
    Tr = eigvec(:,1:nr);
    eigmaxr = sqrt(eigval(nr))/(2*pi);
else
    eigval = sort(eig(K,M));
    Tr = eye(ndofz,ndofz);
    eigmaxr = sqrt(eigval(ndofz))/(2*pi);
    nr = ndofz;
end
disp(['>>>> Maximum frequency of reduced system is ' num2str(eigmaxr) ' Hz'])

Mr = Tr.'*M*Tr;
Cr = Tr.'*C*Tr;
C1r = Tr.'*C1*Tr;
Kr = Tr.'*K*Tr;
fr = Tr.'*ubforce;

A = [zeros(nr,nr) eye(nr,nr); -Mr\Kr -Mr\Cr];
A1 = [zeros(nr,nr) zeros(nr,nr); zeros(nr,nr) -Mr\C1r];
B = [zeros(nr,1); Mr\fr];

options = odeset;
[time,q] = ode45(@deriv,tspan,zeros(2*nr,1),options,A,A1,B,alpha);

time = time.';
npts = length(time);
response = zeros(ndof,npts);
response(dof,:) = Tr*q(:,1:nr).';

speed = 2*alpha(1)*time + alpha(2)*ones(size(time));

return

function [qdot] = deriv(t,q,A,A1,B,alpha)

phi = alpha(1)*t*t + alpha(2)*t + alpha(3);
d_phi = 2*alpha(1)*t + alpha(2);
dd_phi = 2*alpha(1);
qdot = A*q + A1*q*d_phi + real(B*(d_phi*d_phi-j*dd_phi)*exp(j*phi));
