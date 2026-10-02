! SPDX-License-Identifier: Apache-2.0
! C1 additive C ABI for misalignment transient response.
module rd_fault_misalignment_c_api
 use, intrinsic::iso_c_binding,only:c_int,c_double,c_int64_t
 use rd_fault_misalignment,only:misalignment_response,C1_OK,C1_INVALID_INPUT
 implicit none(type,external)
 private
 public::rd_misalignment_required_v1,rd_misalignment_response_v1
contains
 integer(c_int) function rd_misalignment_required_v1(nn,nt,ndof,history_values) bind(C,name='rd_misalignment_required_v1')
 integer(c_int),value::nn,nt
 integer(c_int),intent(out)::ndof,history_values
 integer(c_int64_t)::need
 rd_misalignment_required_v1=C1_INVALID_INPUT;ndof=0;history_values=0
 if(nn<2.or.nn>100.or.nt<2.or.nt>20000)return
 need=int(6*nn,c_int64_t)*int(nt,c_int64_t)
 if(need>huge(history_values))return
 ndof=6*nn;history_values=int(need,c_int);rd_misalignment_required_v1=C1_OK
 end function

 subroutine unpack_model(ns,snodes,spar,sflags,nd,dnodes,dpar,nb,bnodes,bpar,shaft_nodes,shaft_par,shaft_flags,disk_nodes,disk_par,bearing_nodes,bearing_par)
 integer(c_int),intent(in)::ns,nd,nb,snodes(2,*),sflags(4,*),dnodes(*),bnodes(*)
 real(c_double),intent(in)::spar(10,*),dpar(3,*),bpar(12,*)
 integer(c_int),allocatable,intent(out)::shaft_nodes(:,:),shaft_flags(:,:),disk_nodes(:),bearing_nodes(:)
 real(c_double),allocatable,intent(out)::shaft_par(:,:),disk_par(:,:),bearing_par(:,:)
 integer::i,j
 allocate(shaft_nodes(2,max(1,ns)),shaft_flags(4,max(1,ns)),shaft_par(10,max(1,ns)))
 allocate(disk_nodes(max(1,nd)),disk_par(3,max(1,nd)),bearing_nodes(max(1,nb)),bearing_par(12,max(1,nb)))
 shaft_nodes=0;shaft_flags=0;shaft_par=0;disk_nodes=0;disk_par=0;bearing_nodes=0;bearing_par=0
 do j=1,ns
   do i=1,2;shaft_nodes(i,j)=snodes(i,j);enddo
   do i=1,4;shaft_flags(i,j)=sflags(i,j);enddo
   do i=1,10;shaft_par(i,j)=spar(i,j);enddo
 enddo
 do j=1,nd;disk_nodes(j)=dnodes(j);do i=1,3;disk_par(i,j)=dpar(i,j);enddo;enddo
 do j=1,nb;bearing_nodes(j)=bnodes(j);do i=1,12;bearing_par(i,j)=bpar(i,j);enddo;enddo
 end subroutine

 integer(c_int) function rd_misalignment_response_v1(nn,ns,snodes,spar,sflags,nd,dnodes,dpar,nb,bnodes,bpar, &
   coupling,mis_type,coupling_element,dx,dy,mis_angle,kr,kb,delta,input_torque,load_torque,nunb,unb_nodes,unb_mag,unb_phase, &
   nt,t,speed,gamma,beta,tol,history_cap,time_cap,qout,vout,aout,theta_out,funb_out,fmis_out,ftotal_out,iterations_out, &
   residual_out,absres_out,condition_out,failed_step,rigid_params) bind(C,name='rd_misalignment_response_v1')
 integer(c_int),value::nn,ns,nd,nb,coupling,mis_type,coupling_element,nunb,nt,history_cap,time_cap
 integer(c_int),intent(in)::snodes(2,*),sflags(4,*),dnodes(*),bnodes(*),unb_nodes(*)
 real(c_double),intent(in)::spar(10,*),dpar(3,*),bpar(12,*),unb_mag(*),unb_phase(*),t(*)
 real(c_double),value::dx,dy,mis_angle,kr,kb,delta,input_torque,load_torque,speed,gamma,beta,tol
 real(c_double),intent(inout)::qout(*),vout(*),aout(*),theta_out(*),funb_out(*),fmis_out(*),ftotal_out(*)
 integer(c_int),intent(inout)::iterations_out(*)
 real(c_double),intent(inout)::residual_out(*),absres_out(*),condition_out(*),rigid_params(*)
 integer(c_int),intent(out)::failed_step
 integer(c_int),allocatable::shaft_nodes(:,:),shaft_flags(:,:),disk_nodes(:),bearing_nodes(:),ubnodes(:),its(:)
 real(c_double),allocatable::shaft_par(:,:),disk_par(:,:),bearing_par(:,:),ubmag(:),ubphase(:),tt(:)
 real(c_double),allocatable::q(:,:),v(:,:),a(:,:),theta(:),funb(:,:),fmis(:,:),ftotal(:,:),res(:),ares(:),cond(:),rpar(:)
 integer(c_int)::st
 integer::n,i,j,k
 integer(c_int64_t)::need
 rd_misalignment_response_v1=C1_INVALID_INPUT;failed_step=0
 if(nn<2.or.nn>100.or.ns/=nn-1.or.nd<0.or.nb<0.or.nunb<0.or.nt<2)return
 n=6*nn;need=int(n,c_int64_t)*int(nt,c_int64_t)
 if(int(history_cap,c_int64_t)<need.or.time_cap<nt)return
 call unpack_model(ns,snodes,spar,sflags,nd,dnodes,dpar,nb,bnodes,bpar,shaft_nodes,shaft_par,shaft_flags,disk_nodes,disk_par,bearing_nodes,bearing_par)
 allocate(ubnodes(max(1,nunb)),ubmag(max(1,nunb)),ubphase(max(1,nunb)),tt(nt))
 ubnodes=0;ubmag=0;ubphase=0
 do i=1,nunb;ubnodes(i)=unb_nodes(i);ubmag(i)=unb_mag(i);ubphase(i)=unb_phase(i);enddo
 do i=1,nt;tt(i)=t(i);enddo
 allocate(q(n,nt),v(n,nt),a(n,nt),theta(nt),funb(n,nt),fmis(n,nt),ftotal(n,nt),its(nt),res(nt),ares(nt),cond(nt),rpar(4))
 call misalignment_response(nn,ns,shaft_nodes,shaft_par,shaft_flags,nd,disk_nodes,disk_par,nb,bearing_nodes,bearing_par, &
   coupling,mis_type,coupling_element,dx,dy,mis_angle,kr,kb,delta,input_torque,load_torque,nunb,ubnodes,ubmag,ubphase, &
   nt,tt,speed,gamma,beta,tol,q,v,a,theta,funb,fmis,ftotal,its,res,ares,cond,failed_step,rpar,st)
 if(st/=C1_OK)then;rd_misalignment_response_v1=st;return;endif
 do j=1,nt
   theta_out(j)=theta(j);iterations_out(j)=its(j);residual_out(j)=res(j);absres_out(j)=ares(j);condition_out(j)=cond(j)
   do i=1,n
     k=(j-1)*n+i
     qout(k)=q(i,j);vout(k)=v(i,j);aout(k)=a(i,j)
     funb_out(k)=funb(i,j);fmis_out(k)=fmis(i,j);ftotal_out(k)=ftotal(i,j)
   enddo
 enddo
 do i=1,4;rigid_params(i)=rpar(i);enddo
 rd_misalignment_response_v1=C1_OK
 end function
end module rd_fault_misalignment_c_api
