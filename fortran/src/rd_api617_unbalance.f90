module rd_api617_unbalance
 use, intrinsic::ieee_arithmetic,only:ieee_is_finite
 use rd_kinds,only:rk,ik
 use rd_status,only:RD_OK,RD_ERR_INPUT,RD_ERR_UNSUPPORTED
 use rd_assembly_stationary,only:assemble_rotor,assemble_bearings
 use rd_eigensystem,only:second_order_eigs
 use rd_static,only:static_solve
 implicit none(type,external)
 private
 public::api617_required_sizes,api617_full
 real(rk),parameter::g0=9.8065_rk,forward_ratio_limit=.25_rk
contains

 subroutine api617_required_sizes(nnode,num_modes,nphysical,max_unbalance,status)
 integer(ik),intent(in)::nnode,num_modes
 integer(ik),intent(out)::nphysical,max_unbalance,status
 status=RD_ERR_INPUT;nphysical=0;max_unbalance=0
 if(nnode<2.or.nnode>128.or.num_modes<4.or.mod(num_modes,2)/=0)return
 nphysical=num_modes/2
 if(nphysical<1.or.nphysical>4*nnode)return
 max_unbalance=nnode
 status=RD_OK
 end subroutine

 subroutine base_dynamic(nnode,z,ns,sh,nd,di,nb,be,speed,M,Ceff,K,status)
 integer(ik),intent(in)::nnode,ns,nd,nb
 real(rk),intent(in)::z(nnode),sh(11,ns),di(6,nd),be(34,nb),speed
 real(rk),intent(out)::M(4*nnode,4*nnode),Ceff(4*nnode,4*nnode),K(4*nnode,4*nnode)
 integer(ik),intent(out)::status
 real(rk),allocatable::M0(:,:),C0(:,:),G(:,:),K0(:,:),K1(:,:),Mb(:,:),Cb(:,:),Kb(:,:)
 logical,allocatable::iz(:)
 integer::n
 status=RD_ERR_INPUT;n=4*nnode
 if(ns/=nnode-1.or.nb<1.or..not.ieee_is_finite(speed).or.speed<=0)return
 allocate(M0(n,n),C0(n,n),G(n,n),K0(n,n),K1(n,n),Mb(n,n),Cb(n,n),Kb(n,n),iz(n))
 call assemble_rotor(nnode,z,ns,sh,nd,di,M0,C0,G,K0,K1,status);if(status/=RD_OK)return
 call assemble_bearings(nnode,nb,be,speed,Mb,Cb,Kb,iz,status);if(status/=RD_OK)return
 if(any(iz))then;status=RD_ERR_UNSUPPORTED;return;endif
 M=M0+Mb;Ceff=C0+Cb+speed*G;K=K0+Kb+speed*K1
 if(.not.all(ieee_is_finite(M)).or..not.all(ieee_is_finite(Ceff)).or..not.all(ieee_is_finite(K)))then
  status=RD_ERR_INPUT;return
 endif
 status=RD_OK
 end subroutine

 subroutine positive_modes(M,C,K,nmode,wr,wi,wn,wd,V,nfound,status)
 real(rk),intent(in)::M(:,:),C(:,:),K(:,:)
 integer(ik),intent(in)::nmode
 real(rk),intent(out)::wr(nmode),wi(nmode),wn(nmode),wd(nmode)
 complex(rk),intent(out)::V(size(M,1),nmode)
 integer(ik),intent(out)::nfound,status
 integer::n,i,j,nvalid
 complex(rk),allocatable::w(:),vall(:,:),wp(:),vp(:,:),tv(:)
 complex(rk)::tw
 real(rk)::scale,wdi,wdj,wni,wnj
 n=size(M,1);allocate(w(2*n),vall(n,2*n),wp(2*n),vp(n,2*n),tv(n))
 call second_order_eigs(M,C,K,w,vall,status);if(status/=RD_OK)return
 nvalid=0
 do i=1,2*n
   if(aimag(w(i))<=0._rk)cycle
   if(abs(w(i))<=1e-1_rk)cycle
   nvalid=nvalid+1;wp(nvalid)=w(i);vp(:,nvalid)=vall(:,i)
 enddo
 if(nvalid<nmode)then;status=RD_ERR_UNSUPPORTED;return;endif
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
 wr=0;wi=0;wn=0;wd=0;V=(0._rk,0._rk)
 do i=1,nmode
   wr(i)=real(wp(i),rk);wi(i)=aimag(wp(i));wn(i)=abs(wp(i));wd(i)=aimag(wp(i));V(:,i)=vp(:,i)
 enddo
 nfound=nmode;status=RD_OK
 end subroutine

 subroutine orbit_metrics(x,y,major,kappa,major_angle)
 complex(rk),intent(in)::x,y
 real(rk),intent(out)::major,kappa,major_angle
 real(rk)::ru,rv,nu,nv,h11,h22,h12,tr,disc,lmin,lmax,diff,theta
 ru=abs(x);rv=abs(y);nu=atan2(aimag(x),real(x,rk));nv=atan2(aimag(y),real(y,rk))
 h11=(ru*cos(nu))**2+(ru*sin(nu))**2
 h22=(rv*cos(nv))**2+(rv*sin(nv))**2
 h12=ru*rv*(cos(nu)*cos(nv)+sin(nu)*sin(nv))
 tr=h11+h22;disc=sqrt(max(0._rk,(h11-h22)**2+4._rk*h12*h12))
 lmin=max(0._rk,.5_rk*(tr-disc));lmax=max(0._rk,.5_rk*(tr+disc))
 major=sqrt(lmax)
 diff=nv-nu
 if(diff < -acos(-1._rk))diff=diff+2*acos(-1._rk)
 if(diff >  acos(-1._rk))diff=diff-2*acos(-1._rk)
 if(major<=tiny(1._rk))then
   kappa=0
 elseif(diff==0._rk.or.diff==acos(-1._rk))then
   kappa=0
 elseif(0._rk<diff.and.diff<acos(-1._rk))then
   kappa=-sqrt(lmin)/major
 else
   kappa=sqrt(lmin)/major
 endif
 ! Principal axis of the largest eigenvalue of H.  Axis sign is normalized
 ! to the upper half-plane exactly like frozen Orbit._init_orbit.
 theta=.5_rk*atan2(2._rk*h12,h11-h22)
 if(theta<0)theta=theta+acos(-1._rk)
 if(theta>=acos(-1._rk))theta=theta-acos(-1._rk)
 major_angle=theta
 end subroutine

 real(rk) function mode_whirl_ratio(nnode,v,major_out,kappa_out,angle_out) result(ratio)
 integer(ik),intent(in)::nnode
 complex(rk),intent(in)::v(4*nnode)
 real(rk),intent(out)::major_out(nnode),kappa_out(nnode),angle_out(nnode)
 integer::i
 real(rk)::total
 do i=1,nnode
   call orbit_metrics(v(4*i-3),v(4*i-2),major_out(i),kappa_out(i),angle_out(i))
 enddo
 total=sum(major_out)
 if(total==0._rk)then
   ratio=0._rk
 else
   ratio=sum(kappa_out*major_out)/total
 endif
 end function

 real(rk) function shaft_mass(row,z1,z2) result(m)
 real(rk),intent(in)::row(11),z1,z2
 real(rk)::pi
 pi=acos(-1._rk)
 m=row(6)*pi*(row(4)**2-row(5)**2)*(z2-z1)/4._rk
 end function

 real(rk) function disk_mass(row) result(m)
 real(rk),intent(in)::row(6)
 integer::t
 real(rk)::pi
 pi=acos(-1._rk);t=nint(row(1))
 if(t==1.or.t==3)then
   m=row(3)*pi*row(4)*(row(5)**2-row(6)**2)/4._rk
 else
   m=row(3)
 endif
 end function

 subroutine journal_static_loads(nnode,z,ns,sh,nd,di,nb,be,loads,support,status)
 integer(ik),intent(in)::nnode,ns,nd,nb
 real(rk),intent(in)::z(nnode),sh(11,ns),di(6,nd),be(34,nb)
 real(rk),intent(out)::loads(nnode)
 logical,intent(out)::support(nnode)
 integer(ik),intent(out)::status
 real(rk),allocatable::q(:),reaction(:),sw(:),dw(:),shear(:),bend(:),station(:),diag(:)
 integer::i,n
 allocate(q(4*nnode),reaction(nnode),sw(ns),dw(nd),shear(2*ns),bend(2*ns),station(2*ns),diag(3))
 call static_solve(nnode,z,ns,sh,nd,di,nb,be,q,reaction,sw,dw,shear,bend,station,diag,status)
 if(status/=RD_OK)return
 loads=0._rk;support=.false.
 do i=1,nb
   if(nint(be(1,i))==8)cycle
   n=nint(be(2,i));support(n)=.true.
 enddo
 do n=1,nnode
   if(support(n))loads(n)=abs(reaction(n))/g0
 enddo
 status=RD_OK
 end subroutine

 real(rk) function overhung_mass(nnode,z,ns,sh,nd,di,bearing_node,side) result(mass)
 integer(ik),intent(in)::nnode,ns,nd,bearing_node,side
 real(rk),intent(in)::z(nnode),sh(11,ns),di(6,nd)
 integer::i,n
 mass=0._rk
 if(side<0)then
   do i=1,ns
     if(nint(sh(3,i))<=bearing_node)mass=mass+shaft_mass(sh(:,i),z(i),z(i+1))
   enddo
   do i=1,nd
     n=nint(di(2,i));if(n<bearing_node)mass=mass+disk_mass(di(:,i))
   enddo
 else
   do i=1,ns
     if(nint(sh(2,i))>=bearing_node)mass=mass+shaft_mass(sh(:,i),z(i),z(i+1))
   enddo
   do i=1,nd
     n=nint(di(2,i));if(n>bearing_node.and.n<=nnode)mass=mass+disk_mass(di(:,i))
   enddo
 endif
 end function

 subroutine api617_full(nnode,z,ns,sh,nd,di,nb,be,speed,forward_mode,num_modes,maxout, &
                        nout,nodes,magnitude,phase,static_load,mode_index,mode_frequency, &
                        whirl_ratio,major,kappa,major_angle,projection_real,sign_out,status)
 integer(ik),intent(in)::nnode,ns,nd,nb,forward_mode,num_modes,maxout
 real(rk),intent(in)::z(nnode),sh(11,ns),di(6,nd),be(34,nb),speed
 integer(ik),intent(out)::nout,nodes(maxout),mode_index,status
 real(rk),intent(out)::magnitude(maxout),phase(maxout),static_load(maxout),mode_frequency
 real(rk),intent(out)::whirl_ratio(num_modes/2),major(nnode),kappa(nnode),major_angle(nnode),projection_real(nnode),sign_out(nnode)
 real(rk),allocatable::M(:,:),C(:,:),K(:,:),wr(:),wi(:),wn(:),wd(:),majtmp(:),ktmp(:),atmp(:),loads(:)
 complex(rk),allocatable::V(:,:)
 logical,allocatable::support(:)
 integer,allocatable::forward(:),lobe_start(:),lobe_end(:),anti(:)
 integer::nmode,nfound,i,j,nf,selected,reference,nl,current_start,current_sign,node_sign
 integer::left_b,right_b,n_inboard,nearest
 real(rk)::largest,theta,refproj,amp,load,rpm,residual,best
 status=RD_ERR_INPUT;nout=0;nodes=0;magnitude=0;phase=0;static_load=0;mode_index=-1;mode_frequency=0
 if(speed<=0.or.forward_mode<0.or.maxout<nnode.or.mod(num_modes,2)/=0)return
 nmode=num_modes/2
 allocate(M(4*nnode,4*nnode),C(4*nnode,4*nnode),K(4*nnode,4*nnode))
 allocate(wr(nmode),wi(nmode),wn(nmode),wd(nmode),V(4*nnode,nmode))
 allocate(majtmp(nnode),ktmp(nnode),atmp(nnode),loads(nnode),support(nnode),forward(nmode),lobe_start(nnode),lobe_end(nnode),anti(nnode))
 call base_dynamic(nnode,z,ns,sh,nd,di,nb,be,speed,M,C,K,status);if(status/=RD_OK)return
 call positive_modes(M,C,K,nmode,wr,wi,wn,wd,V,nfound,status);if(status/=RD_OK)return
 nf=0
 do i=1,nmode
   whirl_ratio(i)=mode_whirl_ratio(nnode,V(:,i),majtmp,ktmp,atmp)
   if(whirl_ratio(i)>forward_ratio_limit)then;nf=nf+1;forward(nf)=i;endif
 enddo
 if(nf==0)then
   do i=1,nmode
     if(whirl_ratio(i)>0._rk)then;nf=nf+1;forward(nf)=i;endif
   enddo
 endif
 if(forward_mode+1>nf)then;status=RD_ERR_UNSUPPORTED;return;endif
 selected=forward(forward_mode+1);mode_index=selected-1;mode_frequency=wd(selected)
 whirl_ratio=whirl_ratio
 do i=1,nnode
   call orbit_metrics(V(4*i-3,selected),V(4*i-2,selected),major(i),kappa(i),major_angle(i))
 enddo
 reference=maxloc(major,dim=1);largest=major(reference);theta=major_angle(reference)
 refproj=real(V(4*reference-3,selected),rk)*cos(theta)+real(V(4*reference-2,selected),rk)*sin(theta)
 ! projection is complex in ROSS; only real(proj*conj(ref)) determines sign.
 do i=1,nnode
   projection_real(i)=real((V(4*i-3,selected)*cos(theta)+V(4*i-2,selected)*sin(theta))* &
                    conjg(V(4*reference-3,selected)*cos(theta)+V(4*reference-2,selected)*sin(theta)),rk)
   if(projection_real(i)<0)then;sign_out(i)=-1._rk;else;sign_out(i)=1._rk;endif
 enddo
 ! Frozen lobe segmentation.
 nl=0;current_start=1;current_sign=0
 do i=1,nnode
   node_sign=0
   if(major(i)>=.02_rk*largest)node_sign=nint(sign_out(i))
   if(current_sign/=0.and.node_sign/=0.and.node_sign/=current_sign)then
     nl=nl+1;lobe_start(nl)=current_start;lobe_end(nl)=i-1;current_start=i
   endif
   if(node_sign/=0)current_sign=node_sign
 enddo
 nl=nl+1;lobe_start(nl)=current_start;lobe_end(nl)=nnode
 do j=1,nl
   anti(j)=lobe_start(j)-1+maxloc(major(lobe_start(j):lobe_end(j)),dim=1)
 enddo
 call journal_static_loads(nnode,z,ns,sh,nd,di,nb,be,loads,support,status);if(status/=RD_OK)return
 left_b=0;right_b=0
 do i=1,nnode
   if(support(i))then
     if(left_b==0)left_b=i
     right_b=i
   endif
 enddo
 if(left_b==0.or.right_b==0)then;status=RD_ERR_UNSUPPORTED;return;endif
 n_inboard=0
 do j=1,nl
   i=anti(j);amp=major(i)
   if(i>=left_b.and.i<=right_b)then
     if(amp>=.1_rk*largest)n_inboard=n_inboard+1
   endif
 enddo
 rpm=speed*60._rk/(2._rk*acos(-1._rk))
 do j=1,nl
   i=anti(j);amp=major(i)
   if(i>=left_b.and.i<=right_b)then
     if(amp<.1_rk*largest)cycle
   else
     if(i/=reference.and.amp<.5_rk*largest)cycle
   endif
   if(nout>=maxout)then;status=RD_ERR_INPUT;return;endif
   nout=nout+1;nodes(nout)=i
   if(i>=left_b.and.i<=right_b.and.n_inboard==1)then
     load=sum(loads)
   elseif(i>=left_b.and.i<=right_b)then
     nearest=left_b;best=abs(z(left_b)-z(i))
     do selected=left_b,right_b
       if(.not.support(selected))cycle
       if(abs(z(selected)-z(i))<best)then;best=abs(z(selected)-z(i));nearest=selected;endif
     enddo
     load=loads(nearest)
   elseif(i<left_b)then
     load=overhung_mass(nnode,z,ns,sh,nd,di,left_b,-1)
   else
     load=overhung_mass(nnode,z,ns,sh,nd,di,right_b,1)
   endif
   if(rpm<25000._rk)then
     residual=6350._rk*load/rpm
   else
     residual=load/3.937_rk
   endif
   magnitude(nout)=2._rk*residual*1e-6_rk
   phase(nout)=merge(0._rk,acos(-1._rk),sign_out(i)==sign_out(reference))
   static_load(nout)=load
 enddo
 if(nout<1)then;status=RD_ERR_UNSUPPORTED;return;endif
 status=RD_OK
 end subroutine
end module rd_api617_unbalance
