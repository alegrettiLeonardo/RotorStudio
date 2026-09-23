module rd_c_api
 use, intrinsic::iso_c_binding, only:c_int,c_double
 use rd_kinds,only:rk,ik
 use rd_status,only:RD_OK,RD_ERR_INPUT
 use rd_assembly_stationary,only:assemble_rotor,assemble_bearings
 use rd_eigensystem,only:stationary_eigs
 use rd_frequency_response,only:synchronous_response
 use rd_critical_speed,only:critical_speeds
 implicit none(type,external);private
 public::rd_modal_legacy,rd_assemble_legacy,rd_freq_rsp_legacy,rd_crit_spd_legacy,rd_version
contains
 integer(c_int) function rd_version(major,minor,patch) bind(C,name='rd_version')
   integer(c_int),intent(out)::major,minor,patch;major=0;minor=2;patch=0;rd_version=0
 end function
 integer(c_int) function rd_assemble_legacy(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,speed,Mout,Cout,Kout,Gout) bind(C,name='rd_assemble_legacy')
   integer(c_int),value::nnode,nshaft,ndisc,nbear;real(c_double),intent(in)::z(*),shaft(*),disc(*),bear(*);real(c_double),value::speed
   real(c_double),intent(out)::Mout(*),Cout(*),Kout(*),Gout(*)
   real(rk),allocatable::zz(:),sh(:,:),di(:,:),be(:,:),M(:,:),C0(:,:),C1(:,:),K0(:,:),K1(:,:),Mb(:,:),Cb(:,:),Kb(:,:)
   logical,allocatable::iz(:);integer::i,j,ndof;integer(ik)::st
   rd_assemble_legacy=RD_ERR_INPUT;if(nnode<=0)return;ndof=4*nnode
   call unpack(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,zz,sh,di,be)
   allocate(M(ndof,ndof),C0(ndof,ndof),C1(ndof,ndof),K0(ndof,ndof),K1(ndof,ndof),Mb(ndof,ndof),Cb(ndof,ndof),Kb(ndof,ndof),iz(ndof))
   call assemble_rotor(nnode,zz,nshaft,sh,ndisc,di,M,C0,C1,K0,K1,st);if(st/=RD_OK)then;rd_assemble_legacy=st;return;endif
   call assemble_bearings(nnode,nbear,be,speed,Mb,Cb,Kb,iz,st);if(st/=RD_OK)then;rd_assemble_legacy=st;return;endif
   do j=1,ndof;do i=1,ndof
     Mout((j-1)*ndof+i)=M(i,j)+Mb(i,j);Cout((j-1)*ndof+i)=C0(i,j)+Cb(i,j)+speed*C1(i,j)
     Kout((j-1)*ndof+i)=K0(i,j)+Kb(i,j)+speed*K1(i,j);Gout((j-1)*ndof+i)=C1(i,j)
   enddo;enddo;rd_assemble_legacy=RD_OK
 end function
 integer(c_int) function rd_modal_legacy(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,speed,nout,er,ei) bind(C,name='rd_modal_legacy')
   integer(c_int),value::nnode,nshaft,ndisc,nbear,nout
   real(c_double),intent(in)::z(*),shaft(*),disc(*),bear(*);real(c_double),value::speed
   real(c_double),intent(out)::er(*),ei(*)
   real(rk),allocatable::zz(:),sh(:,:),di(:,:),be(:,:),M(:,:),C0(:,:),C1(:,:),K0(:,:),K1(:,:),Mb(:,:),Cb(:,:),Kb(:,:),Mc(:,:),Cc(:,:),Kc(:,:),wr(:),wi(:)
   logical,allocatable::iz(:);integer,allocatable::keep(:);integer::i,j,ndof,nc,idx;integer(ik)::st
   rd_modal_legacy=RD_ERR_INPUT;if(nnode<=0)return;ndof=4*nnode
   call unpack(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,zz,sh,di,be)
   allocate(M(ndof,ndof),C0(ndof,ndof),C1(ndof,ndof),K0(ndof,ndof),K1(ndof,ndof),Mb(ndof,ndof),Cb(ndof,ndof),Kb(ndof,ndof),iz(ndof))
   call assemble_rotor(nnode,zz,nshaft,sh,ndisc,di,M,C0,C1,K0,K1,st);if(st/=RD_OK)then;rd_modal_legacy=st;return;endif
   call assemble_bearings(nnode,nbear,be,speed,Mb,Cb,Kb,iz,st);if(st/=RD_OK)then;rd_modal_legacy=st;return;endif
   nc=count(.not.iz);if(nout<2*nc)then;rd_modal_legacy=RD_ERR_INPUT;return;endif;allocate(keep(nc));idx=0
   do i=1,ndof;if(.not.iz(i))then;idx=idx+1;keep(idx)=i;endif;enddo
   allocate(Mc(nc,nc),Cc(nc,nc),Kc(nc,nc),wr(2*nc),wi(2*nc))
   do j=1,nc;do i=1,nc
     Mc(i,j)=M(keep(i),keep(j))+Mb(keep(i),keep(j));Cc(i,j)=C0(keep(i),keep(j))+Cb(keep(i),keep(j))+speed*C1(keep(i),keep(j));Kc(i,j)=K0(keep(i),keep(j))+Kb(keep(i),keep(j))+speed*K1(keep(i),keep(j))
   enddo;enddo
   call stationary_eigs(Mc,Cc,Kc,wr,wi,st);if(st/=RD_OK)then;rd_modal_legacy=st;return;endif
   do i=1,2*nc;er(i)=wr(i);ei(i)=wi(i);enddo;rd_modal_legacy=RD_OK
 end function
 integer(c_int) function rd_freq_rsp_legacy(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,nforce,force,nbend,bend,nspeed,speeds,rr,ri) bind(C,name='rd_freq_rsp_legacy')
   integer(c_int),value::nnode,nshaft,ndisc,nbear,nforce,nbend,nspeed;real(c_double),intent(in)::z(*),shaft(*),disc(*),bear(*),force(*),bend(*),speeds(*)
   real(c_double),intent(out)::rr(*),ri(*)
   real(rk),allocatable::zz(:),sh(:,:),di(:,:),be(:,:),fo(:,:),bd(:,:),M(:,:),C0(:,:),C1(:,:),K0(:,:),K1(:,:),Mb(:,:),Cb(:,:),Kb(:,:)
   complex(rk),allocatable::resp(:);logical,allocatable::iz(:);integer::i,j,k,ndof;integer(ik)::st
   rd_freq_rsp_legacy=RD_ERR_INPUT;if(nnode<=0.or.nspeed<=0)return;ndof=4*nnode
   call unpack(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,zz,sh,di,be);allocate(fo(5,nforce),bd(3,max(1,nbend)))
   do j=1,nforce;do i=1,5;fo(i,j)=force((j-1)*5+i);enddo;enddo;bd=0;do j=1,nbend;do i=1,3;bd(i,j)=bend((j-1)*3+i);enddo;enddo
   allocate(M(ndof,ndof),C0(ndof,ndof),C1(ndof,ndof),K0(ndof,ndof),K1(ndof,ndof),Mb(ndof,ndof),Cb(ndof,ndof),Kb(ndof,ndof),iz(ndof),resp(ndof))
   call assemble_rotor(nnode,zz,nshaft,sh,ndisc,di,M,C0,C1,K0,K1,st);if(st/=RD_OK)then;rd_freq_rsp_legacy=st;return;endif
   do k=1,nspeed
    call assemble_bearings(nnode,nbear,be,speeds(k),Mb,Cb,Kb,iz,st);if(st/=RD_OK)then;rd_freq_rsp_legacy=st;return;endif
    call synchronous_response(M,C0,C1,K0,K1,Mb,Cb,Kb,iz,speeds(k),fo,nforce,bd,nbend,resp,st);if(st/=RD_OK)then;rd_freq_rsp_legacy=st;return;endif
    do i=1,ndof;rr((k-1)*ndof+i)=real(resp(i),rk);ri((k-1)*ndof+i)=aimag(resp(i));enddo
   enddo;rd_freq_rsp_legacy=RD_OK
 end function
 integer(c_int) function rd_crit_spd_legacy(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,NX,damped,ncrit,maxiter,tol,out) bind(C,name='rd_crit_spd_legacy')
   integer(c_int),value::nnode,nshaft,ndisc,nbear,damped,ncrit,maxiter;real(c_double),intent(in)::z(*),shaft(*),disc(*),bear(*);real(c_double),value::NX,tol;real(c_double),intent(out)::out(*)
   real(rk),allocatable::zz(:),sh(:,:),di(:,:),be(:,:),M(:,:),C0(:,:),C1(:,:),K0(:,:),K1(:,:),crit(:);integer::i,ndof;integer(ik)::st
   rd_crit_spd_legacy=RD_ERR_INPUT;if(nnode<=0.or.ncrit<=0)return;ndof=4*nnode;call unpack(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,zz,sh,di,be)
   allocate(M(ndof,ndof),C0(ndof,ndof),C1(ndof,ndof),K0(ndof,ndof),K1(ndof,ndof),crit(ncrit));call assemble_rotor(nnode,zz,nshaft,sh,ndisc,di,M,C0,C1,K0,K1,st)
   if(st/=RD_OK)then;rd_crit_spd_legacy=st;return;endif;call critical_speeds(nnode,nbear,be,M,C0,C1,K0,K1,NX,damped/=0,ncrit,maxiter,tol,crit,st)
   if(st/=RD_OK)then;rd_crit_spd_legacy=st;return;endif;do i=1,ncrit;out(i)=crit(i);enddo;rd_crit_spd_legacy=RD_OK
 end function
 subroutine unpack(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,zz,sh,di,be)
   integer,intent(in)::nnode,nshaft,ndisc,nbear;real(c_double),intent(in)::z(*),shaft(*),disc(*),bear(*)
   real(rk),allocatable,intent(out)::zz(:),sh(:,:),di(:,:),be(:,:);integer::i,j
   allocate(zz(nnode),sh(11,nshaft),di(6,ndisc),be(34,nbear));do i=1,nnode;zz(i)=z(i);enddo
   do j=1,nshaft;do i=1,11;sh(i,j)=shaft((j-1)*11+i);enddo;enddo
   do j=1,ndisc;do i=1,6;di(i,j)=disc((j-1)*6+i);enddo;enddo
   do j=1,nbear;do i=1,34;be(i,j)=bear((j-1)*34+i);enddo;enddo
 end subroutine
end module rd_c_api
