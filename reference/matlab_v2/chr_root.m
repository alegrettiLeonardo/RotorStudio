function [eigenvalues,eigenvectors,kappa,eccentricity] = chr_root(model,Rotor_Spd)
Node_Def=model.node;Bearing_Def=model.bearing;[nbearing,ncol_bearing]=size(Bearing_Def);
[M0,C0,C1,K0,K1]=rotormtx(model);[nnode,ncol_node]=size(Node_Def);ndof=4*nnode;nspeed=length(Rotor_Spd);
[Mb,Cb,Kb,zero_dof]=bearmtx(model,Rotor_Spd(1));dof=1:ndof;dof(zero_dof)=[];nzero=length(zero_dof);ncdof=ndof-nzero;eigenvalues=zeros(2*ncdof,nspeed);
if nargout==1
 for i=1:nspeed
  [Mb,Cb,Kb,zero_dof]=bearmtx(model,Rotor_Spd(i));M=M0+Mb;K=K0+Kb+Rotor_Spd(i)*K1;C=C0+Cb+Rotor_Spd(i)*C1;
  AA=[zeros(ncdof) eye(ncdof);-M(dof,dof)\K(dof,dof) -M(dof,dof)\C(dof,dof)];eigenvalues_Spd=eig(AA);[eigenvalues_Spd,isort]=sort(eigenvalues_Spd);eigenvalues(:,i)=eigenvalues_Spd;
 end
end
if nargout>=2
 if nspeed==1,eigenvectors=zeros(ndof,2*ncdof);else,eigenvectors=zeros(ndof,2*ncdof,nspeed);end
 eccentricity=zeros(nbearing,nspeed);
 for i=1:nspeed
  [Mb,Cb,Kb,zero_dof,eccentricity_i]=bearmtx(model,Rotor_Spd(i));eccentricity(:,i)=eccentricity_i;M=M0+Mb;K=K0+Kb+Rotor_Spd(i)*K1;C=C0+Cb+Rotor_Spd(i)*C1;
  AA=[zeros(ncdof) eye(ncdof);-M(dof,dof)\K(dof,dof) -M(dof,dof)\C(dof,dof)];[eigenvectors_Spd,eigenvalues_Spd]=eig(AA);[eigenvalues_Spd,isort]=sort(diag(eigenvalues_Spd));eigenvectors_Spd=eigenvectors_Spd(:,isort);eigenvalues(:,i)=eigenvalues_Spd;
  if nspeed==1,eigenvectors(dof,:)=eigenvectors_Spd(1:ncdof,:);else,eigenvectors(dof,:,i)=eigenvectors_Spd(1:ncdof,:);end
 end
end
if nargout>=3
 if nspeed==1,kappa=zeros(ndof,2*ncdof);else,kappa=zeros(ndof,2*ncdof,nspeed);end
 for i=1:nspeed
  for id=1:2*ncdof
   if nspeed==1,evector=eigenvectors(:,id);else,evector=eigenvectors(:,id,i);end
   kk=whirl(evector(1:2:ndof),evector(2:2:ndof));if imag(eigenvalues(id,i))<0,kk=-kk;end
   if nspeed==1,kappa(1:2:ndof,id)=kk;kappa(2:2:ndof,id)=kk;else,kappa(1:2:ndof,id,i)=kk;kappa(2:2:ndof,id,i)=kk;end
  end
 end
end