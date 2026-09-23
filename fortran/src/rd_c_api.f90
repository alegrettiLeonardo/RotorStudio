module rd_c_api
 use, intrinsic::iso_c_binding, only:c_int,c_double
 use rd_kinds,only:rk,ik
 use rd_status,only:RD_OK,RD_ERR_INPUT,RD_ERR_UNSUPPORTED
 use rd_assembly_stationary,only:assemble_rotor,assemble_bearings
 use rd_assembly_rotating,only:assemble_rotor_rotating,assemble_bearings_rotating
 use rd_eigensystem,only:stationary_eigs,second_order_eigs
 use rd_frequency_response,only:synchronous_response
 use rd_external_response,only:auxiliary_frequency_response,foundation_frequency_response
 use rd_critical_speed,only:critical_speeds,critical_speeds_ex
 use rd_coaxial_solver,only:coaxial_eigs,coaxial_frequency_response
 use rd_rotating_solver,only:asymmetric_eigs,asymmetric_frequency_response
 use rd_transient,only:time_foundation_response,runup_response
 implicit none(type,external);private
 public::rd_modal_legacy,rd_modal_legacy_vectors,rd_assemble_legacy,rd_bearings_legacy,rd_freq_rsp_legacy,rd_crit_spd_legacy,rd_crit_spd_legacy_ex
 public::rd_freq_aux_legacy,rd_freq_fdn_legacy,rd_time_fdn_legacy,rd_runup_legacy
 public::rd_coax_modal_legacy,rd_coax_freq_rsp_legacy,rd_asym_assemble_legacy,rd_bearasym_legacy,rd_asym_modal_legacy,rd_asym_freq_rsp_legacy,rd_version
contains
 integer(c_int) function rd_version(major,minor,patch) bind(C,name='rd_version')
   integer(c_int),intent(out)::major,minor,patch;major=0;minor=5;patch=0;rd_version=0
 end function

 integer(c_int) function rd_bearings_legacy(nnode,nbear,bear,speed,Mout,Cout,Kout,zero_mask,ecc) bind(C,name='rd_bearings_legacy')
   integer(c_int),value::nnode,nbear;real(c_double),intent(in)::bear(*);real(c_double),value::speed
   real(c_double),intent(out)::Mout(*),Cout(*),Kout(*),ecc(*);integer(c_int),intent(out)::zero_mask(*)
   real(rk),allocatable::be(:,:),M(:,:),C(:,:),K(:,:),ee(:);logical,allocatable::iz(:);integer::i,j,ndof;integer(ik)::st
   rd_bearings_legacy=RD_ERR_INPUT;if(nnode<=0.or.nbear<0)return;ndof=4*nnode;allocate(be(34,nbear),M(ndof,ndof),C(ndof,ndof),K(ndof,ndof),iz(ndof),ee(nbear))
   do j=1,nbear;do i=1,34;be(i,j)=bear((j-1)*34+i);enddo;enddo
   call assemble_bearings(nnode,nbear,be,speed,M,C,K,iz,st,ee);if(st/=RD_OK)then;rd_bearings_legacy=st;return;endif
   do j=1,ndof;do i=1,ndof;Mout((j-1)*ndof+i)=M(i,j);Cout((j-1)*ndof+i)=C(i,j);Kout((j-1)*ndof+i)=K(i,j);enddo;enddo
   do i=1,ndof;zero_mask(i)=merge(1,0,iz(i));enddo;do i=1,nbear;ecc(i)=ee(i);enddo;rd_bearings_legacy=RD_OK
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

 integer(c_int) function rd_modal_legacy_vectors(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,speed,nout,er,ei,vr,vi,ecc) bind(C,name='rd_modal_legacy_vectors')
   integer(c_int),value::nnode,nshaft,ndisc,nbear,nout
   real(c_double),intent(in)::z(*),shaft(*),disc(*),bear(*);real(c_double),value::speed
   real(c_double),intent(out)::er(*),ei(*),vr(*),vi(*),ecc(*)
   real(rk),allocatable::zz(:),sh(:,:),di(:,:),be(:,:),M(:,:),C0(:,:),C1(:,:),K0(:,:),K1(:,:),Mb(:,:),Cb(:,:),Kb(:,:),Mc(:,:),Cc(:,:),Kc(:,:),ee(:)
   complex(rk),allocatable::w(:),Vred(:,:)
   logical,allocatable::iz(:);integer,allocatable::keep(:);integer::i,j,ndof,nc,idx;integer(ik)::st
   rd_modal_legacy_vectors=RD_ERR_INPUT;if(nnode<=0)return;ndof=4*nnode
   call unpack(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,zz,sh,di,be)
   allocate(M(ndof,ndof),C0(ndof,ndof),C1(ndof,ndof),K0(ndof,ndof),K1(ndof,ndof),Mb(ndof,ndof),Cb(ndof,ndof),Kb(ndof,ndof),iz(ndof),ee(nbear))
   call assemble_rotor(nnode,zz,nshaft,sh,ndisc,di,M,C0,C1,K0,K1,st);if(st/=RD_OK)then;rd_modal_legacy_vectors=st;return;endif
   call assemble_bearings(nnode,nbear,be,speed,Mb,Cb,Kb,iz,st,ee);if(st/=RD_OK)then;rd_modal_legacy_vectors=st;return;endif
   nc=count(.not.iz);if(nout<2*nc)then;rd_modal_legacy_vectors=RD_ERR_INPUT;return;endif;allocate(keep(nc));idx=0
   do i=1,ndof;if(.not.iz(i))then;idx=idx+1;keep(idx)=i;endif;enddo
   allocate(Mc(nc,nc),Cc(nc,nc),Kc(nc,nc),w(2*nc),Vred(nc,2*nc))
   do j=1,nc;do i=1,nc
     Mc(i,j)=M(keep(i),keep(j))+Mb(keep(i),keep(j));Cc(i,j)=C0(keep(i),keep(j))+Cb(keep(i),keep(j))+speed*C1(keep(i),keep(j));Kc(i,j)=K0(keep(i),keep(j))+Kb(keep(i),keep(j))+speed*K1(keep(i),keep(j))
   enddo;enddo
   call second_order_eigs(Mc,Cc,Kc,w,Vred,st);if(st/=RD_OK)then;rd_modal_legacy_vectors=st;return;endif
   do j=1,2*nc
     er(j)=real(w(j),rk);ei(j)=aimag(w(j))
     do i=1,ndof;vr((j-1)*ndof+i)=0._rk;vi((j-1)*ndof+i)=0._rk;enddo
     do i=1,nc;vr((j-1)*ndof+keep(i))=real(Vred(i,j),rk);vi((j-1)*ndof+keep(i))=aimag(Vred(i,j));enddo
   enddo
   do i=1,nbear;ecc(i)=ee(i);enddo;rd_modal_legacy_vectors=RD_OK
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

 integer(c_int) function rd_freq_aux_legacy(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,nforce,force,rotor_speed,nfreq,omega,direction,rr,ri) bind(C,name='rd_freq_aux_legacy')
   integer(c_int),value::nnode,nshaft,ndisc,nbear,nforce,nfreq
   real(c_double),intent(in)::z(*),shaft(*),disc(*),bear(*),force(*),omega(*);real(c_double),value::rotor_speed,direction
   real(c_double),intent(out)::rr(*),ri(*)
   real(rk),allocatable::zz(:),sh(:,:),di(:,:),be(:,:),fo(:,:),om(:),M(:,:),C0(:,:),C1(:,:),K0(:,:),K1(:,:),Mb(:,:),Cb(:,:),Kb(:,:),Mt(:,:),Ct(:,:),Kt(:,:)
   complex(rk),allocatable::resp(:,:);logical,allocatable::iz(:);integer::i,j,ndof;integer(ik)::st
   rd_freq_aux_legacy=RD_ERR_INPUT;if(nnode<=0.or.nfreq<=0)return;ndof=4*nnode
   call unpack(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,zz,sh,di,be);allocate(fo(5,nforce),om(nfreq),resp(ndof,nfreq))
   do j=1,nforce;do i=1,5;fo(i,j)=force((j-1)*5+i);enddo;enddo;do i=1,nfreq;om(i)=omega(i);enddo
   allocate(M(ndof,ndof),C0(ndof,ndof),C1(ndof,ndof),K0(ndof,ndof),K1(ndof,ndof),Mb(ndof,ndof),Cb(ndof,ndof),Kb(ndof,ndof),Mt(ndof,ndof),Ct(ndof,ndof),Kt(ndof,ndof),iz(ndof))
   call assemble_rotor(nnode,zz,nshaft,sh,ndisc,di,M,C0,C1,K0,K1,st);if(st/=RD_OK)then;rd_freq_aux_legacy=st;return;endif
   call assemble_bearings(nnode,nbear,be,rotor_speed,Mb,Cb,Kb,iz,st);if(st/=RD_OK)then;rd_freq_aux_legacy=st;return;endif
   Mt=M+Mb;Ct=C0+Cb+rotor_speed*C1;Kt=K0+Kb+rotor_speed*K1
   call auxiliary_frequency_response(Mt,Ct,Kt,iz,fo,nforce,om,nfreq,direction,resp,st);if(st/=RD_OK)then;rd_freq_aux_legacy=st;return;endif
   do j=1,nfreq;do i=1,ndof;rr((j-1)*ndof+i)=real(resp(i,j),rk);ri((j-1)*ndof+i)=aimag(resp(i,j));enddo;enddo;rd_freq_aux_legacy=RD_OK
 end function

 integer(c_int) function rd_freq_fdn_legacy(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,nforce,force,rotor_speed,nfreq,omega,rr,ri) bind(C,name='rd_freq_fdn_legacy')
   integer(c_int),value::nnode,nshaft,ndisc,nbear,nforce,nfreq
   real(c_double),intent(in)::z(*),shaft(*),disc(*),bear(*),force(*),omega(*);real(c_double),value::rotor_speed
   real(c_double),intent(out)::rr(*),ri(*)
   real(rk),allocatable::zz(:),sh(:,:),di(:,:),be(:,:),fo(:,:),om(:),M(:,:),C0(:,:),C1(:,:),K0(:,:),K1(:,:),Mb(:,:),Cb(:,:),Kb(:,:),Mt(:,:),Ct(:,:),Kt(:,:)
   complex(rk),allocatable::resp(:,:);logical,allocatable::iz(:);integer::i,j,ndof;integer(ik)::st
   rd_freq_fdn_legacy=RD_ERR_INPUT;if(nnode<=0.or.nfreq<=0)return;ndof=4*nnode
   call unpack(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,zz,sh,di,be);allocate(fo(5,nforce),om(nfreq),resp(ndof,nfreq))
   do j=1,nforce;do i=1,5;fo(i,j)=force((j-1)*5+i);enddo;enddo;do i=1,nfreq;om(i)=omega(i);enddo
   allocate(M(ndof,ndof),C0(ndof,ndof),C1(ndof,ndof),K0(ndof,ndof),K1(ndof,ndof),Mb(ndof,ndof),Cb(ndof,ndof),Kb(ndof,ndof),Mt(ndof,ndof),Ct(ndof,ndof),Kt(ndof,ndof),iz(ndof))
   call assemble_rotor(nnode,zz,nshaft,sh,ndisc,di,M,C0,C1,K0,K1,st);if(st/=RD_OK)then;rd_freq_fdn_legacy=st;return;endif
   call assemble_bearings(nnode,nbear,be,rotor_speed,Mb,Cb,Kb,iz,st);if(st/=RD_OK)then;rd_freq_fdn_legacy=st;return;endif
   Mt=M+Mb;Ct=C0+Cb+rotor_speed*C1;Kt=K0+Kb+rotor_speed*K1
   call foundation_frequency_response(Mt,Ct,Kt,Mb,Cb,Kb,iz,be,nbear,fo,nforce,om,nfreq,resp,st);if(st/=RD_OK)then;rd_freq_fdn_legacy=st;return;endif
   do j=1,nfreq;do i=1,ndof;rr((j-1)*ndof+i)=real(resp(i,j),rk);ri((j-1)*ndof+i)=aimag(resp(i,j));enddo;enddo;rd_freq_fdn_legacy=RD_OK
 end function

 integer(c_int) function rd_time_fdn_legacy(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,rotor_speed,foundation_amp,pulse_duration,dt,npts,nr,rtol,atol,h_init,h_max,response,force,time,nr_used,maxfreq,naccept,nreject) bind(C,name='rd_time_fdn_legacy')
   integer(c_int),value::nnode,nshaft,ndisc,nbear,npts,nr
   real(c_double),intent(in)::z(*),shaft(*),disc(*),bear(*),foundation_amp(*)
   real(c_double),value::rotor_speed,pulse_duration,dt,rtol,atol,h_init,h_max
   real(c_double),intent(out)::response(*),force(*),time(*),maxfreq
   integer(c_int),intent(out)::nr_used,naccept,nreject
   real(rk),allocatable::zz(:),sh(:,:),di(:,:),be(:,:),amp(:),M0(:,:),C0(:,:),C1(:,:),K0(:,:),K1(:,:),Mb(:,:),Cb(:,:),Kb(:,:),M(:,:),C(:,:),K(:,:),resp(:,:),ff(:),tt(:)
   logical,allocatable::iz(:);integer::i,j,ndof;integer(ik)::st,nru,na,nrj
   rd_time_fdn_legacy=RD_ERR_INPUT;if(nnode<=0.or.nbear<=0.or.npts<=0)return;ndof=4*nnode
   call unpack(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,zz,sh,di,be);allocate(amp(2*nbear));do i=1,2*nbear;amp(i)=foundation_amp(i);enddo
   allocate(M0(ndof,ndof),C0(ndof,ndof),C1(ndof,ndof),K0(ndof,ndof),K1(ndof,ndof),Mb(ndof,ndof),Cb(ndof,ndof),Kb(ndof,ndof),M(ndof,ndof),C(ndof,ndof),K(ndof,ndof),iz(ndof),resp(ndof,npts),ff(npts),tt(npts))
   call assemble_rotor(nnode,zz,nshaft,sh,ndisc,di,M0,C0,C1,K0,K1,st);if(st/=RD_OK)then;rd_time_fdn_legacy=st;return;endif
   call assemble_bearings(nnode,nbear,be,rotor_speed,Mb,Cb,Kb,iz,st);if(st/=RD_OK)then;rd_time_fdn_legacy=st;return;endif
   M=M0+Mb;C=C0+Cb+rotor_speed*C1;K=K0+Kb+rotor_speed*K1
   call time_foundation_response(M,C,K,Mb,Cb,Kb,iz,be,nbear,amp,pulse_duration,dt,npts,int(nr,ik),rtol,atol,h_init,h_max,resp,ff,tt,nru,maxfreq,na,nrj,st)
   if(st/=RD_OK)then;rd_time_fdn_legacy=st;return;endif
   do j=1,npts;force(j)=ff(j);time(j)=tt(j);do i=1,ndof;response((j-1)*ndof+i)=resp(i,j);enddo;enddo
   nr_used=nru;naccept=na;nreject=nrj;rd_time_fdn_legacy=RD_OK
 end function

 integer(c_int) function rd_runup_legacy(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,nforce,force,alpha,t0,tf,nr,rtol,atol,h_init,h_max,max_out,time,response,speed,nout,nr_used,maxfreq,naccept,nreject) bind(C,name='rd_runup_legacy')
   integer(c_int),value::nnode,nshaft,ndisc,nbear,nforce,nr,max_out
   real(c_double),intent(in)::z(*),shaft(*),disc(*),bear(*),force(*),alpha(*)
   real(c_double),value::t0,tf,rtol,atol,h_init,h_max
   real(c_double),intent(out)::time(*),response(*),speed(*),maxfreq
   integer(c_int),intent(out)::nout,nr_used,naccept,nreject
   real(rk),allocatable::zz(:),sh(:,:),di(:,:),be(:,:),fo(:,:),aa(:),M0(:,:),C0(:,:),C1(:,:),K0(:,:),K1(:,:),Mb(:,:),Cb(:,:),Kb(:,:),M(:,:),C(:,:),K(:,:),fc(:,:),tt(:),resp(:,:),ss(:)
   logical,allocatable::iz(:);integer::i,j,node,ftype,ndof;real(rk)::mag,phase,qr,qi;integer(ik)::st,no,nru,na,nrj
   rd_runup_legacy=RD_ERR_INPUT;if(nnode<=0.or.max_out<2)return;ndof=4*nnode
   call unpack(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,zz,sh,di,be)
   do i=1,nbear;if(be(1,i)>6.5_rk)then;rd_runup_legacy=RD_ERR_UNSUPPORTED;return;endif;enddo
   allocate(fo(5,nforce),aa(3));do j=1,nforce;do i=1,5;fo(i,j)=force((j-1)*5+i);enddo;enddo;do i=1,3;aa(i)=alpha(i);enddo
   allocate(M0(ndof,ndof),C0(ndof,ndof),C1(ndof,ndof),K0(ndof,ndof),K1(ndof,ndof),Mb(ndof,ndof),Cb(ndof,ndof),Kb(ndof,ndof),M(ndof,ndof),C(ndof,ndof),K(ndof,ndof),iz(ndof),fc(ndof,2),tt(max_out),resp(ndof,max_out),ss(max_out));fc=0
   call assemble_rotor(nnode,zz,nshaft,sh,ndisc,di,M0,C0,C1,K0,K1,st);if(st/=RD_OK)then;rd_runup_legacy=st;return;endif
   call assemble_bearings(nnode,nbear,be,0._rk,Mb,Cb,Kb,iz,st);if(st/=RD_OK)then;rd_runup_legacy=st;return;endif
   M=M0+Mb;C=C0+Cb;K=K0+Kb
   do i=1,nforce
     ftype=nint(fo(1,i));if(ftype/=1.and.ftype/=2)cycle
     node=nint(fo(2,i));if(node<1.or.node>nnode)then;rd_runup_legacy=RD_ERR_INPUT;return;endif
     mag=fo(3,i);phase=fo(4,i);qr=mag*cos(phase);qi=mag*sin(phase)
     if(ftype==1)then
       fc(4*node-3,1)=fc(4*node-3,1)+qr;fc(4*node-3,2)=fc(4*node-3,2)+qi
       fc(4*node-2,1)=fc(4*node-2,1)+qi;fc(4*node-2,2)=fc(4*node-2,2)-qr
     else
       fc(4*node-1,1)=fc(4*node-1,1)-qi;fc(4*node-1,2)=fc(4*node-1,2)+qr
       fc(4*node,1)=fc(4*node,1)+qr;fc(4*node,2)=fc(4*node,2)+qi
     endif
   enddo
   call runup_response(M,C,C1,K,iz,fc,aa,t0,tf,int(nr,ik),rtol,atol,h_init,h_max,int(max_out,ik),tt,resp,ss,no,nru,maxfreq,na,nrj,st)
   if(st/=RD_OK)then;rd_runup_legacy=st;return;endif
   do j=1,no;time(j)=tt(j);speed(j)=ss(j);do i=1,ndof;response((j-1)*ndof+i)=resp(i,j);enddo;enddo
   nout=no;nr_used=nru;naccept=na;nreject=nrj;rd_runup_legacy=RD_OK
 end function

 integer(c_int) function rd_crit_spd_legacy(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,NX,damped,ncrit,maxiter,tol,out) bind(C,name='rd_crit_spd_legacy')
   integer(c_int),value::nnode,nshaft,ndisc,nbear,damped,ncrit,maxiter;real(c_double),intent(in)::z(*),shaft(*),disc(*),bear(*);real(c_double),value::NX,tol;real(c_double),intent(out)::out(*)
   real(rk),allocatable::zz(:),sh(:,:),di(:,:),be(:,:),M(:,:),C0(:,:),C1(:,:),K0(:,:),K1(:,:),crit(:);integer::i,ndof;integer(ik)::st
   rd_crit_spd_legacy=RD_ERR_INPUT;if(nnode<=0.or.ncrit<=0)return;ndof=4*nnode;call unpack(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,zz,sh,di,be)
   allocate(M(ndof,ndof),C0(ndof,ndof),C1(ndof,ndof),K0(ndof,ndof),K1(ndof,ndof),crit(ncrit));call assemble_rotor(nnode,zz,nshaft,sh,ndisc,di,M,C0,C1,K0,K1,st)
   if(st/=RD_OK)then;rd_crit_spd_legacy=st;return;endif;call critical_speeds(nnode,nbear,be,M,C0,C1,K0,K1,NX,damped/=0,ncrit,maxiter,tol,crit,st)
   if(st/=RD_OK)then;rd_crit_spd_legacy=st;return;endif;do i=1,ncrit;out(i)=crit(i);enddo;rd_crit_spd_legacy=RD_OK
 end function

 integer(c_int) function rd_crit_spd_legacy_ex(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,NX,damped,ncrit,maxiter,tol,method,initial,ninitial,out,iters,conv) bind(C,name='rd_crit_spd_legacy_ex')
   integer(c_int),value::nnode,nshaft,ndisc,nbear,damped,ncrit,maxiter,method,ninitial;real(c_double),intent(in)::z(*),shaft(*),disc(*),bear(*),initial(*);real(c_double),value::NX,tol
   real(c_double),intent(out)::out(*);integer(c_int),intent(out)::iters(*),conv(*)
   real(rk),allocatable::zz(:),sh(:,:),di(:,:),be(:,:),M(:,:),C0(:,:),C1(:,:),K0(:,:),K1(:,:),crit(:),ini(:);integer(ik),allocatable::iterf(:);logical,allocatable::conf(:);integer::i,ndof;integer(ik)::st
   rd_crit_spd_legacy_ex=RD_ERR_INPUT;if(nnode<=0.or.ncrit<=0)return;ndof=4*nnode;call unpack(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,zz,sh,di,be)
   allocate(M(ndof,ndof),C0(ndof,ndof),C1(ndof,ndof),K0(ndof,ndof),K1(ndof,ndof),crit(ncrit),ini(max(1,ninitial)),iterf(ncrit),conf(ncrit));ini=0
   do i=1,ninitial;ini(i)=initial(i);enddo
   call assemble_rotor(nnode,zz,nshaft,sh,ndisc,di,M,C0,C1,K0,K1,st);if(st/=RD_OK)then;rd_crit_spd_legacy_ex=st;return;endif
   call critical_speeds_ex(nnode,nbear,be,M,C0,C1,K0,K1,NX,damped/=0,ncrit,maxiter,tol,int(method,ik),ini,int(ninitial,ik),crit,iterf,conf,st)
   if(st/=RD_OK)then;rd_crit_spd_legacy_ex=st;return;endif
   do i=1,ncrit;out(i)=crit(i);iters(i)=iterf(i);conv(i)=merge(1,0,conf(i));enddo;rd_crit_spd_legacy_ex=RD_OK
 end function

 integer(c_int) function rd_coax_modal_legacy(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,nrotor,rotors,speed,nout,er,ei,vr,vi) bind(C,name='rd_coax_modal_legacy')
   integer(c_int),value::nnode,nshaft,ndisc,nbear,nrotor,nout;real(c_double),intent(in)::z(*),shaft(*),disc(*),bear(*),rotors(*);real(c_double),value::speed
   real(c_double),intent(out)::er(*),ei(*),vr(*),vi(*)
   real(rk),allocatable::zz(:),sh(:,:),di(:,:),be(:,:),ro(:,:);complex(rk),allocatable::w(:),V(:,:);integer::i,j,ndof;integer(ik)::st
   rd_coax_modal_legacy=RD_ERR_INPUT;if(nnode<=0.or.nrotor<=0)return;ndof=4*nnode;call unpack(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,zz,sh,di,be);allocate(ro(3,nrotor))
   do j=1,nrotor;do i=1,3;ro(i,j)=rotors((j-1)*3+i);enddo;enddo;allocate(w(nout),V(ndof,nout))
   call coaxial_eigs(nnode,zz,nshaft,sh,ndisc,di,nbear,be,nrotor,ro,speed,w,V,st);if(st/=RD_OK)then;rd_coax_modal_legacy=st;return;endif
   do j=1,nout;er(j)=real(w(j),rk);ei(j)=aimag(w(j));do i=1,ndof;vr((j-1)*ndof+i)=real(V(i,j),rk);vi((j-1)*ndof+i)=aimag(V(i,j));enddo;enddo;rd_coax_modal_legacy=RD_OK
 end function

 integer(c_int) function rd_coax_freq_rsp_legacy(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,nrotor,rotors,nforce,force,nspeed,speeds,rr,ri) bind(C,name='rd_coax_freq_rsp_legacy')
   integer(c_int),value::nnode,nshaft,ndisc,nbear,nrotor,nforce,nspeed;real(c_double),intent(in)::z(*),shaft(*),disc(*),bear(*),rotors(*),force(*),speeds(*);real(c_double),intent(out)::rr(*),ri(*)
   real(rk),allocatable::zz(:),sh(:,:),di(:,:),be(:,:),ro(:,:),fo(:,:),sp(:);complex(rk),allocatable::resp(:,:);integer::i,j,ndof;integer(ik)::st
   rd_coax_freq_rsp_legacy=RD_ERR_INPUT;if(nnode<=0.or.nrotor<=0.or.nspeed<=0)return;ndof=4*nnode;call unpack(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,zz,sh,di,be)
   allocate(ro(3,nrotor),fo(5,nforce),sp(nspeed),resp(ndof,nspeed));do j=1,nrotor;do i=1,3;ro(i,j)=rotors((j-1)*3+i);enddo;enddo;do j=1,nforce;do i=1,5;fo(i,j)=force((j-1)*5+i);enddo;enddo;do i=1,nspeed;sp(i)=speeds(i);enddo
   call coaxial_frequency_response(nnode,zz,nshaft,sh,ndisc,di,nbear,be,nrotor,ro,nforce,fo,nspeed,sp,resp,st);if(st/=RD_OK)then;rd_coax_freq_rsp_legacy=st;return;endif
   do j=1,nspeed;do i=1,ndof;rr((j-1)*ndof+i)=real(resp(i,j),rk);ri((j-1)*ndof+i)=aimag(resp(i,j));enddo;enddo;rd_coax_freq_rsp_legacy=RD_OK
 end function

 integer(c_int) function rd_asym_assemble_legacy(nnode,z,nshaft,shaft,ndisc,disc,Mout,C0out,C1out,K0out,K1out,K2out) bind(C,name='rd_asym_assemble_legacy')
   integer(c_int),value::nnode,nshaft,ndisc;real(c_double),intent(in)::z(*),shaft(*),disc(*);real(c_double),intent(out)::Mout(*),C0out(*),C1out(*),K0out(*),K1out(*),K2out(*)
   real(rk),allocatable::zz(:),sh(:,:),di(:,:),M(:,:),C0(:,:),C1(:,:),K0(:,:),K1(:,:),K2(:,:);integer::i,j,ndof;integer(ik)::st
   rd_asym_assemble_legacy=RD_ERR_INPUT;if(nnode<=0)return;ndof=4*nnode;call unpack_no_bear(nnode,z,nshaft,shaft,ndisc,disc,zz,sh,di);allocate(M(ndof,ndof),C0(ndof,ndof),C1(ndof,ndof),K0(ndof,ndof),K1(ndof,ndof),K2(ndof,ndof))
   call assemble_rotor_rotating(nnode,zz,nshaft,sh,ndisc,di,M,C0,C1,K0,K1,K2,st);if(st/=RD_OK)then;rd_asym_assemble_legacy=st;return;endif
   do j=1,ndof;do i=1,ndof;Mout((j-1)*ndof+i)=M(i,j);C0out((j-1)*ndof+i)=C0(i,j);C1out((j-1)*ndof+i)=C1(i,j);K0out((j-1)*ndof+i)=K0(i,j);K1out((j-1)*ndof+i)=K1(i,j);K2out((j-1)*ndof+i)=K2(i,j);enddo;enddo;rd_asym_assemble_legacy=RD_OK
 end function

 integer(c_int) function rd_bearasym_legacy(nnode,nbear,bear,Cout,Kout,K1out,zero_mask) bind(C,name='rd_bearasym_legacy')
   integer(c_int),value::nnode,nbear;real(c_double),intent(in)::bear(*);real(c_double),intent(out)::Cout(*),Kout(*),K1out(*);integer(c_int),intent(out)::zero_mask(*)
   real(rk),allocatable::be(:,:),C(:,:),K(:,:),K1(:,:);logical,allocatable::iz(:);integer::i,j,ndof;integer(ik)::st
   rd_bearasym_legacy=RD_ERR_INPUT;if(nnode<=0)return;ndof=4*nnode;allocate(be(34,nbear),C(ndof,ndof),K(ndof,ndof),K1(ndof,ndof),iz(ndof));do j=1,nbear;do i=1,34;be(i,j)=bear((j-1)*34+i);enddo;enddo
   call assemble_bearings_rotating(nnode,nbear,be,C,K,K1,iz,st);if(st/=RD_OK)then;rd_bearasym_legacy=st;return;endif
   do j=1,ndof;do i=1,ndof;Cout((j-1)*ndof+i)=C(i,j);Kout((j-1)*ndof+i)=K(i,j);K1out((j-1)*ndof+i)=K1(i,j);enddo;enddo;do i=1,ndof;zero_mask(i)=merge(1,0,iz(i));enddo;rd_bearasym_legacy=RD_OK
 end function

 integer(c_int) function rd_asym_modal_legacy(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,speed,want_vectors,nout,er,ei,vr,vi) bind(C,name='rd_asym_modal_legacy')
   integer(c_int),value::nnode,nshaft,ndisc,nbear,want_vectors,nout;real(c_double),intent(in)::z(*),shaft(*),disc(*),bear(*);real(c_double),value::speed;real(c_double),intent(out)::er(*),ei(*),vr(*),vi(*)
   real(rk),allocatable::zz(:),sh(:,:),di(:,:),be(:,:);complex(rk),allocatable::w(:),V(:,:);integer::i,j,ndof;integer(ik)::st
   rd_asym_modal_legacy=RD_ERR_INPUT;if(nnode<=0)return;ndof=4*nnode;call unpack(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,zz,sh,di,be);allocate(w(nout),V(ndof,nout))
   call asymmetric_eigs(nnode,zz,nshaft,sh,ndisc,di,nbear,be,speed,want_vectors/=0,w,V,st);if(st/=RD_OK)then;rd_asym_modal_legacy=st;return;endif
   do j=1,nout;er(j)=real(w(j),rk);ei(j)=aimag(w(j));do i=1,ndof;vr((j-1)*ndof+i)=real(V(i,j),rk);vi((j-1)*ndof+i)=aimag(V(i,j));enddo;enddo;rd_asym_modal_legacy=RD_OK
 end function

 integer(c_int) function rd_asym_freq_rsp_legacy(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,nforce,force,nspeed,speeds,response) bind(C,name='rd_asym_freq_rsp_legacy')
   integer(c_int),value::nnode,nshaft,ndisc,nbear,nforce,nspeed;real(c_double),intent(in)::z(*),shaft(*),disc(*),bear(*),force(*),speeds(*);real(c_double),intent(out)::response(*)
   real(rk),allocatable::zz(:),sh(:,:),di(:,:),be(:,:),fo(:,:),sp(:),resp(:,:);integer::i,j,ndof;integer(ik)::st
   rd_asym_freq_rsp_legacy=RD_ERR_INPUT;if(nnode<=0.or.nspeed<=0)return;ndof=4*nnode;call unpack(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,zz,sh,di,be);allocate(fo(5,nforce),sp(nspeed),resp(ndof,nspeed))
   do j=1,nforce;do i=1,5;fo(i,j)=force((j-1)*5+i);enddo;enddo;do i=1,nspeed;sp(i)=speeds(i);enddo
   call asymmetric_frequency_response(nnode,zz,nshaft,sh,ndisc,di,nbear,be,nforce,fo,nspeed,sp,resp,st);if(st/=RD_OK)then;rd_asym_freq_rsp_legacy=st;return;endif
   do j=1,nspeed;do i=1,ndof;response((j-1)*ndof+i)=resp(i,j);enddo;enddo;rd_asym_freq_rsp_legacy=RD_OK
 end function

 subroutine unpack(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,zz,sh,di,be)
   integer,intent(in)::nnode,nshaft,ndisc,nbear;real(c_double),intent(in)::z(*),shaft(*),disc(*),bear(*)
   real(rk),allocatable,intent(out)::zz(:),sh(:,:),di(:,:),be(:,:);integer::i,j
   allocate(zz(nnode),sh(11,nshaft),di(6,ndisc),be(34,nbear));do i=1,nnode;zz(i)=z(i);enddo
   do j=1,nshaft;do i=1,11;sh(i,j)=shaft((j-1)*11+i);enddo;enddo
   do j=1,ndisc;do i=1,6;di(i,j)=disc((j-1)*6+i);enddo;enddo
   do j=1,nbear;do i=1,34;be(i,j)=bear((j-1)*34+i);enddo;enddo
 end subroutine
 subroutine unpack_no_bear(nnode,z,nshaft,shaft,ndisc,disc,zz,sh,di)
   integer,intent(in)::nnode,nshaft,ndisc;real(c_double),intent(in)::z(*),shaft(*),disc(*)
   real(rk),allocatable,intent(out)::zz(:),sh(:,:),di(:,:);integer::i,j
   allocate(zz(nnode),sh(11,nshaft),di(6,ndisc));do i=1,nnode;zz(i)=z(i);enddo
   do j=1,nshaft;do i=1,11;sh(i,j)=shaft((j-1)*11+i);enddo;enddo
   do j=1,ndisc;do i=1,6;di(i,j)=disc((j-1)*6+i);enddo;enddo
 end subroutine
end module rd_c_api
