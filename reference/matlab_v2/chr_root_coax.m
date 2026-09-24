function [eigenvalues,eigenvectors] = chr_root_coax(model,Rotor_Spd)
Node_Def=model.node;Rotor_Def=model.rotors;Bearing_Def=model.bearing;nrotor=size(Rotor_Def,1);nbearing=size(Bearing_Def,1);
Bear_Speed_Ratio=ones(nbearing,1);nlink=0;Link_Def=[];
for ibearing=nbearing:-1:1
 if Bearing_Def(ibearing,1)==7 | Bearing_Def(ibearing,1)==8
  Bearing_node=Bearing_Def(ibearing,2);for irotor=1:nrotor,if Bearing_node>=Rotor_Def(irotor,1)&Bearing_node<=Rotor_Def(irotor,2),Bear_Speed_Ratio(ibearing)=Rotor_Def(irotor,3);end,end
 end
 if Bearing_Def(ibearing,1)==20,Link_Def=[Link_Def;Bearing_Def(ibearing,:)];Bearing_Def(ibearing,:)=[];nlink=nlink+1;end
end
[M0,C0,C1,K0,K1]=rotormtx(model);[nnode,ncol_node]=size(Node_Def);ndof=4*nnode;nspeed=length(Rotor_Spd);
[Mb,Cb,Kb,zero_dof]=bearmtx(model,Rotor_Spd(1));dof=1:ndof;dof(zero_dof)=[];nzero=length(zero_dof);ncdof=ndof-nzero;eigenvalues=zeros(2*ncdof,nspeed);
RelSpd=zeros(ndof);
for irotor=1:nrotor,n1=Rotor_Def(irotor,1);n2=Rotor_Def(irotor,2);ndof_rotor=4*(n2-n1+1);RelSpd(4*n1-3:4*n2,4*n1-3:4*n2)=Rotor_Def(irotor,3)*eye(ndof_rotor);end
for ilink=1:nlink
 n1=Link_Def(ilink,2);n2=Link_Def(ilink,3);dof_link=[4*n1-3 4*n2-3];K0(dof_link,dof_link)=K0(dof_link,dof_link)+Link_Def(ilink,4)*[1 -1;-1 1];C0(dof_link,dof_link)=C0(dof_link,dof_link)+Link_Def(ilink,6)*[1 -1;-1 1];
 dof_link=[4*n1-2 4*n2-2];K0(dof_link,dof_link)=K0(dof_link,dof_link)+Link_Def(ilink,5)*[1 -1;-1 1];C0(dof_link,dof_link)=C0(dof_link,dof_link)+Link_Def(ilink,7)*[1 -1;-1 1];
end
if nargout==1
 for i=1:nspeed,[Mb,Cb,Kb,zero_dof]=bearmtx(model,Rotor_Spd(i));M=M0+Mb;K=K0+Kb+Rotor_Spd(i)*RelSpd*K1;C=C0+Cb+Rotor_Spd(i)*RelSpd*C1;AA=[zeros(ncdof) eye(ncdof);-M(dof,dof)\K(dof,dof) -M(dof,dof)\C(dof,dof)];eigenvalues_Spd=eig(AA);[eigenvalues_Spd,isort]=sort(eigenvalues_Spd);eigenvalues(:,i)=eigenvalues_Spd;end
end
if nargout==2
 if nspeed==1,eigenvectors=zeros(ndof,2*ncdof);else,eigenvectors=zeros(ndof,2*ncdof,nspeed);end
 for i=1:nspeed,[Mb,Cb,Kb,zero_dof]=bearmtx(model,Rotor_Spd(i));M=M0+Mb;K=K0+Kb+Rotor_Spd(i)*RelSpd*K1;C=C0+Cb+Rotor_Spd(i)*RelSpd*C1;AA=[zeros(ncdof) eye(ncdof);-M(dof,dof)\K(dof,dof) -M(dof,dof)\C(dof,dof)];[eigenvectors_Spd,eigenvalues_Spd]=eig(AA);[eigenvalues_Spd,isort]=sort(diag(eigenvalues_Spd));eigenvectors_Spd=eigenvectors_Spd(:,isort);eigenvalues(:,i)=eigenvalues_Spd;if nspeed==1,eigenvectors(dof,:)=eigenvectors_Spd(1:ncdof,:);else,eigenvectors(dof,:,i)=eigenvectors_Spd(1:ncdof,:);end,end
end