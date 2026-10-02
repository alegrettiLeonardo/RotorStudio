! SPDX-License-Identifier: Apache-2.0
! C1 native misalignment fault on the promoted B2 full 6-DOF platform.
module rd_fault_misalignment
 use, intrinsic::ieee_arithmetic,only:ieee_is_finite
 use, intrinsic::iso_fortran_env,only:int64
 use rd_kinds,only:rk,ik
 use rd_6dof_assembly,only:assemble_6dof,B2_OK
 use rd_newmark,only:newmark_step
 implicit none(type,external)
 private
 integer(ik),parameter,public::C1_OK=0_ik,C1_INVALID_INPUT=50_ik,C1_UNSUPPORTED=51_ik
 integer(ik),parameter,public::C1_B2_FAILURE=52_ik,C1_NEWMARK_FAILURE=53_ik,C1_NONFINITE=54_ik
 public::flex_force_at,rigid_force_at,misalignment_response
contains
 subroutine coupling_dofs(nn,left_node,idx,status)
 integer(ik),intent(in)::nn,left_node
 integer,intent(out)::idx(12)
 integer(ik),intent(out)::status
 integer::i
 status=C1_INVALID_INPUT;idx=0
 if(left_node<1.or.left_node>=nn)return
 do i=1,6
   idx(i)=6*(left_node-1)+i
   idx(6+i)=6*left_node+i
 enddo
 status=C1_OK
 end subroutine

 subroutine flex_component(nn,left_node,theta,kind,radius,dx,dy,mis_angle,kr,kb,input_torque,load_torque,F,status)
 integer(ik),intent(in)::nn,left_node,kind
 real(rk),intent(in)::theta,radius,dx,dy,mis_angle,kr,kb,input_torque,load_torque
 real(rk),intent(out)::F(6*nn)
 integer(ik),intent(out)::status
 integer::idx(12),j
 real(rk)::pi,aux1,aux2,phi,a(3),fv(3),fp(3),fpx,fpy,aux,fa,fax,fay
 F=0._rk;status=C1_INVALID_INPUT
 if(.not.all(ieee_is_finite([theta,radius,dx,dy,mis_angle,kr,kb,input_torque,load_torque])))return
 if(radius<=0._rk.or.kr<0._rk.or.kb<0._rk)return
 call coupling_dofs(nn,left_node,idx,status);if(status/=C1_OK)return
 pi=acos(-1._rk);a=[0._rk,pi/6._rk,pi/3._rk]
 if(kind==1)then
   if(dy==0._rk)return
   aux1=radius**2+dx**2+dy**2
   aux2=2._rk*radius*sqrt(dx**2+dy**2)
   phi=atan(dx/dy)+theta
   fv(1)=sin(phi+a(1));fv(2)=cos(phi+a(2));fv(3)=-sin(phi+a(3))
   do j=1,3
     if(aux1+aux2*fv(j)<0._rk)return
     fp(j)=sqrt(aux1+aux2*fv(j))-radius
   enddo
   fpx=(fp(1)*sin(theta+4._rk*a(1))+fp(2)*sin(theta+4._rk*a(2))-fp(3)*sin(theta+4._rk*a(3)))*kr
   fpy=(fp(1)*cos(theta+4._rk*a(1))+fp(2)*cos(theta+4._rk*a(2))-fp(3)*cos(theta+4._rk*a(3)))*kr
   F(idx(1))=fpx;F(idx(7))=-fpx
   F(idx(2))=fpy;F(idx(8))=-fpy
   F(idx(6))=input_torque;F(idx(12))=load_torque
 elseif(kind==2)then
   aux=kb*radius*sqrt(max(0._rk,2._rk-2._rk*cos(mis_angle)))*sin(mis_angle)
   fax=0._rk;fay=0._rk
   do j=1,3
     fa=abs(aux*sin(theta+4._rk*a(j)))
     fax=fax+fa*cos(theta+pi+4._rk*a(j))
     fay=fay+fa*sin(theta+pi+4._rk*a(j))
   enddo
   F(idx(1))=fax;F(idx(7))=-fax
   F(idx(2))=fay;F(idx(8))=-fay
   F(idx(6))=input_torque;F(idx(12))=load_torque
 else
   status=C1_INVALID_INPUT;return
 endif
 if(.not.all(ieee_is_finite(F)))then;status=C1_NONFINITE;return;endif
 status=C1_OK
 end subroutine

 subroutine flex_force_at(nn,left_node,theta,mis_type,radius,dx,dy,mis_angle,kr,kb,input_torque,load_torque,F,status)
 integer(ik),intent(in)::nn,left_node,mis_type
 real(rk),intent(in)::theta,radius,dx,dy,mis_angle,kr,kb,input_torque,load_torque
 real(rk),intent(out)::F(6*nn)
 integer(ik),intent(out)::status
 real(rk)::Fp(6*nn),Fa(6*nn)
 integer(ik)::sp,sa
 F=0._rk
 select case(mis_type)
 case(1)
   call flex_component(nn,left_node,theta,1,radius,dx,dy,mis_angle,kr,kb,input_torque,load_torque,F,status)
 case(2)
   call flex_component(nn,left_node,theta,2,radius,dx,dy,mis_angle,kr,kb,input_torque,load_torque,F,status)
 case(3)
   call flex_component(nn,left_node,theta,1,radius,dx,dy,mis_angle,kr,kb,input_torque,load_torque,Fp,sp)
   if(sp/=C1_OK)then;status=sp;return;endif
   call flex_component(nn,left_node,theta,2,radius,dx,dy,mis_angle,kr,kb,input_torque,load_torque,Fa,sa)
   if(sa/=C1_OK)then;status=sa;return;endif
   F=Fp+Fa;status=C1_OK
 case default
   status=C1_INVALID_INPUT
 end select
 end subroutine

 subroutine rigid_force_at(nn,left_node,theta,delta,input_torque,load_torque,kl1,kl2,kt1,kt2,q,phi_state,F,status)
 integer(ik),intent(in)::nn,left_node
 real(rk),intent(in)::theta,delta,input_torque,load_torque,kl1,kl2,kt1,kt2,q(6*nn)
 real(rk),intent(inout)::phi_state
 real(rk),intent(out)::F(6*nn)
 integer(ik),intent(out)::status
 integer::idx(12),j
 real(rk)::kte,w1,w2,kle,sn,cs,kbeta(12),qloc(12),couple
 F=0._rk;status=C1_INVALID_INPUT
 if(.not.all(ieee_is_finite([theta,delta,input_torque,load_torque,kl1,kl2,kt1,kt2,phi_state])))return
 if(.not.all(ieee_is_finite(q)).or.delta<0._rk)return
 if(abs(kt1+kt2)<=tiny(1._rk).or.abs(kl1+kl2)<=tiny(1._rk))return
 call coupling_dofs(nn,left_node,idx,status);if(status/=C1_OK)return
 kte=1._rk/(kt1+kt2);w1=kt1*kte;w2=kt2*kte
 kle=kl1*kl2/(kl1+kl2)
 phi_state=w1*theta+w2*theta+kle*kte*delta*((q(idx(7))-q(idx(1)))*sin(phi_state)-(q(idx(8))-q(idx(2)))*cos(phi_state))
 sn=sin(phi_state);cs=cos(phi_state);kbeta=0._rk
 kbeta(1)=kle*delta*(w1*sn);kbeta(2)=-kle*delta*(w1*cs)
 kbeta(7)=kle*delta*(w2*sn);kbeta(8)=-kle*delta*(w2*cs)
 do j=1,12;qloc(j)=q(idx(j));enddo
 couple=sum(kbeta*qloc)
 F(idx(1))=-kle*delta*(cs-1._rk);F(idx(2))=-kle*delta*sn
 F(idx(7))= kle*delta*(cs-1._rk);F(idx(8))= kle*delta*sn
 F(idx(6))=input_torque-load_torque+couple
 F(idx(12))=-(input_torque-load_torque)-couple
 if(.not.all(ieee_is_finite(F)).or..not.ieee_is_finite(phi_state))then;status=C1_NONFINITE;return;endif
 status=C1_OK
 end subroutine

 subroutine misalignment_response(nn,ns,shaft_nodes,shaft_par,shaft_flags,nd,disk_nodes,disk_par,nb,bearing_nodes,bearing_par, &
   coupling,mis_type,coupling_element,dx,dy,mis_angle,kr,kb,delta,input_torque,load_torque,nunb,unb_nodes,unb_mag,unb_phase, &
   nt,t,speed,gamma,beta,tol,q,v,a,theta,Funb,Fmis,Ftotal,iterations,residual,absres,condition,failed_step,rigid_params,status)
 integer(ik),intent(in)::nn,ns,nd,nb,coupling,mis_type,coupling_element,nunb,nt
 integer(ik),intent(in)::shaft_nodes(2,max(1,ns)),shaft_flags(4,max(1,ns)),disk_nodes(max(1,nd)),bearing_nodes(max(1,nb))
 integer(ik),intent(in)::unb_nodes(max(1,nunb))
 real(rk),intent(in)::shaft_par(10,max(1,ns)),disk_par(3,max(1,nd)),bearing_par(12,max(1,nb))
 real(rk),intent(in)::dx,dy,mis_angle,kr,kb,delta,input_torque,load_torque,unb_mag(max(1,nunb)),unb_phase(max(1,nunb))
 real(rk),intent(in)::t(nt),speed,gamma,beta,tol
 real(rk),intent(out)::q(6*nn,nt),v(6*nn,nt),a(6*nn,nt),theta(nt),Funb(6*nn,nt),Fmis(6*nn,nt),Ftotal(6*nn,nt)
 integer(ik),intent(out)::iterations(nt),failed_step,status
 real(rk),intent(out)::residual(nt),absres(nt),condition(nt),rigid_params(4)
 real(rk),allocatable::M(:,:),K(:,:),C(:,:),G(:,:),S(:,:),Ce(:,:),ft(:)
 real(rk)::radius,phi_state,kl1,kl2,kt1,kt2,phase
 integer(ik)::st,nst
 integer::n,i,j,node,ix,left_node
 integer(int64)::budget
 status=C1_INVALID_INPUT;failed_step=0;rigid_params=0._rk
 if(nn<2.or.nn>100.or.ns/=nn-1.or.nd<0.or.nb<0.or.nt<2.or.nt>20000.or.nunb<0.or.nunb>nn)return
 if(coupling/=1.and.coupling/=2)return
 if(coupling_element<1.or.coupling_element>ns)return
 if(coupling==1.and.(mis_type<1.or.mis_type>3))return
 if(coupling==2.and.mis_type/=0)return
 if(.not.all(ieee_is_finite(t)).or.any(t(2:)<=t(:nt-1)))return
 if(.not.all(ieee_is_finite([speed,gamma,beta,tol,dx,dy,mis_angle,kr,kb,delta,input_torque,load_torque])))return
 if(gamma<=0._rk.or.beta<=0._rk.or.tol<=0._rk)return
 if(nunb>0)then
   if(.not.all(ieee_is_finite(unb_mag(:nunb))).or..not.all(ieee_is_finite(unb_phase(:nunb))) )return
 endif
 n=6*nn;budget=int(7_int64*n*nt+5_int64*n*n,int64)*8_int64
 if(budget>512_int64*1024_int64*1024_int64)return
 allocate(M(n,n),K(n,n),C(n,n),G(n,n),S(n,n),Ce(n,n),ft(n))
 call assemble_6dof(nn,ns,shaft_nodes,shaft_par,shaft_flags,nd,disk_nodes,disk_par,nb,bearing_nodes,bearing_par,M,K,C,G,S,st)
 if(st/=B2_OK)then;status=C1_B2_FAILURE;return;endif
 Ce=C+speed*G
 if(.not.all(ieee_is_finite(Ce)))then;status=C1_NONFINITE;return;endif
 q=0._rk;v=0._rk;a=0._rk;Funb=0._rk;Fmis=0._rk;Ftotal=0._rk
 iterations=0;residual=0._rk;absres=0._rk;condition=0._rk
 theta=speed*(t-t(1))
 do j=1,nunb
   node=unb_nodes(j);if(node<1.or.node>nn)then;status=C1_INVALID_INPUT;return;endif
   ix=6*(node-1)+1
   do i=1,nt
     phase=unb_phase(j)+theta(i)
     Funb(ix,i)=Funb(ix,i)+unb_mag(j)*speed**2*cos(phase)
     Funb(ix+1,i)=Funb(ix+1,i)+unb_mag(j)*speed**2*sin(phase)
   enddo
 enddo
 left_node=shaft_nodes(1,coupling_element)
 radius=shaft_par(3,coupling_element)/2._rk
 if(coupling==1)then
   do i=1,nt
     call flex_force_at(nn,left_node,theta(i),mis_type,radius,dx,dy,mis_angle,kr,kb,input_torque,load_torque,Fmis(:,i),st)
     if(st/=C1_OK)then;status=st;return;endif
   enddo
   Ftotal=Funb+Fmis
 else
   ix=6*(left_node-1)+1
   kl1=K(ix,ix);kl2=K(ix+6,ix+6);kt1=K(ix+5,ix+5);kt2=K(ix+11,ix+11)
   rigid_params=[kl1,kl2,kt1,kt2]
   phi_state=-acos(-1._rk)/180._rk
   Ftotal=Funb
 endif
 absres(1)=norm2(Ftotal(:,1));if(any(Ftotal(:,1)/=0._rk))residual(1)=1._rk
 do i=2,nt
   failed_step=i
   if(coupling==2)then
     call rigid_force_at(nn,left_node,theta(i),delta,input_torque,load_torque,kl1,kl2,kt1,kt2,q(:,i-1),phi_state,Fmis(:,i),st)
     if(st/=C1_OK)then;status=st;return;endif
     Ftotal(:,i)=Funb(:,i)+Fmis(:,i)
   endif
   ft=Ftotal(:,i)
   call newmark_step(n,M,Ce,K,ft,t(i)-t(i-1),gamma,beta,tol,q(:,i-1),v(:,i-1),a(:,i-1), &
     q(:,i),v(:,i),a(:,i),iterations(i),residual(i),absres(i),condition(i),nst)
   if(nst/=0)then;status=C1_NEWMARK_FAILURE;return;endif
 enddo
 if(.not.all(ieee_is_finite(q)).or..not.all(ieee_is_finite(Fmis)).or..not.all(ieee_is_finite(Ftotal)))then
   status=C1_NONFINITE;return
 endif
 failed_step=0;status=C1_OK
 end subroutine
end module rd_fault_misalignment
