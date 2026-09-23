function [response,force,time] = time_fdn(model,Rotor_Spd,dt,npts,nr)
%
%  function  time_fdn.m
%
%   [response, force, time] = time_fdn(model,Rotor_Spd,dt,npts)
%
% Calculates the steady state forced response to foundation excitation of
% the rotor system at a single shaft speed in the frequency domain 
%
%    Rotor_Spd    is a single rotor speed in rad/s
%
%    response     is the response output and is a 2 dimensional array
%                 The indices are DoFs and frequency
%
%    force        is the force input to the foundation as a function of
%                 time
%
%    time         is the time points for the response output
%
%    Force_Def    = model.force
%                 gives the force definition. For foundation excitation by
%                 a half sine pulse this must be 5 in the first column. 
%                 The remainder of the row gives the relative amplitude of
%                 the forcing at each bearing DoF (must be zero for short 
%                 or long bearings). The remaining two elements give the
%                 duration and magnitude of the half sine pulse.
%
%    dt           is the time interval for the output
%
%    npts         is the number of output points
%
%    nr           is the number of degrees of freedom in the reduced model
%                 the default is no reduction
%
%
% This function is part of a MATLAB Toolbox to accompany the book
% 'Dynamics of Rotating Machinery' by MI Friswell, JET Penny, SD Garvey
% & AW Lees, published by Cambridge University Press, 2010
%

if nargin < 5 % no model reduction
    nr = 0;
end

Node_Def = model.node;
Force_Def = model.force;
Bearing_Def = model.bearing;

if length(Rotor_Spd) > 1
    disp('>>>> Error - only a single shaft speed must be defined for foundation excitation')
    disp('             using the first shaft speed only')
    Rotor_Spd = Rotor_Spd(1);
end

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
    if Force_Def(iforce,1) ~= 5, Force_Def(iforce,:) = []; end
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
if ncol_force < 2*nbearing + 2
    disp('>>>> Error - insufficient foundation force parameters defined')
    response = [];
    force = [];
    time = [];
    return
end
for ibearing = 1:nbearing
    if Bearing_Def(ibearing,1) > 2 | Bearing_Def(ibearing,1) < 9
        ibnode = Bearing_Def(ibearing,2);
        qf(4*ibnode-3) = Force_Def(2*ibearing);
        qf(4*ibnode-2) = Force_Def(2*ibearing+1);
    end
end
qf = real(qf);

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

pulse_duration = Force_Def(2*nbearing+2);

% reduce the model
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
Kr = Tr.'*K*Tr;
Mfr = Tr.'*Mf;
Cfr = Tr.'*Cf;
Kfr = Tr.'*Kf;

A = [zeros(nr,nr) eye(nr,nr); -Mr\Kr -Mr\Cr];
B2 = [zeros(nr,1); Mr\Mfr];
B1 = [zeros(nr,1); Mr\Cfr];
B0 = [zeros(nr,1); Mr\Kfr];

Time0 = dt*(0:npts-1);
force = zeros(1,npts);
npulse = floor(pulse_duration/dt) + 1;
force(1:npulse) = sin(pi*Time0(1:npulse)/pulse_duration);

options = odeset;
[time,q]=ode45(@deriv,Time0,zeros(2*nr,1),options,A,B2,B1,B0,pulse_duration);

time = time.';
response = zeros(ndof,npts);
response(dof,:) = Tr*q(:,1:nr).';

return

function [qdot] = deriv(t,q,A,B2,B1,B0,pulse_duration)

if t > pulse_duration
    qdot = A*q;
else
    om = pi/pulse_duration;
    y = sin(om*t); 
    yd = om*cos(om*t);
    ydd = -om*om*y;
    qdot = A*q + B2*ydd + B1*yd + B0*y;
end
