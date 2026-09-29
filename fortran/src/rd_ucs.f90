module rd_ucs
 use, intrinsic::ieee_arithmetic,only:ieee_is_finite
 use rd_kinds,only:rk,ik
 use rd_status,only:RD_OK,RD_ERR_INPUT,RD_ERR_UNSUPPORTED
 use rd_assembly_stationary,only:assemble_rotor
 use rd_eigensystem,only:second_order_eigs
 use rd_intersections,only:curve_intersections
 use rd_rouch,only:rouch_mass
 implicit none(type,external)
 private
 public::ucs_required_sizes,ucs_logspace,ucs_map,ucs_matrix,ucs_full
contains
 subroutine ucs_required_sizes(nk,num_modes,ncoeff,nbspeed,nbranch,maxint,ncritmode,status)
 integer(ik),intent(in)::nk,num_modes,ncoeff,nbspeed
 integer(ik),intent(out)::nbranch,maxint,ncritmode,status
 status=RD_ERR_INPUT;nbranch=0;maxint=0;ncritmode=6
 if(nk<2.or.num_modes<4.or.ncoeff<1.or.ncoeff>2.or.nbspeed<2)return
 nbranch=num_modes/4
 if(nbranch<1)return
 if((nk-1)>huge(maxint)/max(1,(nbspeed-1)*ncoeff*nbranch))return
 maxint=nbranch*ncoeff*(nk-1)*(nbspeed-1)
 status=RD_OK
 end subroutine

 subroutine ucs_logspace(start_exp,stop_exp,nk,grid,status)
 real(rk),intent(in)::start_exp,stop_exp
 integer(ik),intent(in)::nk
 real(rk),intent(out)::grid(nk)
 integer(ik),intent(out)::status
 integer::i
 real(rk)::step
 status=RD_ERR_INPUT
 if(nk<2.or..not.ieee_is_finite(start_exp).or..not.ieee_is_finite(stop_exp))return
 if(stop_exp<=start_exp)return
 step=(stop_exp-start_exp)/real(nk-1,rk)
 do i=1,nk
   grid(i)=10._rk**(start_exp+real(i-1,rk)*step)
 enddo
 if(.not.all(ieee_is_finite(grid)).or.any(grid<=0))return
 status=RD_OK
 end subroutine

 subroutine support_stiffness(nnode,nsupport,support_nodes,ks,Kmat,status)
 integer(ik),intent(in)::nnode,nsupport,support_nodes(nsupport)
 real(rk),intent(in)::ks
 real(rk),intent(inout)::Kmat(4*nnode,4*nnode)
 integer(ik),intent(out)::status
 integer::i,n,x,y
 status=RD_ERR_INPUT
 if(nsupport<1.or..not.ieee_is_finite(ks).or.ks<=0)return
 do i=1,nsupport
   n=support_nodes(i)
   if(n<1.or.n>nnode)return
   x=4*n-3;y=4*n-2
   Kmat(x,x)=Kmat(x,x)+ks;Kmat(y,y)=Kmat(y,y)+ks
 enddo
 status=RD_OK
 end subroutine

 subroutine zero_damping_shaft(ns,sh_in,sh_out)
 integer(ik),intent(in)::ns
 real(rk),intent(in)::sh_in(11,ns)
 real(rk),intent(out)::sh_out(11,ns)
 integer::i,stype
 sh_out=sh_in
 do i=1,ns
   stype=nint(sh_out(1,i))
   if(stype>=1.and.stype<=8)sh_out(9,i)=0._rk
 enddo
 end subroutine

 subroutine build_temp(nnode,z,ns,sh,nd,di,nsupport,support_nodes,ks,synchronous,Mmat,Cmat,Gmat,Kmat,status)
 integer(ik),intent(in)::nnode,ns,nd,nsupport,support_nodes(nsupport),synchronous
 real(rk),intent(in)::z(nnode),sh(11,ns),di(6,nd),ks
 real(rk),intent(out)::Mmat(4*nnode,4*nnode),Cmat(4*nnode,4*nnode),Gmat(4*nnode,4*nnode),Kmat(4*nnode,4*nnode)
 integer(ik),intent(out)::status
 real(rk),allocatable::sh0(:,:),M0(:,:),C0(:,:),K1(:,:),Ms(:,:)
 if(synchronous/=0.and.synchronous/=1)then;status=RD_ERR_INPUT;return;endif
 allocate(sh0(11,ns));call zero_damping_shaft(ns,sh,sh0)
 allocate(M0(4*nnode,4*nnode),C0(4*nnode,4*nnode),K1(4*nnode,4*nnode),Ms(4*nnode,4*nnode))
 call assemble_rotor(nnode,z,ns,sh0,nd,di,M0,C0,Gmat,Kmat,K1,status);if(status/=RD_OK)return
 ! UCS temporary rotor has no seals, no bearing damping, and zero shaft
 ! proportional damping. The only support contribution is isotropic K.
 Cmat=0._rk
 call support_stiffness(nnode,nsupport,support_nodes,ks,Kmat,status);if(status/=RD_OK)return
 if(synchronous==1)then
   call rouch_mass(nnode,M0,Gmat,Ms,status);if(status/=RD_OK)return
   Mmat=Ms
 else
   Mmat=M0
 endif
 if(.not.all(ieee_is_finite(Mmat)).or..not.all(ieee_is_finite(Kmat)).or..not.all(ieee_is_finite(Gmat)))then
   status=RD_ERR_INPUT;return
 endif
 status=RD_OK
 end subroutine

 subroutine positive_modes(M,C,K,maxm,synchronous,wr,wi,wn,wd,zeta,logdec,nfound,status)
 real(rk),intent(in)::M(:,:),C(:,:),K(:,:)
 integer(ik),intent(in)::maxm,synchronous
 real(rk),intent(out)::wr(maxm),wi(maxm),wn(maxm),wd(maxm),zeta(maxm),logdec(maxm)
 integer(ik),intent(out)::nfound,status
 integer::n,i,j,nvalid
 complex(rk),allocatable::w(:),wp(:),V(:,:)
 complex(rk)::tw
 real(rk)::td,pi_,wdi,wdj,wni,wnj,round_scale
 n=size(M,1);allocate(w(2*n),wp(2*n),V(n,2*n))
 call second_order_eigs(M,C,K,w,V,status);if(status/=RD_OK)return
 if(synchronous/=0.and.synchronous/=1)then;status=RD_ERR_INPUT;return;endif

 ! Frozen ROSS synchronous/Rouch _eigen() first removes real roots and roots
 ! with |real/imag| >= 1000, then _index() sorts rounded (10 decimal) values
 ! by sign, wd and wn.  Since UCS consumes the positive-imaginary half, build
 ! that exact admissible set before selecting modal.wn[::2].
 nvalid=0
 do i=1,2*n
   if(aimag(w(i))<=0._rk)cycle
   if(synchronous==1)then
     if(abs(real(w(i),rk)/aimag(w(i)))>=1000._rk)cycle
   endif
   nvalid=nvalid+1
   wp(nvalid)=w(i)
 enddo
 if(nvalid<1)then;status=RD_ERR_UNSUPPORTED;return;endif

 round_scale=1.0e10_rk
 do i=1,nvalid-1
   do j=i+1,nvalid
     wdi=anint(aimag(wp(i))*round_scale)/round_scale
     wdj=anint(aimag(wp(j))*round_scale)/round_scale
     wni=anint(abs(wp(i))*round_scale)/round_scale
     wnj=anint(abs(wp(j))*round_scale)/round_scale
     if(wdj<wdi.or.(wdj==wdi.and.wnj<wni))then
       tw=wp(i);wp(i)=wp(j);wp(j)=tw
     endif
   enddo
 enddo

 nfound=min(nvalid,int(maxm))
 wr=0;wi=0;wn=0;wd=0;zeta=0;logdec=0;pi_=acos(-1._rk)
 do i=1,nfound
   wr(i)=real(wp(i),rk);wi(i)=aimag(wp(i));wn(i)=abs(wp(i));wd(i)=aimag(wp(i))
   if(wn(i)>0)zeta(i)=-wr(i)/wn(i)
   td=1._rk-zeta(i)**2
   if(td>0)logdec(i)=2*pi_*zeta(i)/sqrt(td)
 enddo
 status=RD_OK
 end subroutine

 subroutine ucs_map(nnode,z,ns,sh,nd,di,nsupport,support_nodes,start_exp,stop_exp,nk,num_modes,synchronous,grid,rotor_wn,status)
 integer(ik),intent(in)::nnode,ns,nd,nsupport,support_nodes(nsupport),nk,num_modes,synchronous
 real(rk),intent(in)::z(nnode),sh(11,ns),di(6,nd),start_exp,stop_exp
 real(rk),intent(out)::grid(nk),rotor_wn(num_modes/4,nk)
 integer(ik),intent(out)::status
 real(rk),allocatable::Mmat(:,:),Cmat(:,:),Gmat(:,:),Kmat(:,:),wr(:),wi(:),wn(:),wd(:),ze(:),ld(:)
 integer::i,j,need,nfound
 need=num_modes/2
 if(nnode<2.or.ns/=nnode-1.or.nd<0.or.nsupport<1.or.nk<2.or.num_modes<4.or.num_modes/4<1)then;status=RD_ERR_INPUT;return;endif
 call ucs_logspace(start_exp,stop_exp,nk,grid,status);if(status/=RD_OK)return
 allocate(Mmat(4*nnode,4*nnode),Cmat(4*nnode,4*nnode),Gmat(4*nnode,4*nnode),Kmat(4*nnode,4*nnode))
 allocate(wr(need),wi(need),wn(need),wd(need),ze(need),ld(need));rotor_wn=0
 do i=1,nk
   call build_temp(nnode,z,ns,sh,nd,di,nsupport,support_nodes,grid(i),synchronous,Mmat,Cmat,Gmat,Kmat,status);if(status/=RD_OK)return
   call positive_modes(Mmat,Cmat,Kmat,need,synchronous,wr,wi,wn,wd,ze,ld,nfound,status);if(status/=RD_OK)return
   if(nfound<2*(num_modes/4)-1)then;status=RD_ERR_UNSUPPORTED;return;endif
   do j=1,num_modes/4
     rotor_wn(j,i)=wn(2*j-1)
   enddo
 enddo
 status=RD_OK
 end subroutine

 subroutine ucs_matrix(nnode,z,ns,sh,nd,di,nsupport,support_nodes,ks,synchronous,Mmat,Cmat,Gmat,Kmat,status)
 integer(ik),intent(in)::nnode,ns,nd,nsupport,support_nodes(nsupport),synchronous
 real(rk),intent(in)::z(nnode),sh(11,ns),di(6,nd),ks
 real(rk),intent(out)::Mmat(4*nnode,4*nnode),Cmat(4*nnode,4*nnode),Gmat(4*nnode,4*nnode),Kmat(4*nnode,4*nnode)
 integer(ik),intent(out)::status
 call build_temp(nnode,z,ns,sh,nd,di,nsupport,support_nodes,ks,synchronous,Mmat,Cmat,Gmat,Kmat,status)
 end subroutine

 subroutine ucs_full(nnode,z,ns,sh,nd,di,nsupport,support_nodes,start_exp,stop_exp,nk,num_modes,synchronous, &
                     nbspeed,bearing_speed,kxx,kyy,ncoeff,maxint,grid,rotor_wn,nint,ikcrit,ispeed,imode,isource, &
                     cer,cei,cwn,cwd,czeta,clogdec,status)
 integer(ik),intent(in)::nnode,ns,nd,nsupport,support_nodes(nsupport),nk,num_modes,synchronous,nbspeed,ncoeff,maxint
 real(rk),intent(in)::z(nnode),sh(11,ns),di(6,nd),start_exp,stop_exp,bearing_speed(nbspeed),kxx(nbspeed),kyy(nbspeed)
 real(rk),intent(out)::grid(nk),rotor_wn(num_modes/4,nk),ikcrit(maxint),ispeed(maxint)
 integer(ik),intent(out)::nint,imode(maxint),isource(maxint),status
 real(rk),intent(out)::cer(6,maxint),cei(6,maxint),cwn(6,maxint),cwd(6,maxint),czeta(6,maxint),clogdec(6,maxint)
 integer::im,ic,q,got,room,nfound
 real(rk),allocatable::tx(:),ty(:),Mmat(:,:),Cmat(:,:),Gmat(:,:),Kmat(:,:),wr(:),wi(:),wn(:),wd(:),ze(:),ld(:)
 if(ncoeff<1.or.ncoeff>2.or.maxint<0.or.nbspeed<2)then;status=RD_ERR_INPUT;return;endif
 if(any(.not.ieee_is_finite(bearing_speed)).or.any(.not.ieee_is_finite(kxx)).or.any(.not.ieee_is_finite(kyy)))then;status=RD_ERR_INPUT;return;endif
 if(any(bearing_speed(2:)<bearing_speed(:nbspeed-1)))then;status=RD_ERR_INPUT;return;endif
 call ucs_map(nnode,z,ns,sh,nd,di,nsupport,support_nodes,start_exp,stop_exp,nk,num_modes,synchronous,grid,rotor_wn,status);if(status/=RD_OK)return
 nint=0;ikcrit=0;ispeed=0;imode=0;isource=0;cer=0;cei=0;cwn=0;cwd=0;czeta=0;clogdec=0
 allocate(tx(max(1,(nk-1)*(nbspeed-1))),ty(max(1,(nk-1)*(nbspeed-1))))
 allocate(Mmat(4*nnode,4*nnode),Cmat(4*nnode,4*nnode),Gmat(4*nnode,4*nnode),Kmat(4*nnode,4*nnode))
 allocate(wr(6),wi(6),wn(6),wd(6),ze(6),ld(6))
 do im=1,num_modes/4
   do ic=1,ncoeff
     room=maxint-nint
     if(room<0)then;status=RD_ERR_INPUT;return;endif
     if(ic==1)then
       call curve_intersections(nk,grid,rotor_wn(im,:),nbspeed,kxx,bearing_speed,size(tx),got,tx,ty,status)
     else
       call curve_intersections(nk,grid,rotor_wn(im,:),nbspeed,kyy,bearing_speed,size(tx),got,tx,ty,status)
     endif
     if(status/=RD_OK)return
     if(got>room)then;status=RD_ERR_INPUT;return;endif
     do q=1,got
       nint=nint+1;ikcrit(nint)=tx(q);ispeed(nint)=ty(q);imode(nint)=im;isource(nint)=ic
       ! Frozen ROSS critical point solve is standard non-Rouch even when the
       ! map was generated with synchronous=True.
       call build_temp(nnode,z,ns,sh,nd,di,nsupport,support_nodes,tx(q),0_ik,Mmat,Cmat,Gmat,Kmat,status);if(status/=RD_OK)return
       Cmat=ty(q)*Gmat
       call positive_modes(Mmat,Cmat,Kmat,6_ik,0_ik,wr,wi,wn,wd,ze,ld,nfound,status);if(status/=RD_OK)return
       if(nfound<6)then;status=RD_ERR_UNSUPPORTED;return;endif
       cer(:,nint)=wr;cei(:,nint)=wi;cwn(:,nint)=wn;cwd(:,nint)=wd;czeta(:,nint)=ze;clogdec(:,nint)=ld
     enddo
   enddo
 enddo
 status=RD_OK
 end subroutine
end module rd_ucs
