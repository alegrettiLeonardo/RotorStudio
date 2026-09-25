module rb_tilting_pad_physics
  use rb_kinds, only: rk, ik
  use rb_status, only: RB_OK, RB_ERR_INPUT, RB_ERR_CONVERGENCE
  use rb_reynolds_element, only: rb_reynolds_q4_element
  use rb_reynolds_banded, only: rb_assemble_q4_banded, rb_include_pressure_bc, &
                                rb_lu_factor_band, rb_lu_solve_band_cavitating
  use rb_dynamic_reduction, only: rb_dynamic_reduce_tilts
  implicit none(type, external)
  private

  public :: rb_tilting_pad_isoviscous

contains

  subroutine rb_tilting_pad_isoviscous(speed, excitation_frequency, weight, fxs_load, fys_load, &
                                        journal_diameter, radial_clearance, viscosity, pad_thickness, pad_density, &
                                        n_pads, pivot_angle, pad_arc, pad_axial_length, preload, offset, k_rotate, &
                                        total_e_x, total_e_z, xj_ratio_initial, yj_ratio_initial, relax_p, &
                                        max_iterations, force_tolerance, xj_ratio, yj_ratio, tilt_angle, &
                                        k_reduced, c_reduced, fx_hydro, fy_hydro, p_max, iterations, status)
    real(rk), intent(in) :: speed, excitation_frequency, weight, fxs_load, fys_load
    real(rk), intent(in) :: journal_diameter, radial_clearance, viscosity, pad_thickness, pad_density
    integer(ik), intent(in) :: n_pads, total_e_x, total_e_z, max_iterations
    real(rk), intent(in) :: pivot_angle(n_pads), pad_arc(n_pads), pad_axial_length(n_pads)
    real(rk), intent(in) :: preload(n_pads), offset(n_pads), k_rotate(n_pads)
    real(rk), intent(in) :: xj_ratio_initial, yj_ratio_initial, relax_p, force_tolerance
    real(rk), intent(out) :: xj_ratio, yj_ratio, tilt_angle(n_pads)
    real(rk), intent(out) :: k_reduced(2,2), c_reduced(2,2), fx_hydro, fy_hydro, p_max
    integer(ik), intent(out) :: iterations, status

    integer :: nn, it, p
    integer(ik) :: st
    real(rk), allocatable :: p_static(:,:), moments(:)
    real(rk), allocatable :: tilt_p(:), tilt_m(:)
    real(rk) :: xj, yj, fx_ext, fy_ext, fx_net, fy_net, load_scale
    real(rk) :: eps, eps_t, fxp, fyp, fxm, fym, ptmp, dx, dy, det, normd, denom
    real(rk) :: k_eff(2,2), k_j(2,2), c_j(2,2)
    real(rk), allocatable :: kdx(:), kdy(:), kxd(:), kyd(:), kdd(:)
    real(rk), allocatable :: cdx(:), cdy(:), cxd(:), cyd(:), cdd(:)
    real(rk), allocatable :: plen(:), ip(:)
    real(rk) :: mp, mm, fpx, fpy, fmx, fmy

    status=RB_OK
    xj_ratio=0._rk; yj_ratio=0._rk; tilt_angle=0._rk
    k_reduced=0._rk; c_reduced=0._rk
    fx_hydro=0._rk; fy_hydro=0._rk; p_max=0._rk; iterations=0_ik

    if (speed<=0._rk .or. excitation_frequency<=0._rk .or. journal_diameter<=0._rk .or. &
        radial_clearance<=0._rk .or. viscosity<=0._rk .or. pad_thickness<=0._rk .or. &
        pad_density<0._rk .or. n_pads<1 .or. total_e_x<2 .or. total_e_z<2 .or. &
        mod(total_e_x,2_ik)/=0 .or. mod(total_e_z,2_ik)/=0 .or. max_iterations<1 .or. &
        relax_p<=0._rk .or. relax_p>1._rk .or. force_tolerance<=0._rk) then
      status=RB_ERR_INPUT
      return
    end if
    if (any(pad_arc<=0._rk) .or. any(pad_axial_length<=0._rk) .or. &
        any(preload<0._rk) .or. any(preload>=1._rk) .or. any(offset<=0._rk) .or. any(offset>=1._rk)) then
      status=RB_ERR_INPUT
      return
    end if

    nn=(int(total_e_x)+1)*(int(total_e_z)+1)
    allocate(p_static(nn,n_pads),moments(n_pads),tilt_p(n_pads),tilt_m(n_pads))
    allocate(kdx(n_pads),kdy(n_pads),kxd(n_pads),kyd(n_pads),kdd(n_pads))
    allocate(cdx(n_pads),cdy(n_pads),cxd(n_pads),cyd(n_pads),cdd(n_pads))
    allocate(plen(n_pads),ip(n_pads))
    plen=0.5_rk*journal_diameter*pad_arc

    xj=xj_ratio_initial*radial_clearance
    yj=yj_ratio_initial*radial_clearance
    fx_ext=fxs_load
    fy_ext=fys_load-weight
    load_scale=max(1._rk,sqrt(fx_ext*fx_ext+fy_ext*fy_ext))
    eps=max(radial_clearance*1e-5_rk,1e-10_rk)

    do it=1,int(max_iterations)
      call tp_equilibrate_pads(speed,journal_diameter,radial_clearance,viscosity,pad_thickness,n_pads, &
                               pivot_angle,pad_arc,pad_axial_length,preload,offset,k_rotate,total_e_x,total_e_z, &
                               xj,yj,tilt_angle,p_static,moments,fx_hydro,fy_hydro,p_max,st)
      if(st/=RB_OK)then;status=st;return;end if

      fx_net=fx_hydro+fx_ext
      fy_net=fy_hydro+fy_ext
      iterations=int(it,ik)
      if(sqrt(fx_net*fx_net+fy_net*fy_net)<=force_tolerance*load_scale .and. it>1)exit

      call tp_equilibrated_force(speed,journal_diameter,radial_clearance,viscosity,pad_thickness,n_pads, &
                                 pivot_angle,pad_arc,pad_axial_length,preload,offset,k_rotate,total_e_x,total_e_z, &
                                 xj+eps,yj,tilt_p,fxp,fyp,ptmp,st)
      if(st/=RB_OK)then;status=st;return;end if
      call tp_equilibrated_force(speed,journal_diameter,radial_clearance,viscosity,pad_thickness,n_pads, &
                                 pivot_angle,pad_arc,pad_axial_length,preload,offset,k_rotate,total_e_x,total_e_z, &
                                 xj-eps,yj,tilt_m,fxm,fym,ptmp,st)
      if(st/=RB_OK)then;status=st;return;end if
      k_eff(1,1)=-(fxp-fxm)/(2._rk*eps)
      k_eff(2,1)=-(fyp-fym)/(2._rk*eps)

      call tp_equilibrated_force(speed,journal_diameter,radial_clearance,viscosity,pad_thickness,n_pads, &
                                 pivot_angle,pad_arc,pad_axial_length,preload,offset,k_rotate,total_e_x,total_e_z, &
                                 xj,yj+eps,tilt_p,fxp,fyp,ptmp,st)
      if(st/=RB_OK)then;status=st;return;end if
      call tp_equilibrated_force(speed,journal_diameter,radial_clearance,viscosity,pad_thickness,n_pads, &
                                 pivot_angle,pad_arc,pad_axial_length,preload,offset,k_rotate,total_e_x,total_e_z, &
                                 xj,yj-eps,tilt_m,fxm,fym,ptmp,st)
      if(st/=RB_OK)then;status=st;return;end if
      k_eff(1,2)=-(fxp-fxm)/(2._rk*eps)
      k_eff(2,2)=-(fyp-fym)/(2._rk*eps)

      det=k_eff(1,1)*k_eff(2,2)-k_eff(1,2)*k_eff(2,1)
      if(abs(det)<=1e-12_rk*max(1._rk,abs(k_eff(1,1)*k_eff(2,2)),abs(k_eff(1,2)*k_eff(2,1))))then
        status=RB_ERR_CONVERGENCE;return
      end if
      dx=(k_eff(2,2)*fx_net-k_eff(1,2)*fy_net)/det
      dy=(-k_eff(2,1)*fx_net+k_eff(1,1)*fy_net)/det
      normd=sqrt(dx*dx+dy*dy)
      if(normd>0.2_rk*radial_clearance)then
        dx=dx*0.2_rk*radial_clearance/normd
        denom=sqrt(dx*dx+dy*dy)
        if(denom>tiny(1._rk))dy=dy*0.2_rk*radial_clearance/denom
      end if
      xj=xj+relax_p*dx
      yj=yj+relax_p*dy
      if(sqrt(xj*xj+yj*yj)>=0.995_rk*radial_clearance)then
        denom=sqrt(xj*xj+yj*yj)
        xj=xj*0.995_rk*radial_clearance/denom
        yj=yj*0.995_rk*radial_clearance/denom
      end if
    end do

    if(sqrt(fx_net*fx_net+fy_net*fy_net)>force_tolerance*load_scale)then
      status=RB_ERR_CONVERGENCE;return
    end if

    call tp_equilibrate_pads(speed,journal_diameter,radial_clearance,viscosity,pad_thickness,n_pads, &
                             pivot_angle,pad_arc,pad_axial_length,preload,offset,k_rotate,total_e_x,total_e_z, &
                             xj,yj,tilt_angle,p_static,moments,fx_hydro,fy_hydro,p_max,st)
    if(st/=RB_OK)then;status=st;return;end if

    ! Uncondensed stiffness blocks: finite-difference the fully solved static
    ! Reynolds force/moment while holding each final pad tilt fixed.
    call tp_fixedtilt_state(speed,journal_diameter,radial_clearance,viscosity,pad_thickness,n_pads,pivot_angle, &
                            pad_arc,pad_axial_length,preload,offset,k_rotate,total_e_x,total_e_z,xj+eps,yj,tilt_angle, &
                            fxp,fyp,moments,p_static,ptmp,st)
    if(st/=RB_OK)then;status=st;return;end if
    tilt_p=moments
    call tp_fixedtilt_state(speed,journal_diameter,radial_clearance,viscosity,pad_thickness,n_pads,pivot_angle, &
                            pad_arc,pad_axial_length,preload,offset,k_rotate,total_e_x,total_e_z,xj-eps,yj,tilt_angle, &
                            fxm,fym,moments,p_static,ptmp,st)
    if(st/=RB_OK)then;status=st;return;end if
    tilt_m=moments
    k_j(1,1)=-(fxp-fxm)/(2._rk*eps); k_j(2,1)=-(fyp-fym)/(2._rk*eps)
    kdx=-(tilt_p-tilt_m)/(2._rk*eps)

    call tp_fixedtilt_state(speed,journal_diameter,radial_clearance,viscosity,pad_thickness,n_pads,pivot_angle, &
                            pad_arc,pad_axial_length,preload,offset,k_rotate,total_e_x,total_e_z,xj,yj+eps,tilt_angle, &
                            fxp,fyp,moments,p_static,ptmp,st)
    if(st/=RB_OK)then;status=st;return;end if
    tilt_p=moments
    call tp_fixedtilt_state(speed,journal_diameter,radial_clearance,viscosity,pad_thickness,n_pads,pivot_angle, &
                            pad_arc,pad_axial_length,preload,offset,k_rotate,total_e_x,total_e_z,xj,yj-eps,tilt_angle, &
                            fxm,fym,moments,p_static,ptmp,st)
    if(st/=RB_OK)then;status=st;return;end if
    tilt_m=moments
    k_j(1,2)=-(fxp-fxm)/(2._rk*eps); k_j(2,2)=-(fyp-fym)/(2._rk*eps)
    kdy=-(tilt_p-tilt_m)/(2._rk*eps)

    do p=1,int(n_pads)
      eps_t=max(1e-8_rk,abs(tilt_angle(p))*1e-4_rk)
      tilt_p=tilt_angle; tilt_m=tilt_angle
      tilt_p(p)=tilt_p(p)+eps_t; tilt_m(p)=tilt_m(p)-eps_t
      call tp_single_pad_static(speed,journal_diameter,radial_clearance,viscosity,pad_thickness,pivot_angle(p), &
                                pad_arc(p),pad_axial_length(p),preload(p),offset(p),k_rotate(p),total_e_x,total_e_z, &
                                xj,yj,tilt_p(p),p_static(:,p),fpx,fpy,mp,ptmp,st)
      if(st/=RB_OK)then;status=st;return;end if
      call tp_single_pad_static(speed,journal_diameter,radial_clearance,viscosity,pad_thickness,pivot_angle(p), &
                                pad_arc(p),pad_axial_length(p),preload(p),offset(p),k_rotate(p),total_e_x,total_e_z, &
                                xj,yj,tilt_m(p),p_static(:,p),fmx,fmy,mm,ptmp,st)
      if(st/=RB_OK)then;status=st;return;end if
      kxd(p)=-(fpx-fmx)/(2._rk*eps_t)
      kyd(p)=-(fpy-fmy)/(2._rk*eps_t)
      kdd(p)=-(mp-mm)/(2._rk*eps_t)-k_rotate(p)
      ! k_rotate is supplied separately to the dynamic reducer.
    end do

    ! Damping blocks from the three velocity-perturbation Reynolds equations.
    c_j=0._rk; cdx=0._rk; cdy=0._rk; cxd=0._rk; cyd=0._rk; cdd=0._rk
    do p=1,int(n_pads)
      call tp_single_pad_pert(1_ik,journal_diameter,radial_clearance,viscosity,pad_thickness,pivot_angle(p), &
                              pad_arc(p),pad_axial_length(p),preload(p),offset(p),total_e_x,total_e_z,xj,yj, &
                              tilt_angle(p),p_static(:,p),fpx,fpy,mp,st)
      if(st/=RB_OK)then;status=st;return;end if
      c_j(1,1)=c_j(1,1)+fpx; c_j(2,1)=c_j(2,1)+fpy; cdx(p)=mp
      call tp_single_pad_pert(2_ik,journal_diameter,radial_clearance,viscosity,pad_thickness,pivot_angle(p), &
                              pad_arc(p),pad_axial_length(p),preload(p),offset(p),total_e_x,total_e_z,xj,yj, &
                              tilt_angle(p),p_static(:,p),fpx,fpy,mp,st)
      if(st/=RB_OK)then;status=st;return;end if
      c_j(1,2)=c_j(1,2)+fpx; c_j(2,2)=c_j(2,2)+fpy; cdy(p)=mp
      call tp_single_pad_pert(3_ik,journal_diameter,radial_clearance,viscosity,pad_thickness,pivot_angle(p), &
                              pad_arc(p),pad_axial_length(p),preload(p),offset(p),total_e_x,total_e_z,xj,yj, &
                              tilt_angle(p),p_static(:,p),fpx,fpy,mp,st)
      if(st/=RB_OK)then;status=st;return;end if
      cxd(p)=fpx; cyd(p)=fpy; cdd(p)=mp
    end do

    call rb_dynamic_reduce_tilts(n_pads,k_j,c_j,kdx,kdy,kxd,kyd,kdd,cdx,cdy,cxd,cyd,cdd, &
                                 plen,pad_thickness,pad_axial_length,pad_density,excitation_frequency,k_rotate, &
                                 k_reduced,c_reduced,ip,st)
    if(st/=RB_OK)then;status=st;return;end if

    xj_ratio=xj/radial_clearance
    yj_ratio=yj/radial_clearance
  end subroutine rb_tilting_pad_isoviscous


  subroutine tp_equilibrated_force(speed,d,cb,mu,tp,np,piv,arc,alen,pre,off,krot,nx,nz,xj,yj,tilt,fx,fy,pmax,status)
    real(rk),intent(in)::speed,d,cb,mu,tp,piv(np),arc(np),alen(np),pre(np),off(np),krot(np),xj,yj
    integer(ik),intent(in)::np,nx,nz
    real(rk),intent(out)::tilt(np),fx,fy,pmax
    integer(ik),intent(out)::status
    integer::nn
    real(rk),allocatable::press(:,:),mom(:)
    nn=(int(nx)+1)*(int(nz)+1);allocate(press(nn,np),mom(np))
    call tp_equilibrate_pads(speed,d,cb,mu,tp,np,piv,arc,alen,pre,off,krot,nx,nz,xj,yj,tilt,press,mom,fx,fy,pmax,status)
  end subroutine tp_equilibrated_force


  subroutine tp_equilibrate_pads(speed,d,cb,mu,tp,np,piv,arc,alen,pre,off,krot,nx,nz,xj,yj,tilt,press,mom,fx,fy,pmax,status)
    real(rk),intent(in)::speed,d,cb,mu,tp,piv(np),arc(np),alen(np),pre(np),off(np),krot(np),xj,yj
    integer(ik),intent(in)::np,nx,nz
    real(rk),intent(out)::tilt(np),press(:,:),mom(np),fx,fy,pmax
    integer(ik),intent(out)::status
    integer::p,iter,nn
    real(rk)::r,cp,lead,xp,rtilt,lo,hi,t,fp,fy_i,m,pmi,sden,hmin
    integer(ik)::st

    status=RB_OK;fx=0._rk;fy=0._rk;pmax=0._rk
    nn=(int(nx)+1)*(int(nz)+1)
    do p=1,int(np)
      r=0.5_rk*d;cp=cb/(1._rk-pre(p));lead=piv(p)-arc(p)*off(p);xp=off(p)*arc(p)
      rtilt=r+cb+tp
      sden=sin(arc(p)-xp)
      if(abs(sden)<=1e-12_rk .or. abs(sin(-xp))<=1e-12_rk)then;status=RB_ERR_INPUT;return;end if
      hi=(cb-xj*cos(lead+arc(p))-yj*sin(lead+arc(p)))/(rtilt*sden)
      lo=(cb-xj*cos(lead)-yj*sin(lead))/(rtilt*sin(-xp))
      if(lo>hi)then;t=lo;lo=hi;hi=t;end if

      do iter=1,100
        if(abs(hi-lo)<1e-8_rk)then
          t=lo
        else
          t=0.5_rk*(lo+hi)
        end if
        call tp_single_pad_static(speed,d,cb,mu,tp,piv(p),arc(p),alen(p),pre(p),off(p),krot(p),nx,nz, &
                                  xj,yj,t,press(1:nn,p),fp,fy_i,m,pmi,st,hmin)
        if(st/=RB_OK .or. hmin<0._rk)then
          if(t>0._rk)then;hi=t;else;lo=t;end if
          cycle
        end if
        if(abs(hi-lo)<1e-8_rk)exit
        if(m>=0._rk)then;lo=t;else;hi=t;end if
      end do
      tilt(p)=t;mom(p)=m;fx=fx+fp;fy=fy+fy_i;pmax=max(pmax,pmi)
    end do
  end subroutine tp_equilibrate_pads


  subroutine tp_fixedtilt_state(speed,d,cb,mu,tp,np,piv,arc,alen,pre,off,krot,nx,nz,xj,yj,tilt,fx,fy,mom,press,pmax,status)
    real(rk),intent(in)::speed,d,cb,mu,tp,piv(np),arc(np),alen(np),pre(np),off(np),krot(np),xj,yj,tilt(np)
    integer(ik),intent(in)::np,nx,nz
    real(rk),intent(out)::fx,fy,mom(np),press(:,:),pmax
    integer(ik),intent(out)::status
    integer::p,nn
    real(rk)::fi,gi,mi,pm,hmin
    integer(ik)::st
    status=RB_OK;fx=0._rk;fy=0._rk;pmax=0._rk;nn=(int(nx)+1)*(int(nz)+1)
    do p=1,int(np)
      call tp_single_pad_static(speed,d,cb,mu,tp,piv(p),arc(p),alen(p),pre(p),off(p),krot(p),nx,nz,xj,yj, &
                                tilt(p),press(1:nn,p),fi,gi,mi,pm,st,hmin)
      if(st/=RB_OK)then;status=st;return;end if
      fx=fx+fi;fy=fy+gi;mom(p)=mi;pmax=max(pmax,pm)
    end do
  end subroutine tp_fixedtilt_state


  subroutine tp_single_pad_static(speed,d,cb,mu,tp,piv,arc,alen,pre,off,krot,nx,nz,xj,yj,tilt,pressure,fx,fy,moment,pmax,status,hmin_out)
    real(rk),intent(in)::speed,d,cb,mu,tp,piv,arc,alen,pre,off,krot,xj,yj,tilt
    integer(ik),intent(in)::nx,nz
    real(rk),intent(out)::pressure(:),fx,fy,moment,pmax
    integer(ik),intent(out)::status
    real(rk),intent(out),optional::hmin_out
    integer::nn,ix,iz,node,e,n1,n2,n3,n4,bw,ncol,nbc
    real(rk)::r,cp,lead,xp,dx,dz,theta,hv,he,dhdx,gamma,kcoef,q,u,area,ang,pavg,hmin
    real(rk),allocatable::h(:),a(:,:),rhs(:),alow(:,:),pres(:)
    real(rk)::em(4,4),ec(4)
    integer(ik),allocatable::ipiv(:),bcidx(:),nodes0(:)
    integer(ik)::st

    status=RB_OK;fx=0._rk;fy=0._rk;moment=0._rk;pmax=0._rk
    nn=(int(nx)+1)*(int(nz)+1)
    if(size(pressure)<nn)then;status=RB_ERR_INPUT;return;end if
    r=0.5_rk*d;cp=cb/(1._rk-pre);lead=piv-arc*off;xp=off*arc
    dx=r*arc/real(nx,rk);dz=alen/real(nz,rk);bw=int(nz)+3;ncol=2*bw-1
    allocate(h(nn),a(nn,ncol),rhs(nn),alow(nn,bw-1),ipiv(nn),bcidx(nn),pres(nn),nodes0(4))
    a=0._rk;rhs=0._rk;pressure=0._rk;pres=0._rk
    hmin=huge(1._rk)
    do ix=0,int(nx)
      theta=arc*real(ix,rk)/real(nx,rk)
      do iz=0,int(nz)
        node=ix*(int(nz)+1)+iz+1
        hv=cp-xj*cos(lead+theta)-yj*sin(lead+theta)-pre*cp*cos(theta-xp) &
           -(r+cb+tp)*tilt*sin(theta-xp)
        h(node)=hv;hmin=min(hmin,hv)
      end do
    end do
    if(present(hmin_out))hmin_out=hmin
    if(hmin<=0._rk)then;status=RB_ERR_CONVERGENCE;return;end if
    gamma=-1._rk/(12._rk*mu);u=speed*r
    do ix=0,int(nx)-1
      do iz=0,int(nz)-1
        n1=ix*(int(nz)+1)+iz+1;n2=(ix+1)*(int(nz)+1)+iz+1;n3=n2+1;n4=n1+1
        he=.25_rk*(h(n1)+h(n2)+h(n3)+h(n4));kcoef=he**3*gamma
        dhdx=(-h(n1)+h(n2)+h(n3)-h(n4))/(2._rk*dx);q=.5_rk*u*dhdx
        call rb_reynolds_q4_element(kcoef,kcoef,q,dx,dz,em,ec,st)
        if(st/=RB_OK)then;status=st;return;end if
        nodes0=[int(n1-1,ik),int(n2-1,ik),int(n3-1,ik),int(n4-1,ik)]
        call rb_assemble_q4_banded(em,ec,nodes0,int(bw,ik),a,rhs,st)
        if(st/=RB_OK)then;status=st;return;end if
      end do
    end do
    nbc=0
    do ix=0,int(nx)
      do iz=0,int(nz)
        node=ix*(int(nz)+1)+iz+1
        if(iz==0 .or. iz==int(nz) .or. ix==0 .or. ix==int(nx))then
          nbc=nbc+1;bcidx(nbc)=int(node-1,ik);pres(nbc)=0._rk
        end if
      end do
    end do
    call rb_include_pressure_bc(a,rhs,int(bw,ik),int(nbc,ik),bcidx,pres,int(nn,ik),st)
    if(st/=RB_OK)then;status=st;return;end if
    call rb_lu_factor_band(a,int(nn,ik),int(bw,ik),alow,ipiv,st)
    if(st/=RB_OK)then;status=st;return;end if
    call rb_lu_solve_band_cavitating(a,int(nn,ik),int(bw,ik),alow,ipiv,rhs,0._rk,st)
    if(st/=RB_OK)then;status=st;return;end if
    pressure(1:nn)=rhs(1:nn);pmax=maxval(rhs(1:nn))
    do ix=0,int(nx)-1
      do iz=0,int(nz)-1
        n1=ix*(int(nz)+1)+iz+1;n2=(ix+1)*(int(nz)+1)+iz+1;n3=n2+1;n4=n1+1
        area=dx*dz;theta=arc*(real(ix,rk)+.5_rk)/real(nx,rk);ang=lead+theta
        pavg=.25_rk*(pressure(n1)+pressure(n2)+pressure(n3)+pressure(n4))
        fx=fx-area*pavg*cos(ang);fy=fy-area*pavg*sin(ang)
        moment=moment-(r+tp)*area*pavg*sin(theta-xp)
      end do
    end do
    moment=moment-krot*tilt
  end subroutine tp_single_pad_static


  subroutine tp_single_pad_pert(mode,d,cb,mu,tp,piv,arc,alen,pre,off,nx,nz,xj,yj,tilt,p_static,fx,fy,moment,status)
    integer(ik),intent(in)::mode,nx,nz
    real(rk),intent(in)::d,cb,mu,tp,piv,arc,alen,pre,off,xj,yj,tilt,p_static(:)
    real(rk),intent(out)::fx,fy,moment
    integer(ik),intent(out)::status
    integer::nn,ix,iz,node,n1,n2,n3,n4,bw,ncol,nbc
    real(rk)::r,cp,lead,xp,dx,dz,theta,hv,he,gamma,kcoef,q,area,ang,pavg
    real(rk),allocatable::h(:),a(:,:),rhs(:),alow(:,:),pres(:)
    real(rk)::em(4,4),ec(4)
    integer(ik),allocatable::ipiv(:),bcidx(:),nodes0(:)
    integer(ik)::st

    status=RB_OK;fx=0._rk;fy=0._rk;moment=0._rk
    nn=(int(nx)+1)*(int(nz)+1);r=.5_rk*d;cp=cb/(1._rk-pre);lead=piv-arc*off;xp=off*arc
    dx=r*arc/real(nx,rk);dz=alen/real(nz,rk);bw=int(nz)+3;ncol=2*bw-1
    allocate(h(nn),a(nn,ncol),rhs(nn),alow(nn,bw-1),ipiv(nn),bcidx(nn),pres(nn),nodes0(4))
    a=0._rk;rhs=0._rk;pres=0._rk
    do ix=0,int(nx)
      theta=arc*real(ix,rk)/real(nx,rk)
      do iz=0,int(nz)
        node=ix*(int(nz)+1)+iz+1
        hv=cp-xj*cos(lead+theta)-yj*sin(lead+theta)-pre*cp*cos(theta-xp) &
           -(r+cb+tp)*tilt*sin(theta-xp)
        if(hv<=0._rk)then;status=RB_ERR_CONVERGENCE;return;end if
        h(node)=hv
      end do
    end do
    gamma=-1._rk/(12._rk*mu)
    do ix=0,int(nx)-1
      do iz=0,int(nz)-1
        n1=ix*(int(nz)+1)+iz+1;n2=(ix+1)*(int(nz)+1)+iz+1;n3=n2+1;n4=n1+1
        he=.25_rk*(h(n1)+h(n2)+h(n3)+h(n4));kcoef=he**3*gamma
        theta=arc*(real(ix,rk)+.5_rk)/real(nx,rk);ang=lead+theta
        select case(mode)
        case(1);q=-cos(ang)
        case(2);q=-sin(ang)
        case(3);q=-(r+tp)*sin(theta-xp)
        case default;status=RB_ERR_INPUT;return
        end select
        call rb_reynolds_q4_element(kcoef,kcoef,q,dx,dz,em,ec,st)
        if(st/=RB_OK)then;status=st;return;end if
        nodes0=[int(n1-1,ik),int(n2-1,ik),int(n3-1,ik),int(n4-1,ik)]
        call rb_assemble_q4_banded(em,ec,nodes0,int(bw,ik),a,rhs,st)
        if(st/=RB_OK)then;status=st;return;end if
      end do
    end do
    nbc=0
    do ix=0,int(nx)
      do iz=0,int(nz)
        node=ix*(int(nz)+1)+iz+1
        if(iz==0 .or. iz==int(nz) .or. ix==0 .or. ix==int(nx) .or. abs(p_static(node))<1e-6_rk)then
          nbc=nbc+1;bcidx(nbc)=int(node-1,ik);pres(nbc)=0._rk
        end if
      end do
    end do
    call rb_include_pressure_bc(a,rhs,int(bw,ik),int(nbc,ik),bcidx,pres,int(nn,ik),st)
    if(st/=RB_OK)then;status=st;return;end if
    call rb_lu_factor_band(a,int(nn,ik),int(bw,ik),alow,ipiv,st)
    if(st/=RB_OK)then;status=st;return;end if
    call tp_lu_solve_signed(a,int(nn,ik),int(bw,ik),alow,ipiv,rhs,st)
    if(st/=RB_OK)then;status=st;return;end if
    do ix=0,int(nx)-1
      do iz=0,int(nz)-1
        n1=ix*(int(nz)+1)+iz+1;n2=(ix+1)*(int(nz)+1)+iz+1;n3=n2+1;n4=n1+1
        area=dx*dz;theta=arc*(real(ix,rk)+.5_rk)/real(nx,rk);ang=lead+theta
        pavg=.25_rk*(rhs(n1)+rhs(n2)+rhs(n3)+rhs(n4))
        fx=fx+area*pavg*cos(ang);fy=fy+area*pavg*sin(ang)
        moment=moment+(r+tp)*area*pavg*sin(theta-xp)
      end do
    end do
  end subroutine tp_single_pad_pert


  subroutine tp_lu_solve_signed(a,total_n,bandwidth,a_lower,index1,b,status)
    real(rk),intent(in)::a(:,:),a_lower(:,:)
    integer(ik),intent(in)::total_n,bandwidth,index1(:)
    real(rk),intent(inout)::b(:)
    integer(ik),intent(out)::status
    integer::total_column,ll,k,i,ip
    real(rk)::tmp,dum
    status=RB_OK;total_column=2*int(bandwidth)-1
    ll=int(bandwidth)-1
    do k=1,int(total_n)
      ip=int(index1(k));if(ip<1 .or. ip>total_n)then;status=RB_ERR_INPUT;return;end if
      if(ip/=k)then;tmp=b(k);b(k)=b(ip);b(ip)=tmp;end if
      if(ll<total_n)ll=ll+1
      do i=k+1,ll;b(i)=b(i)-a_lower(k,i-k)*b(k);end do
    end do
    ll=1
    do i=int(total_n),1,-1
      dum=b(i)
      do k=2,ll;dum=dum-a(i,k)*b(k+i-1);end do
      if(abs(a(i,1))<=tiny(1._rk))then;status=RB_ERR_INPUT;return;end if
      b(i)=dum/a(i,1);if(ll<total_column)ll=ll+1
    end do
  end subroutine tp_lu_solve_signed

end module rb_tilting_pad_physics
