function [Cb,Kb,K1b,zero_dof] = bearasym(model)
%
%  function bearasym.m
%
%     [Mb,Cb,Kb,zero_dof] = bearasym(model)
%
% calculates the mass, stiffness and damping matrices for the bearings
% for the asymetrical rotor case - bearings must be symetrical
%
% zero_dof indicates the degrees of freedom that should be constrained
% for stiff bearings (bearing types 1 and 2)
%
%
% This function is part of a MATLAB Toolbox to accompany the book
% 'Dynamics of Rotating Machinery' by MI Friswell, JET Penny, SD Garvey
% & AW Lees, published by Cambridge University Press, 2010
%

Node_Def = model.node;
Bearing_Def = model.bearing;

% determine the number of degrees of freedom and initialise matrices

[no_node,ncol_node] = size(Node_Def);
ndof = 4*no_node;
[nbearing,ncol_bearing] = size(Bearing_Def);
Cb  = zeros(ndof,ndof);
Kb  = zeros(ndof,ndof);
K1b = zeros(ndof,ndof);
zero_dof = [];

% go through each bearing, and deciding on bearing type include model

for i = 1:nbearing
    
    Bearing_Type = round(Bearing_Def(i,1));
    if (Bearing_Type<1) | (Bearing_Type>4)
        disp(['>>>> Error - bearing type ' num2str(Bearing_Type) ' not implemented - bearing ignored'])
    end
    Kb1 = zeros(4,4);
    K1b1 = zeros(4,4);
    Cb1 = zeros(4,4);
    
    if Bearing_Type == 1       % short, stiff bearing - pinned boundary condition
        n1 = Bearing_Def(i,2);
        zero_dof = [zero_dof 4*n1-3 4*n1-2];
    end
    
    if Bearing_Type == 2       % long, stiff bearing - clamped boundary condition
        n1 = Bearing_Def(i,2);
        zero_dof = [zero_dof 4*n1-3:4*n1];
    end
    
    if Bearing_Type == 3       % constant stiffness and damping, diagonal, no rotations
        if ncol_bearing<6, disp('>>>> Error - too few columns in bearing definition matrix for bearing type 3'), end
        if Bearing_Def(i,3)~=Bearing_Def(i,4), disp('>>>> Error - bearings must be symmetric'), end
        if Bearing_Def(i,5)~=Bearing_Def(i,6), disp('>>>> Error - bearings must be symmetric'), end
        Kb1 = diag( [Bearing_Def(i,3) Bearing_Def(i,4) 0 0] );
        Cb1 = diag( [Bearing_Def(i,5) Bearing_Def(i,6) 0 0] );
        K1b1(1,2) = -Bearing_Def(i,5); K1b1(2,1) = Bearing_Def(i,5);
    end
    
    if Bearing_Type == 4       % constant stiffness and damping, diagonal
        if ncol_bearing<10, disp('>>>> Error - too few columns in bearing definition matrix for bearing type 4'), end
        if Bearing_Def(i,3)~=Bearing_Def(i,4), disp('>>>> Error - bearings must be symmetric'), end
        if Bearing_Def(i,5)~=Bearing_Def(i,6), disp('>>>> Error - bearings must be symmetric'), end
        if Bearing_Def(i,7)~=Bearing_Def(i,8), disp('>>>> Error - bearings must be symmetric'), end
        if Bearing_Def(i,9)~=Bearing_Def(i,10), disp('>>>> Error - bearings must be symmetric'), end
        Kb1 = diag( [Bearing_Def(i,3) Bearing_Def(i,4) Bearing_Def(i,5) Bearing_Def(i,6)] );
        Cb1 = diag( [Bearing_Def(i,7) Bearing_Def(i,8) Bearing_Def(i,9) Bearing_Def(i,10)] );
        K1b1(1,2) = -Bearing_Def(i,7); K1b1(2,1) = Bearing_Def(i,7);
        K1b1(3,4) = -Bearing_Def(i,9); K1b1(2,1) = Bearing_Def(i,9);
    end
    
    nnode = Bearing_Def(i,2);
    dof = (4*nnode-3):4*nnode;
    Kb(dof,dof) = Kb(dof,dof) + Kb1;
    Cb(dof,dof) = Cb(dof,dof) + Cb1;
    K1b(dof,dof) = K1b(dof,dof) + K1b1;
    
end
