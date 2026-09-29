module rd_clearance
 use, intrinsic::ieee_arithmetic,only:ieee_is_finite
 use rd_kinds,only:rk,ik
 use rd_status,only:RD_OK,RD_ERR_INPUT,RD_ERR_UNSUPPORTED
 use rd_forced_response,only:forced_response,forced_size_valid
 use rd_api617_unbalance,only:api617_full
 implicit none(type,external)
 private
 public::clearance_required_sizes,clearance_full
contains

 subroutine clearance_required_sizes(nnode,nf,nprobe,nclear,max_unbalance,status)
 integer(ik),intent(in)::nnode,nf,nprobe,nclear
 integer(ik),intent(out)::max_unbalance,status
 status=RD_ERR_INPUT;max_unbalance=0
 if(nnode<2.or.nnode>128.or.nf<1.or.nf>10000.or.nprobe<1.or.nprobe>nnode*4.or.nclear<1.or.nclear>nnode*4)return
 if(.not.forced_size_valid(nnode,nf))return
 max_unbalance=nnode
 status=RD_OK
 end subroutine

 pure real(rk) function major_axis(x,y) result(a)
 complex(rk),intent(in)::x,y
 real(rk)::h11,h22,h12,tr,disc
 h11=abs(x)**2;h22=abs(y)**2;h12=real(x*conjg(y),rk)
 tr=h11+h22
 disc=sqrt(max(0._rk,(h11-h22)**2+4._rk*h12*h12))
 a=sqrt(max(0._rk,.5_rk*(tr+disc)))
 end function

 subroutine clearance_full(nn,z,ns,sh,nd,di,nb,bnodes,coeff,be_nmc,nf,speed,nma,nmc, &
                           nprobe,probe_nodes,probe_angles,nclear,clear_nodes,radial_clearance, &
                           explicit_ub,nub_in,ub_nodes_in,ub_mag_in,ub_phase_in,mode,num_modes, &
                           cap_enabled,cap,maxout,nout,ub_nodes,ub_mag,ub_phase,mode_index,mode_frequency, &
                           probe_response,vibration_limit,max_probe_amplitude,scale_factor, &
                           diametral_clearance,clearance_response,max_clearance_response,speed_at_max,passed,status)
 integer(ik),intent(in)::nn,ns,nd,nb,nf,nprobe,nclear,explicit_ub,nub_in,mode,num_modes,cap_enabled,maxout
 integer(ik),intent(in)::bnodes(nb),probe_nodes(nprobe),clear_nodes(nclear),ub_nodes_in(maxout)
 real(rk),intent(in)::z(nn),sh(11,ns),di(6,nd),coeff(12,nb,nf),be_nmc(34,nb),speed(nf),nma,nmc
 real(rk),intent(in)::probe_angles(nprobe),radial_clearance(nclear),ub_mag_in(maxout),ub_phase_in(maxout),cap
 integer(ik),intent(out)::nout,ub_nodes(maxout),mode_index,passed(nclear),status
 real(rk),intent(out)::ub_mag(maxout),ub_phase(maxout),mode_frequency
 real(rk),intent(out)::probe_response(nprobe,nf),vibration_limit,max_probe_amplitude,scale_factor
 real(rk),intent(out)::diametral_clearance(nclear),clearance_response(nclear,nf),max_clearance_response(nclear),speed_at_max(nclear)

 real(rk),allocatable::fr(:,:),fi(:,:),qr(:,:),qi(:,:),vr(:,:),vi(:,:),ar(:,:),ai(:,:),res(:),cond(:)
 real(rk),allocatable::ratio(:),major(:),kappa(:),angle(:),proj(:),sgn(:),dummy_load(:)
 integer(ik),allocatable::dummy_nodes(:)
 real(rk)::rpm,c,s,a
 complex(rk)::x,y,p
 integer::i,j,k,dof,nphysical,imax
 status=RD_ERR_INPUT;nout=0;ub_nodes=0;ub_mag=0;ub_phase=0;mode_index=-1;mode_frequency=0
 if(.not.forced_size_valid(nn,nf).or.ns/=nn-1.or.nb<1.or.nprobe<1.or.nclear<1)return
 if(.not.ieee_is_finite(nma).or..not.ieee_is_finite(nmc).or.nma<0.or.nmc<=0.or.nma>nmc)return
 if(.not.all(ieee_is_finite(speed)).or.any(speed<0).or.any(speed(2:nf)<=speed(1:nf-1)))return
 if(.not.all(ieee_is_finite(probe_angles)).or..not.all(ieee_is_finite(radial_clearance)).or.any(radial_clearance<=0))return
 if(any(probe_nodes<1).or.any(probe_nodes>nn).or.any(clear_nodes<1).or.any(clear_nodes>nn))return
 if(cap_enabled/=0.and.(.not.ieee_is_finite(cap).or.cap<=0))return
 if(maxout<nn)return

 allocate(fr(4*nn,nf),fi(4*nn,nf),qr(4*nn,nf),qi(4*nn,nf),vr(4*nn,nf),vi(4*nn,nf),ar(4*nn,nf),ai(4*nn,nf),res(nf),cond(nf))
 allocate(ratio(num_modes/2),major(nn),kappa(nn),angle(nn),proj(nn),sgn(nn),dummy_load(nn),dummy_nodes(nn))

 if(explicit_ub/=0)then
   if(nub_in<1.or.nub_in>nn)return
   if(any(ub_nodes_in(1:nub_in)<1).or.any(ub_nodes_in(1:nub_in)>nn))return
   if(.not.all(ieee_is_finite(ub_mag_in(1:nub_in))).or.any(ub_mag_in(1:nub_in)<0).or. &
      .not.all(ieee_is_finite(ub_phase_in(1:nub_in))))return
   nout=nub_in;ub_nodes(1:nout)=ub_nodes_in(1:nout);ub_mag(1:nout)=ub_mag_in(1:nout);ub_phase(1:nout)=ub_phase_in(1:nout)
 else
   call api617_full(nn,z,ns,sh,nd,di,nb,be_nmc,nmc,mode,num_modes,maxout,nout,ub_nodes,ub_mag,ub_phase,dummy_load, &
                    mode_index,mode_frequency,ratio,major,kappa,angle,proj,sgn,status)
   if(status/=RD_OK)return
 endif

 fr=0._rk;fi=0._rk
 do k=1,nout
   do i=1,nf
     dof=4*ub_nodes(k)-3
     c=cos(ub_phase(k));s=sin(ub_phase(k))
     fr(dof,i)=fr(dof,i)+ub_mag(k)*speed(i)**2*c
     fi(dof,i)=fi(dof,i)+ub_mag(k)*speed(i)**2*s
     fr(dof+1,i)=fr(dof+1,i)+ub_mag(k)*speed(i)**2*s
     fi(dof+1,i)=fi(dof+1,i)-ub_mag(k)*speed(i)**2*c
   enddo
 enddo

 call forced_response(nn,z,ns,sh,nd,di,nb,bnodes,nf,speed,0_ik,0._rk,coeff,4*nn,nf,fr,fi, &
                      qr,qi,vr,vi,ar,ai,res,cond,status)
 if(status/=RD_OK)return

 probe_response=0._rk
 do j=1,nprobe
   dof=4*probe_nodes(j)-3
   do i=1,nf
     p=cmplx(qr(dof,i),qi(dof,i),rk)*cos(probe_angles(j))+cmplx(qr(dof+1,i),qi(dof+1,i),rk)*sin(probe_angles(j))
     probe_response(j,i)=2._rk*abs(p)
   enddo
 enddo

 max_probe_amplitude=0._rk
 do i=1,nf
   if(speed(i)>=nma.and.speed(i)<=nmc)max_probe_amplitude=max(max_probe_amplitude,maxval(probe_response(:,i)))
 enddo
 if(.not.ieee_is_finite(max_probe_amplitude).or.max_probe_amplitude<=0)then;status=RD_ERR_UNSUPPORTED;return;endif

 rpm=nmc*60._rk/(2._rk*acos(-1._rk))
 vibration_limit=min(25.4_rk,25.4_rk*sqrt(12000._rk/rpm))*1.e-6_rk
 scale_factor=vibration_limit/max_probe_amplitude
 if(cap_enabled/=0)scale_factor=min(scale_factor,cap)

 do j=1,nclear
   diametral_clearance(j)=2._rk*radial_clearance(j)
   dof=4*clear_nodes(j)-3
   do i=1,nf
     x=cmplx(qr(dof,i),qi(dof,i),rk);y=cmplx(qr(dof+1,i),qi(dof+1,i),rk)
     clearance_response(j,i)=2._rk*scale_factor*major_axis(x,y)
   enddo
   imax=maxloc(clearance_response(j,:),dim=1)
   max_clearance_response(j)=clearance_response(j,imax)
   speed_at_max(j)=speed(imax)
   passed(j)=merge(1_ik,0_ik,max_clearance_response(j)<.75_rk*diametral_clearance(j))
 enddo

 if(.not.all(ieee_is_finite(probe_response)).or..not.all(ieee_is_finite(clearance_response)).or. &
    .not.ieee_is_finite(vibration_limit).or..not.ieee_is_finite(scale_factor))then
   status=RD_ERR_INPUT;return
 endif
 status=RD_OK
 end subroutine
end module rd_clearance
