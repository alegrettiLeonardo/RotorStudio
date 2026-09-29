module rd_level1
 use, intrinsic::ieee_arithmetic,only:ieee_is_finite
 use rd_kinds,only:rk,ik
 use rd_status,only:RD_OK,RD_ERR_INPUT,RD_ERR_UNSUPPORTED
 use rd_assembly_stationary,only:assemble_rotor,assemble_bearings
 use rd_eigensystem,only:second_order_eigs
 implicit none(type,external)
 private
 public::level1_required_sizes,level1_matrix,level1_full
contains

 subroutine level1_required_sizes(nnode,nq,nmodes,nstate,status)
 integer(ik),intent(in)::nnode,nq
 integer(ik),intent(out)::nmodes,nstate,status
 status=RD_ERR_INPUT;nmodes=0;nstate=0
 if(nnode<2.or.nnode>128.or.nq<2.or.nq>4096)return
 nmodes=min(6_ik,4_ik*nnode)
 nstate=2_ik*4_ik*nnode
 status=RD_OK
 end subroutine

 subroutine base_matrices(nnode,z,ns,sh,nd,di,nb,be,speed,M,C,G,K,status)
 integer(ik),intent(in)::nnode,ns,nd,nb
 real(rk),intent(in)::z(nnode),sh(11,ns),di(6,nd),be(34,nb),speed
 real(rk),intent(out)::M(4*nnode,4*nnode),C(4*nnode,4*nnode),G(4*nnode,4*nnode),K(4*nnode,4*nnode)
 integer(ik),intent(out)::status
 real(rk),allocatable::M0(:,:),C0(:,:),K0(:,:),K1(:,:),Mb(:,:),Cb(:,:),Kb(:,:)
 logical,allocatable::iz(:)
 integer::n
 n=4*nnode
 status=RD_ERR_INPUT
 if(ns/=nnode-1.or.nb<1.or..not.ieee_is_finite(speed).or.speed<0)return
 allocate(M0(n,n),C0(n,n),K0(n,n),K1(n,n),Mb(n,n),Cb(n,n),Kb(n,n),iz(n))
 call assemble_rotor(nnode,z,ns,sh,nd,di,M0,C0,G,K0,K1,status);if(status/=RD_OK)return
 call assemble_bearings(nnode,nb,be,speed,Mb,Cb,Kb,iz,status);if(status/=RD_OK)return
 ! Initial A6 scope excludes rigid/linked constraints.  Reject instead of
 ! silently reducing a different topology.
 if(any(iz))then;status=RD_ERR_UNSUPPORTED;return;endif
 M=M0+Mb
 C=C0+Cb+speed*G
 K=K0+Kb+speed*K1
 if(.not.all(ieee_is_finite(M)).or..not.all(ieee_is_finite(C)).or. &
    .not.all(ieee_is_finite(G)).or..not.all(ieee_is_finite(K)))then
   status=RD_ERR_INPUT;return
 endif
 status=RD_OK
 end subroutine

 subroutine add_cross_coupling(nnode,node,Q,K,status)
 integer(ik),intent(in)::nnode,node
 real(rk),intent(in)::Q
 real(rk),intent(inout)::K(4*nnode,4*nnode)
 integer(ik),intent(out)::status
 integer::x,y
 status=RD_ERR_INPUT
 if(node<1.or.node>nnode.or..not.ieee_is_finite(Q))return
 x=4*node-3;y=4*node-2
 K(x,y)=K(x,y)+Q
 K(y,x)=K(y,x)-Q
 status=RD_OK
 end subroutine

 subroutine ross_positive_modes(M,C,K,nmode,wr,wi,wn,wd,zeta,logdec,V,nfound,status)
 real(rk),intent(in)::M(:,:),C(:,:),K(:,:)
 integer(ik),intent(in)::nmode
 real(rk),intent(out)::wr(nmode),wi(nmode),wn(nmode),wd(nmode),zeta(nmode),logdec(nmode)
 complex(rk),intent(out)::V(size(M,1),nmode)
 integer(ik),intent(out)::nfound,status
 integer::n,i,j,nvalid,idx
 complex(rk),allocatable::w(:),vall(:,:),wp(:),vp(:,:)
 complex(rk)::tw
 complex(rk),allocatable::tv(:)
 real(rk)::pi_,td,scale,wdi,wdj,wni,wnj
 n=size(M,1)
 allocate(w(2*n),vall(n,2*n),wp(2*n),vp(n,2*n),tv(n))
 call second_order_eigs(M,C,K,w,vall,status);if(status/=RD_OK)return
 nvalid=0
 do i=1,2*n
   if(aimag(w(i))<=0._rk)cycle
   if(abs(w(i))<=1e-1_rk)cycle
   nvalid=nvalid+1;wp(nvalid)=w(i);vp(:,nvalid)=vall(:,i)
 enddo
 if(nvalid<1)then;status=RD_ERR_UNSUPPORTED;return;endif
 ! Frozen Rotor._index rounds to 10 decimals then sorts positive-imag roots by
 ! wd and wn.  Reproduce that ordering before run_modal takes its first modes.
 scale=1e10_rk
 do i=1,nvalid-1
   do j=i+1,nvalid
     wdi=anint(aimag(wp(i))*scale)/scale;wdj=anint(aimag(wp(j))*scale)/scale
     wni=anint(abs(wp(i))*scale)/scale;wnj=anint(abs(wp(j))*scale)/scale
     if(wdj<wdi.or.(wdj==wdi.and.wnj<wni))then
       tw=wp(i);wp(i)=wp(j);wp(j)=tw
       tv=vp(:,i);vp(:,i)=vp(:,j);vp(:,j)=tv
     endif
   enddo
 enddo
 nfound=min(int(nmode),nvalid)
 wr=0;wi=0;wn=0;wd=0;zeta=0;logdec=0;V=(0._rk,0._rk);pi_=acos(-1._rk)
 do idx=1,nfound
   wr(idx)=real(wp(idx),rk);wi(idx)=aimag(wp(idx));wn(idx)=abs(wp(idx));wd(idx)=aimag(wp(idx))
   if(wn(idx)>0)zeta(idx)=-wr(idx)/wn(idx)
   td=1._rk-zeta(idx)**2
   if(td>0)logdec(idx)=2*pi_*zeta(idx)/sqrt(td)
   V(:,idx)=vp(:,idx)
 enddo
 status=RD_OK
 end subroutine

 integer(ik) function orbit_direction(x,y) result(direction)
 complex(rk),intent(in)::x,y
 real(rk)::ru,rv,nu,nv,diff,c,s11,s22,s12,tr,disc,lmin,lmax,kappa
 ! 1 Forward, 2 Mixed (mode-level only), 3 Backward
 ru=abs(x);rv=abs(y);nu=atan2(aimag(x),real(x,rk));nv=atan2(aimag(y),real(y,rk))
 s11=ru*ru;s22=rv*rv;s12=ru*rv*cos(nu-nv)
 tr=s11+s22;disc=sqrt(max(0._rk,(s11-s22)**2+4._rk*s12*s12))
 lmin=max(0._rk,.5_rk*(tr-disc));lmax=max(0._rk,.5_rk*(tr+disc))
 diff=nv-nu
 if(diff < -acos(-1._rk))diff=diff+2*acos(-1._rk)
 if(diff >  acos(-1._rk))diff=diff-2*acos(-1._rk)
 if(lmax<=tiny(1._rk))then
   kappa=0
 elseif(diff==0._rk.or.diff==acos(-1._rk))then
   kappa=0
 elseif(0._rk<diff.and.diff<acos(-1._rk))then
   kappa=-sqrt(lmin/lmax)
 else
   kappa=sqrt(lmin/lmax)
 endif
 direction=merge(1_ik,3_ik,kappa>0._rk)
 end function

 integer(ik) function mode_direction(nnode,v) result(direction)
 integer(ik),intent(in)::nnode
 complex(rk),intent(in)::v(4*nnode)
 integer::node,nf,nb,d
 nf=0;nb=0
 do node=1,nnode
   d=orbit_direction(v(4*node-3),v(4*node-2))
   if(d==1)nf=nf+1
   if(d==3)nb=nb+1
 enddo
 if(nf==nnode)then
   direction=1_ik
 elseif(nb==nnode)then
   direction=3_ik
 else
   direction=2_ik
 endif
 end function

 subroutine level1_matrix(nnode,z,ns,sh,nd,di,nb,be,speed,node,Q,M,C,G,K,status)
 integer(ik),intent(in)::nnode,ns,nd,nb,node
 real(rk),intent(in)::z(nnode),sh(11,ns),di(6,nd),be(34,nb),speed,Q
 real(rk),intent(out)::M(4*nnode,4*nnode),C(4*nnode,4*nnode),G(4*nnode,4*nnode),K(4*nnode,4*nnode)
 integer(ik),intent(out)::status
 call base_matrices(nnode,z,ns,sh,nd,di,nb,be,speed,M,C,G,K,status);if(status/=RD_OK)return
 call add_cross_coupling(nnode,node,Q,K,status)
 end subroutine

 subroutine level1_full(nnode,z,ns,sh,nd,di,nb,be,speed,node,q0,q1,nq,nmode, &
                        qgrid,selected_logdec,selected_mode,mode_dir,wr,wi,wn,wd,zeta,logdec,status)
 integer(ik),intent(in)::nnode,ns,nd,nb,node,nq,nmode
 real(rk),intent(in)::z(nnode),sh(11,ns),di(6,nd),be(34,nb),speed,q0,q1
 real(rk),intent(out)::qgrid(nq),selected_logdec(nq)
 integer(ik),intent(out)::selected_mode(nq),mode_dir(nmode,nq)
 real(rk),intent(out)::wr(nmode,nq),wi(nmode,nq),wn(nmode,nq),wd(nmode,nq),zeta(nmode,nq),logdec(nmode,nq)
 integer(ik),intent(out)::status
 real(rk),allocatable::M(:,:),C(:,:),G(:,:),K(:,:),rwr(:),rwi(:),rwn(:),rwd(:),rz(:),rld(:)
 complex(rk),allocatable::V(:,:)
 integer::i,j,nfound,first
 status=RD_ERR_INPUT
 if(nq<2.or.nmode<1.or.node<1.or.node>nnode.or..not.ieee_is_finite(q0).or..not.ieee_is_finite(q1).or.q1<=q0)return
 allocate(M(4*nnode,4*nnode),C(4*nnode,4*nnode),G(4*nnode,4*nnode),K(4*nnode,4*nnode))
 allocate(rwr(nmode),rwi(nmode),rwn(nmode),rwd(nmode),rz(nmode),rld(nmode),V(4*nnode,nmode))
 do i=1,nq
   qgrid(i)=q0+(q1-q0)*real(i-1,rk)/real(nq-1,rk)
 enddo
 selected_logdec=0;selected_mode=0;mode_dir=0;wr=0;wi=0;wn=0;wd=0;zeta=0;logdec=0
 do i=1,nq
   call level1_matrix(nnode,z,ns,sh,nd,di,nb,be,speed,node,qgrid(i),M,C,G,K,status);if(status/=RD_OK)return
   call ross_positive_modes(M,C,K,nmode,rwr,rwi,rwn,rwd,rz,rld,V,nfound,status);if(status/=RD_OK)return
   if(nfound<nmode)then;status=RD_ERR_UNSUPPORTED;return;endif
   first=0
   do j=1,nmode
     mode_dir(j,i)=mode_direction(nnode,V(:,j))
     wr(j,i)=rwr(j);wi(j,i)=rwi(j);wn(j,i)=rwn(j);wd(j,i)=rwd(j);zeta(j,i)=rz(j);logdec(j,i)=rld(j)
     if(first==0.and.mode_dir(j,i)/=3)first=j
   enddo
   if(first==0)then;status=RD_ERR_UNSUPPORTED;return;endif
   selected_mode(i)=first
   selected_logdec(i)=rld(first)
 enddo
 if(.not.all(ieee_is_finite(selected_logdec)))then;status=RD_ERR_INPUT;return;endif
 status=RD_OK
 end subroutine
end module rd_level1
