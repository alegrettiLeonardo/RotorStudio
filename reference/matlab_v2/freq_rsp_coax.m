function [response] = freq_rsp_coax(model,Rotor_Spd)
Node_Def=model.node;Force_Def=model.force;Rotor_Def=model.rotors;Bearing_Def=model.bearing;nbearing=size(Bearing_Def,1);nrotor=size(Rotor_Def,1);
Bear_Speed_Ratio=ones(nbearing,1);nlink=0;Link_Def=[];
for ibearing=nbearing:-1:1
 if Bearing_Def(ibearing,1)==7 | Bearing_Def(ibearing,1)==8
  Bearing_node=Bearing_Def(ibearing,2);for irotor=1:nrotor,if Bearing_node>=Rotor_Def(irotor,1)&Bearing_node<=Rotor_Def(irotor,2),Bear_Speed_Ratio(ibearing)=Rotor_Def(irotor,3);end,end
 end
 if Bearing_Def(ibearing,1)==20,Link_Def=[Link_Def;Bearing_Def(ibearing,:)];Bearing_Def(ibearing,:)=[];nlink=nlink+1;end
end
nspeed=length(Rotor_Spd);[nforce,ncol_force]=size(Force_Def);jot=sqrt(-1);
[M0,C0,C1,K0,K1]=rotormtx(model);[nnode,ncol_node]=size(Node_Def);ndof=4*nnode;[Mb,Cb,Kb,zero_dof]=bearmtx(model,Rotor_Spd(1));dof=1:ndof;dof(zero_dof)=[];nzero=length(zero_dof);
RelSpd=zeros(ndof);
for irotor=1:nrotor,n1=Rotor_Def(irotor,1);n2=Rotor_Def(irotor,2);ndof_rotor=4*(n2-n1+1);RelSpd(4*n1-3:4*n2,4*n1-3:4*n2)=Rotor_Def(irotor,3)*eye(ndof_rotor);end
for ilink=1:nlink,n1=Link_Def(ilink,2);n2=Link_Def(ilink,3);dof_link=[4*n1-3 4*n2-3];K0(dof_link,dof_link)=K0(dof_link,dof_link)+Link_Def(ilink,4)*[1 -1;-1 1];C0(dof_link,dof_link)=C0(dof_link,dof_link)+Link_Def(ilink,6)*[1 -1;-1 1];dof_link=[4*n1-2 4*n2-2];K0(dof_link,dof_link)=K0(dof_link,dof_link)+Link_Def(ilink,5)*[1 -1;-1 1];C0(dof_link,dof_link)=C0(dof_link,dof_link)+Link_Def(ilink,7)*[1 -1;-1 1];end
ub_rotor_n=zeros(1,nrotor);ubforce=zeros(ndof,nrotor);
for iforce=1:nforce
 if Force_Def(iforce,1)==1
  node=Force_Def(iforce,2);unbal_mag=Force_Def(iforce,3);unbal_phase=Force_Def(iforce,4);force_dof=[4*node-3;4*node-2];
  for irotor=1:nrotor,if node>=Rotor_Def(irotor,1)&node<=Rotor_Def(irotor,2),irotor_ub=irotor;ub_rotor_n(irotor)=1;end,end
  ubforce(force_dof,irotor_ub)=ubforce(force_dof,irotor_ub)+unbal_mag*exp(j*unbal_phase)*[1;-jot];
 end
end
ubforce=ubforce(:,irotor_ub);ubforce(zero_dof)=[];
response=zeros(ndof,nspeed);
for ispeed=1:nspeed
 [Mb,Cb,Kb,zero_dof]=bearmtx(model,Rotor_Spd(ispeed));M=M0+Mb;K=K0+Kb+Rotor_Spd(ispeed)*RelSpd*K1;C=C0+Cb+Rotor_Spd(ispeed)*RelSpd*C1;
 if nzero>0,M=M(dof,dof);C=C(dof,dof);K=K(dof,dof);end
 Excite_Spd=Rotor_Def(irotor_ub,3)*Rotor_Spd(ispeed);force=ubforce*(Excite_Spd^2);response(dof,ispeed)=(-M*(Excite_Spd^2)+jot*C*Excite_Spd+K)\force;
end