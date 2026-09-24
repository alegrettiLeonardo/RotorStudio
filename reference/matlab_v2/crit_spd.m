function [critical_speeds,mode_shapes] = crit_spd(model,NX,damped_NF,number_criticals,max_iterations,convergence_tol,initial_estimates)
%
%  function  crit_spd.m
%
%   [critical_speeds,mode_shape] = crit_spd(model,NX,damped_NF,
%      number_criticals,max_iterations,convergence_tol,initial_estimates)
%
% This functions calculates the critical speeds for the rotor system 
% either using the direct approach (for constant stiffness bearings) or 
% by iteration (possible for all cases). The critical speeds are defined
% when the rotor spin speed equals a natural frequency
%
%   NX                  shaft order to calculate unbalance
%                       (=1 for unbalance, which is default)
%
%   damped_NF           determines whether the damped natural frequencies
%                       (default, damped_NF=1) or undamped natural 
%                       frequencies (damped_NF=0) are used
%
%   number_criticals    number of criticals to compute (default=5)
%
%   max_iterations      maximum iterations to try (default=20)
%
%   convergence_tol     relative change in critical speed from one
%                       iteration to next for convergence (default=1e-6)
%
%   initial_estimates   initial estimate of critical speeds - only used 
%                       for iterative method and critical speeds closest
%                       to these initial estimates are obtained
%
%
% This function is part of a MATLAB Toolbox to accompany the book
% 'Dynamics of Rotating Machinery' by MI Friswell, JET Penny, SD Garvey
% & AW Lees, published by Cambridge University Press, 2010
%


% first sort out which method to use
%
%  imethod = 1    direct
%  imethod = 2    iterative, choose eigenvalue by number
%  imethod = 3    iterative, choose eigenvalue by closeness to current


% only methods 1 and 2 implemented so far
% =======================================


if nargin==7, 
    imethod = 3;
    number_criticals = length(initial_estimates);
end
if nargin==6, imethod = 2; end
% check to see if there are any speed dependent bearings
Bearing_Def = model.bearing;
[nbearing,ncol_bearing] = size(Bearing_Def);
const_bearing = 1;
for i=1:nbearing
    bearing_type = Bearing_Def(i,1) ;
    if (bearing_type==7) | (bearing_type==8) 
        const_bearing = 0;
    end
end
if (nargin<6)
    if const_bearing
        imethod = 1;
    else
        imethod = 2;
    end
end

% add in defaults
if nargin < 2, NX = 1; end
if nargin < 3, damped_NF = 1; end
if nargin < 4, number_criticals = 5; end
if nargin < 5, max_iterations = 20; end
if nargin < 6, convergence_tol = 1e-6; end    


% make sure NX is within a reasonable range
NX = abs(NX);
NX = max([NX 0.2]);


Node_Def = model.node;
[nnode,ncol_node] = size(Node_Def);
ndof = 4*nnode;

% The direct method

if imethod==1
    
    [M0,C0,C1,K0,K1] = rotormtx(model);
    [Mb,Cb,Kb,zero_dof] = bearmtx(model,0);
    dof = 1:ndof;
    dof(zero_dof) = [];
    nzero = length(zero_dof);
    ncdof = ndof - nzero;
    jot = sqrt(-1);
    MM = -(NX^2)*(M0 + Mb) + jot*NX*C1;
    CC = jot*NX*(C0 + Cb) + K1;
    KK = K0 + Kb;
    AA = [zeros(ncdof,ncdof) eye(ncdof,ncdof); -MM(dof,dof)\KK(dof,dof) -MM(dof,dof)\CC(dof,dof)];
    if nargout<=1
        eigenvalues = sort(eig(AA));
    end
    if nargout==2   
        [eigenvectors,eigenvalues] = eig(AA);
        [eigenvalues,isort] = sort(diag(eigenvalues));
        eigenvectors = eigenvectors(:,isort);
        mode_shapes = zeros(ndof,number_criticals);
        mode_shapes(dof,:) = eigenvectors(1:ncdof,(1:2:2*number_criticals));       
    end
    if damped_NF
        critical_speeds = abs(real(eigenvalues(1:2:2*number_criticals)));
    else
        critical_speeds = abs(eigenvalues(1:2:2*number_criticals));
    end
    
end



if imethod==2
    
    % obtain model of rotor
    [M0,C0,C1,K0,K1] = rotormtx(model);
    
    % calculate critical speeds - first sort out zeroed DoF
    Rotor_Spd = 2*pi*500/60;  % start with initial guess of 500 rev/min
    [Mb,Cb,Kb,zero_dof] = bearmtx(model,Rotor_Spd);
    dof = 1:ndof;
    dof(zero_dof) = [];
    nzero = length(zero_dof);
    ncdof = ndof - nzero;
    M = M0 + Mb;
    K = K0 + Kb + Rotor_Spd*K1;
    C = C0 + Cb + Rotor_Spd*C1;
    AA = [zeros(ncdof,ncdof) eye(ncdof,ncdof); -M(dof,dof)\K(dof,dof) -M(dof,dof)\C(dof,dof)];
    eigenvalues_initial = sort(eig(AA));
    
    critical_speeds = zeros(number_criticals,1);
    for icritical = 1:number_criticals
        ieig = 2*icritical-1;
        rel_change = 1;
        iteration = 0;
        if damped_NF>0.5
            critical_i = abs(imag(eigenvalues_initial(ieig)))/NX;
        else
            critical_i = abs(eigenvalues_initial(ieig))/NX;
        end
        %  disp([icritical iteration 30*critical_i/pi])
        while (rel_change>convergence_tol) & (iteration<max_iterations)
            [Mb,Cb,Kb,zero_dof] = bearmtx(model,critical_i);
            M = M0 + Mb;
            K = K0 + Kb + critical_i*K1;
            C = C0 + Cb + critical_i*C1;
            AA = [zeros(ncdof,ncdof) eye(ncdof,ncdof); -M(dof,dof)\K(dof,dof) -M(dof,dof)\C(dof,dof)];
            eigenvalues = sort(eig(AA));
            critical_i_old = critical_i;
            if damped_NF>0.5
                critical_i = abs(imag(eigenvalues(ieig)))/NX;
            else
                critical_i = abs(eigenvalues(ieig))/NX;
            end
            if critical_i_old == 0
                rel_change = 2*convergence_tol;
            else
                rel_change = abs( (critical_i - critical_i_old)/critical_i_old );
            end
            iteration = iteration + 1;
            %     disp([icritical iteration 30*critical_i/pi])
        end
        critical_speeds(icritical) = critical_i;
    end
    
    % Calculate the eigenvectors corresponding to the critical speeds if
    % required
    
    if nargout == 2
        mode_shapes = zeros(ndof,number_criticals);
        for icritical = 1:number_criticals
            [Mb,Cb,Kb,zero_dof] = bearmtx(model,critical_speeds(icritical));
            M = M0 + Mb;
            K = K0 + Kb + critical_speeds(icritical)*K1;
            C = C0 + Cb + critical_speeds(icritical)*C1;
            AA = [zeros(ncdof,ncdof) eye(ncdof,ncdof); -M(dof,dof)\K(dof,dof) -M(dof,dof)\C(dof,dof)];
            [eigenvectors_i,eigenvalues] = eig(AA);
            [eigenvalues,isort] = sort(diag(eigenvalues));
            eigenvectors_i = eigenvectors_i(:,isort);
            mode_shapes(dof,icritical) = eigenvectors_i(1:ncdof,2*icritical-1);
        end
    end
    
end




if imethod==3
    
    % obtain model of rotor
    [M0,C0,C1,K0,K1] = rotormtx(model);
    
    % calculate critical speeds - first sort out zeroed DoF
    Rotor_Spd = 2*pi*500/60;  % assume non-zero speed, just in case of fluid bearings
    [Mb,Cb,Kb,zero_dof] = bearmtx(model,Rotor_Spd);
    dof = 1:ndof;
    dof(zero_dof) = [];
    nzero = length(zero_dof);
    ncdof = ndof - nzero;
    
    critical_speeds = zeros(number_criticals,1);
    for icritical = 1:number_criticals
        rel_change = 1;
        iteration = 0;
        critical_i = abs(initial_estimates(icritical));
        while (rel_change>convergence_tol) & (iteration<max_iterations)
            [Mb,Cb,Kb,zero_dof] = bearmtx(model,critical_i);
            M = M0 + Mb;
            K = K0 + Kb + critical_i*K1;
            C = C0 + Cb + critical_i*C1;
            AA = [zeros(ncdof,ncdof) eye(ncdof,ncdof); -M(dof,dof)\K(dof,dof) -M(dof,dof)\C(dof,dof)];
            eigenvalues = sort(eig(AA));
            critical_i_old = critical_i;
            if damped_NF>0.5
                critical_est = abs(imag(eigenvalues))/NX;
            else
                critical_est = abs(eigenvalues)/NX;
            end
            [delta_c,index_c] = min( abs( critical_est - initial_estimates(icritical) ) );
            critical_i = critical_est(index_c);  
            if critical_i_old == 0
                rel_change = 2*convergence_tol;
            else
                rel_change = abs( (critical_i - critical_i_old)/critical_i_old );
            end
            iteration = iteration + 1;
            %     disp([icritical iteration 30*critical_i/pi])
        end
        critical_speeds(icritical) = critical_i;
    end
    
    % Calculate the eigenvectors corresponding to the critical speeds if
    % required
    
    if nargout == 2
        mode_shapes = zeros(ndof,number_criticals);
        for icritical = 1:number_criticals
            [Mb,Cb,Kb,zero_dof] = bearmtx(model,critical_speeds(icritical));
            M = M0 + Mb;
            K = K0 + Kb + critical_speeds(icritical)*K1;
            C = C0 + Cb + critical_speeds(icritical)*C1;
            AA = [zeros(ncdof,ncdof) eye(ncdof,ncdof); -M(dof,dof)\K(dof,dof) -M(dof,dof)\C(dof,dof)];
            [eigenvectors_i,eigenvalues] = eig(AA);
            [eigenvalues,isort] = sort(diag(eigenvalues));
            eigenvectors_i = eigenvectors_i(:,isort);
            if damped_NF>0.5
                critical_est = abs(imag(eigenvalues))/NX;
            else
                critical_est = abs(eigenvalues)/NX;
            end
            [delta_c,index_c] = min( abs( critical_est - critical_speeds(icritical) ) );           
            mode_shapes(dof,icritical) = eigenvectors_i(1:ncdof,index_c);
        end
    end
    
end



