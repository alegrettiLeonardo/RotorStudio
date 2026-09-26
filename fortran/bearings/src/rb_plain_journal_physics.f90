module rb_plain_journal_physics
  use rb_kinds, only: rk, ik
  use rb_status, only: RB_OK, RB_ERR_INPUT, RB_ERR_CONVERGENCE
  use rb_reynolds_element, only: rb_reynolds_q4_element
  use rb_reynolds_banded, only: rb_assemble_q4_banded, rb_include_pressure_bc, &
                                rb_lu_factor_band, rb_lu_solve_band_cavitating
  implicit none(type, external)
  private

  public :: rb_plain_journal_isoviscous

contains

  subroutine rb_plain_journal_isoviscous(speed, weight, fxs_load, fys_load, journal_diameter, radial_clearance, &
                                         viscosity, n_pads, pivot_angle, pad_arc, pad_axial_length, preload, offset, &
                                         total_e_x, total_e_z, xj_ratio_initial, yj_ratio_initial, relax_p, &
                                         max_iterations, force_tolerance, xj_ratio, yj_ratio, k_out, c_out, &
                                         fx_hydro, fy_hydro, p_max, iterations, status)
    real(rk), intent(in) :: speed, weight, fxs_load, fys_load, journal_diameter, radial_clearance, viscosity
    integer(ik), intent(in) :: n_pads, total_e_x, total_e_z, max_iterations
    real(rk), intent(in) :: pivot_angle(n_pads), pad_arc(n_pads), pad_axial_length(n_pads)
    real(rk), intent(in) :: preload(n_pads), offset(n_pads)
    real(rk), intent(in) :: xj_ratio_initial, yj_ratio_initial, relax_p, force_tolerance
    real(rk), intent(out) :: xj_ratio, yj_ratio, k_out(2,2), c_out(2,2), fx_hydro, fy_hydro, p_max
    integer(ik), intent(out) :: iterations, status

    real(rk), allocatable :: p_static(:,:)
    real(rk) :: xj, yj, fx_ext, fy_ext, fx_net, fy_net, load_scale
    real(rk) :: eps, fxp, fyp, fxm, fym, dummy_pmax
    real(rk) :: dx, dy, det, normd, denom
    real(rk) :: kxx, kxy, kyx, kyy
    integer :: it
    integer(ik) :: st
    integer :: nn

    status = RB_OK
    xj_ratio = 0._rk; yj_ratio = 0._rk
    k_out = 0._rk; c_out = 0._rk
    fx_hydro = 0._rk; fy_hydro = 0._rk; p_max = 0._rk
    iterations = 0_ik

    if (speed <= 0._rk .or. journal_diameter <= 0._rk .or. radial_clearance <= 0._rk .or. viscosity <= 0._rk .or. &
        n_pads < 1 .or. total_e_x < 2 .or. total_e_z < 2 .or. mod(total_e_x,2_ik) /= 0 .or. &
        mod(total_e_z,2_ik) /= 0 .or. max_iterations < 1 .or. relax_p <= 0._rk .or. relax_p > 1._rk .or. &
        force_tolerance <= 0._rk) then
      status = RB_ERR_INPUT
      return
    end if
    if (any(pad_arc <= 0._rk) .or. any(pad_axial_length <= 0._rk) .or. &
        any(preload < 0._rk) .or. any(preload >= 1._rk) .or. &
        any(offset < 0._rk) .or. any(offset > 1._rk)) then
      status = RB_ERR_INPUT
      return
    end if

    nn = (int(total_e_x)+1)*(int(total_e_z)+1)
    allocate(p_static(nn,n_pads))

    xj = xj_ratio_initial*radial_clearance
    yj = yj_ratio_initial*radial_clearance
    fx_ext = fxs_load
    fy_ext = fys_load - weight
    load_scale = max(1._rk, sqrt(fx_ext*fx_ext + fy_ext*fy_ext))

    eps = max(radial_clearance*1.0e-5_rk, 1.0e-10_rk)

    do it = 1, int(max_iterations)
      call rb_fixed_state(speed,journal_diameter,radial_clearance,viscosity,n_pads,pivot_angle,pad_arc, &
                          pad_axial_length,preload,offset,total_e_x,total_e_z,xj,yj,p_static, &
                          fx_hydro,fy_hydro,p_max,st)
      if (st /= RB_OK) then
        status = st
        return
      end if

      fx_net = fx_hydro + fx_ext
      fy_net = fy_hydro + fy_ext
      iterations = int(it,ik)
      if (sqrt(fx_net*fx_net + fy_net*fy_net) <= force_tolerance*load_scale) exit

      call rb_force_only(speed,journal_diameter,radial_clearance,viscosity,n_pads,pivot_angle,pad_arc, &
                         pad_axial_length,preload,offset,total_e_x,total_e_z,xj+eps,yj,fxp,fyp,dummy_pmax,st)
      if (st /= RB_OK) then; status=st; return; end if
      call rb_force_only(speed,journal_diameter,radial_clearance,viscosity,n_pads,pivot_angle,pad_arc, &
                         pad_axial_length,preload,offset,total_e_x,total_e_z,xj-eps,yj,fxm,fym,dummy_pmax,st)
      if (st /= RB_OK) then; status=st; return; end if
      kxx = -(fxp-fxm)/(2._rk*eps)
      kyx = -(fyp-fym)/(2._rk*eps)

      call rb_force_only(speed,journal_diameter,radial_clearance,viscosity,n_pads,pivot_angle,pad_arc, &
                         pad_axial_length,preload,offset,total_e_x,total_e_z,xj,yj+eps,fxp,fyp,dummy_pmax,st)
      if (st /= RB_OK) then; status=st; return; end if
      call rb_force_only(speed,journal_diameter,radial_clearance,viscosity,n_pads,pivot_angle,pad_arc, &
                         pad_axial_length,preload,offset,total_e_x,total_e_z,xj,yj-eps,fxm,fym,dummy_pmax,st)
      if (st /= RB_OK) then; status=st; return; end if
      kxy = -(fxp-fxm)/(2._rk*eps)
      kyy = -(fyp-fym)/(2._rk*eps)

      dx = 0._rk; dy = 0._rk
      if (abs(kyy) > 1e-6_rk .and. abs(kxx/kyy) < 1e-4_rk) then
        dy = fy_net/kyy
      else if (abs(kxx) > 1e-6_rk .and. abs(kyy/kxx) < 1e-4_rk) then
        dx = fx_net/kxx
      else if (abs(kxy) < 1e-6_rk .and. abs(kyx) < 1e-6_rk .and. abs(kxx) > 1e-6_rk .and. abs(kyy) > 1e-6_rk) then
        dx = fx_net/kxx
        dy = fy_net/kyy
      else
        det = kxx*kyy-kxy*kyx
        if (abs(det) <= 1e-12_rk*max(1._rk,abs(kxx*kyy),abs(kxy*kyx))) then
          status = RB_ERR_CONVERGENCE
          return
        end if
        dx = (kyy*fx_net-kxy*fy_net)/det
        dy = (-kyx*fx_net+kxx*fy_net)/det
      end if

      normd = sqrt(dx*dx+dy*dy)
      if (normd > 0.2_rk*radial_clearance) then
        dx = dx*0.2_rk*radial_clearance/normd
        denom = sqrt(dx*dx+dy*dy)
        if (denom > tiny(1._rk)) dy = dy*0.2_rk*radial_clearance/denom
      end if

      xj = xj + relax_p*dx
      yj = yj + relax_p*dy

      if (sqrt(xj*xj+yj*yj) >= 0.995_rk*radial_clearance) then
        denom = sqrt(xj*xj+yj*yj)
        xj = xj*(0.995_rk*radial_clearance/denom)
        yj = yj*(0.995_rk*radial_clearance/denom)
      end if
    end do

    if (sqrt(fx_net*fx_net + fy_net*fy_net) > force_tolerance*load_scale) then
      status = RB_ERR_CONVERGENCE
      return
    end if

    ! Recompute the converged state and static tangent.
    call rb_fixed_state(speed,journal_diameter,radial_clearance,viscosity,n_pads,pivot_angle,pad_arc, &
                        pad_axial_length,preload,offset,total_e_x,total_e_z,xj,yj,p_static, &
                        fx_hydro,fy_hydro,p_max,st)
    if (st /= RB_OK) then; status=st; return; end if

    call rb_force_only(speed,journal_diameter,radial_clearance,viscosity,n_pads,pivot_angle,pad_arc, &
                       pad_axial_length,preload,offset,total_e_x,total_e_z,xj+eps,yj,fxp,fyp,dummy_pmax,st)
    if (st /= RB_OK) then; status=st; return; end if
    call rb_force_only(speed,journal_diameter,radial_clearance,viscosity,n_pads,pivot_angle,pad_arc, &
                       pad_axial_length,preload,offset,total_e_x,total_e_z,xj-eps,yj,fxm,fym,dummy_pmax,st)
    if (st /= RB_OK) then; status=st; return; end if
    k_out(1,1)=-(fxp-fxm)/(2._rk*eps)
    k_out(2,1)=-(fyp-fym)/(2._rk*eps)

    call rb_force_only(speed,journal_diameter,radial_clearance,viscosity,n_pads,pivot_angle,pad_arc, &
                       pad_axial_length,preload,offset,total_e_x,total_e_z,xj,yj+eps,fxp,fyp,dummy_pmax,st)
    if (st /= RB_OK) then; status=st; return; end if
    call rb_force_only(speed,journal_diameter,radial_clearance,viscosity,n_pads,pivot_angle,pad_arc, &
                       pad_axial_length,preload,offset,total_e_x,total_e_z,xj,yj-eps,fxm,fym,dummy_pmax,st)
    if (st /= RB_OK) then; status=st; return; end if
    k_out(1,2)=-(fxp-fxm)/(2._rk*eps)
    k_out(2,2)=-(fyp-fym)/(2._rk*eps)

    call rb_damping_state(journal_diameter,radial_clearance,viscosity,n_pads,pivot_angle,pad_arc, &
                          pad_axial_length,preload,offset,total_e_x,total_e_z,xj,yj,p_static,c_out,st)
    if (st /= RB_OK) then; status=st; return; end if

    xj_ratio = xj/radial_clearance
    yj_ratio = yj/radial_clearance
  end subroutine rb_plain_journal_isoviscous


  subroutine rb_force_only(speed,journal_diameter,radial_clearance,viscosity,n_pads,pivot_angle,pad_arc, &
                           pad_axial_length,preload,offset,total_e_x,total_e_z,xj,yj,fx,fy,pmax,status)
    real(rk), intent(in) :: speed,journal_diameter,radial_clearance,viscosity,xj,yj
    integer(ik), intent(in) :: n_pads,total_e_x,total_e_z
    real(rk), intent(in) :: pivot_angle(n_pads),pad_arc(n_pads),pad_axial_length(n_pads),preload(n_pads),offset(n_pads)
    real(rk), intent(out) :: fx,fy,pmax
    integer(ik), intent(out) :: status
    real(rk), allocatable :: pressure(:,:)
    integer :: nn
    nn=(int(total_e_x)+1)*(int(total_e_z)+1)
    allocate(pressure(nn,n_pads))
    call rb_fixed_state(speed,journal_diameter,radial_clearance,viscosity,n_pads,pivot_angle,pad_arc, &
                        pad_axial_length,preload,offset,total_e_x,total_e_z,xj,yj,pressure,fx,fy,pmax,status)
  end subroutine rb_force_only


  subroutine rb_fixed_state(speed,journal_diameter,radial_clearance,viscosity,n_pads,pivot_angle,pad_arc, &
                            pad_axial_length,preload,offset,total_e_x,total_e_z,xj,yj,pressure,fx,fy,pmax,status)
    real(rk), intent(in) :: speed,journal_diameter,radial_clearance,viscosity,xj,yj
    integer(ik), intent(in) :: n_pads,total_e_x,total_e_z
    real(rk), intent(in) :: pivot_angle(n_pads),pad_arc(n_pads),pad_axial_length(n_pads),preload(n_pads),offset(n_pads)
    real(rk), intent(out) :: pressure(:,:),fx,fy,pmax
    integer(ik), intent(out) :: status
    integer :: p, nn
    real(rk) :: fxi,fyi,pmi
    real(rk), allocatable :: p_dummy(:)

    status=RB_OK; fx=0._rk; fy=0._rk; pmax=0._rk
    pressure=0._rk
    nn=(int(total_e_x)+1)*(int(total_e_z)+1)
    allocate(p_dummy(nn))
    p_dummy=0._rk
    do p=1,int(n_pads)
      call rb_solve_pad(0_ik,speed,journal_diameter,radial_clearance,viscosity,pivot_angle(p),pad_arc(p), &
                        pad_axial_length(p),preload(p),offset(p),total_e_x,total_e_z,xj,yj, &
                        p_dummy,pressure(:,p),fxi,fyi,pmi,status)
      if(status/=RB_OK)return
      fx=fx+fxi; fy=fy+fyi; pmax=max(pmax,pmi)
    end do
  end subroutine rb_fixed_state


  subroutine rb_damping_state(journal_diameter,radial_clearance,viscosity,n_pads,pivot_angle,pad_arc, &
                              pad_axial_length,preload,offset,total_e_x,total_e_z,xj,yj,p_static,c_out,status)
    real(rk), intent(in) :: journal_diameter,radial_clearance,viscosity,xj,yj
    integer(ik), intent(in) :: n_pads,total_e_x,total_e_z
    real(rk), intent(in) :: pivot_angle(n_pads),pad_arc(n_pads),pad_axial_length(n_pads),preload(n_pads),offset(n_pads)
    real(rk), intent(in) :: p_static(:,:)
    real(rk), intent(out) :: c_out(2,2)
    integer(ik), intent(out) :: status
    real(rk), allocatable :: ppert(:)
    real(rk) :: fx,fy,pm
    integer :: p,nn

    c_out=0._rk; status=RB_OK
    nn=(int(total_e_x)+1)*(int(total_e_z)+1)
    allocate(ppert(nn))
    do p=1,int(n_pads)
      call rb_solve_pad(1_ik,0._rk,journal_diameter,radial_clearance,viscosity,pivot_angle(p),pad_arc(p), &
                        pad_axial_length(p),preload(p),offset(p),total_e_x,total_e_z,xj,yj, &
                        p_static(:,p),ppert,fx,fy,pm,status)
      if(status/=RB_OK)return
      c_out(1,1)=c_out(1,1)+fx
      c_out(2,1)=c_out(2,1)+fy

      call rb_solve_pad(2_ik,0._rk,journal_diameter,radial_clearance,viscosity,pivot_angle(p),pad_arc(p), &
                        pad_axial_length(p),preload(p),offset(p),total_e_x,total_e_z,xj,yj, &
                        p_static(:,p),ppert,fx,fy,pm,status)
      if(status/=RB_OK)return
      c_out(1,2)=c_out(1,2)+fx
      c_out(2,2)=c_out(2,2)+fy
    end do
  end subroutine rb_damping_state


  subroutine rb_solve_pad(mode,speed,journal_diameter,radial_clearance,viscosity,pivot_angle,pad_arc, &
                          axial_length,preload,offset,total_e_x,total_e_z,xj,yj,p_static,pressure,fx,fy,pmax,status)
    integer(ik), intent(in) :: mode,total_e_x,total_e_z
    real(rk), intent(in) :: speed,journal_diameter,radial_clearance,viscosity,pivot_angle,pad_arc
    real(rk), intent(in) :: axial_length,preload,offset,xj,yj
    real(rk), intent(in) :: p_static(:)
    real(rk), intent(out) :: pressure(:),fx,fy,pmax
    integer(ik), intent(out) :: status

    integer :: nx,nz,nn,ne,bw,ncol,i,j,e,n1,n2,n3,n4,nbc,node
    real(rk) :: radius,cp,leading,dx,dz,theta,hval,h_e,dhdx_e,gamma,kcoef,q,u
    real(rk) :: em(4,4),ec(4),area,ang
    real(rk),allocatable :: h(:),gmat(:,:),rhs(:),al(:,:),pres(:)
    integer(ik),allocatable :: piv(:),bc(:),nodes0(:)
    integer(ik) :: st
    logical :: is360

    status=RB_OK; fx=0._rk; fy=0._rk; pmax=0._rk
    nx=int(total_e_x); nz=int(total_e_z); nn=(nx+1)*(nz+1); ne=nx*nz
    if(size(pressure)<nn .or. size(p_static)<nn)then;status=RB_ERR_INPUT;return;end if
    radius=0.5_rk*journal_diameter
    cp=radial_clearance/(1._rk-preload)
    leading=pivot_angle-pad_arc*offset
    dx=radius*pad_arc/real(nx,rk)
    dz=axial_length/real(nz,rk)
    bw=nz+3
    ncol=2*bw-1
    is360=abs(pad_arc-2._rk*acos(-1._rk))<1e-6_rk

    allocate(h(nn),gmat(nn,ncol),rhs(nn),al(nn,bw-1),piv(nn),bc(nn),pres(nn),nodes0(4))
    gmat=0._rk;rhs=0._rk;pressure=0._rk;bc=0_ik;pres=0._rk

    do i=0,nx
      theta=pad_arc*real(i,rk)/real(nx,rk)
      do j=0,nz
        node=i*(nz+1)+j+1
        hval=cp-xj*cos(leading+theta)-yj*sin(leading+theta)-preload*cp*cos(theta-offset*pad_arc)
        if(hval<=1e-10_rk)then;status=RB_ERR_CONVERGENCE;return;end if
        h(node)=hval
      end do
    end do

    gamma=-1._rk/(12._rk*viscosity)
    u=speed*radius

    do i=0,nx-1
      do j=0,nz-1
        e=i*nz+j+1
        n1=i*(nz+1)+j+1
        n2=(i+1)*(nz+1)+j+1
        n3=n2+1
        n4=n1+1
        h_e=0.25_rk*(h(n1)+h(n2)+h(n3)+h(n4))
        kcoef=h_e**3*gamma
        if(is360)then
          ! Current ROSS treats a 360-degree smooth pad as the short/oil-seal
          ! special case and suppresses the circumferential diffusion term.
          call rb_reynolds_q4_element(0._rk,kcoef,0._rk,dx,dz,em,ec,st)
        else
          select case(mode)
          case(0)
            dhdx_e=(-h(n1)+h(n2)+h(n3)-h(n4))/(2._rk*dx)
            q=0.5_rk*u*dhdx_e
          case(1)
            ang=leading+pad_arc*(real(i,rk)+0.5_rk)/real(nx,rk)
            q=-cos(ang)
          case(2)
            ang=leading+pad_arc*(real(i,rk)+0.5_rk)/real(nx,rk)
            q=-sin(ang)
          case default
            status=RB_ERR_INPUT;return
          end select
          call rb_reynolds_q4_element(kcoef,kcoef,q,dx,dz,em,ec,st)
        end if
        if(st/=RB_OK)then;status=st;return;end if
        nodes0=[int(n1-1,ik),int(n2-1,ik),int(n3-1,ik),int(n4-1,ik)]
        call rb_assemble_q4_banded(em,ec,nodes0,int(bw,ik),gmat,rhs,st)
        if(st/=RB_OK)then;status=st;return;end if
      end do
    end do

    nbc=0
    do i=0,nx
      do j=0,nz
        node=i*(nz+1)+j+1
        if(j==0 .or. j==nz .or. ((i==0 .or. i==nx) .and. .not.is360))then
          nbc=nbc+1;bc(nbc)=int(node-1,ik);pres(nbc)=0._rk
        else if(mode/=0_ik .and. abs(p_static(node))<1e-6_rk)then
          nbc=nbc+1;bc(nbc)=int(node-1,ik);pres(nbc)=0._rk
        end if
      end do
    end do

    call rb_include_pressure_bc(gmat,rhs,int(bw,ik),int(nbc,ik),bc,pres,int(nn,ik),st)
    if(st/=RB_OK)then;status=st;return;end if
    call rb_lu_factor_band(gmat,int(nn,ik),int(bw,ik),al,piv,st)
    if(st/=RB_OK)then;status=st;return;end if
    if(mode==0_ik)then
      call rb_lu_solve_band_cavitating(gmat,int(nn,ik),int(bw,ik),al,piv,rhs,0._rk,st)
    else
      ! Perturbation pressures are signed; current ROSS applies zero-pressure
      ! boundary conditions on the cavitated static nodes but does not clamp
      ! the perturbation solution itself.
      call rb_lu_solve_band_signed(gmat,int(nn,ik),int(bw,ik),al,piv,rhs,st)
    end if
    if(st/=RB_OK)then;status=st;return;end if
    pressure(1:nn)=rhs(1:nn)
    pmax=maxval(pressure(1:nn))

    do i=0,nx-1
      do j=0,nz-1
        n1=i*(nz+1)+j+1
        n2=(i+1)*(nz+1)+j+1
        n3=n2+1
        n4=n1+1
        area=dx*dz
        ang=leading+pad_arc*(real(i,rk)+0.5_rk)/real(nx,rk)
        if(mode==0_ik)then
          fx=fx-area*0.25_rk*(pressure(n1)+pressure(n2)+pressure(n3)+pressure(n4))*cos(ang)
          fy=fy-area*0.25_rk*(pressure(n1)+pressure(n2)+pressure(n3)+pressure(n4))*sin(ang)
        else
          fx=fx+area*0.25_rk*(pressure(n1)+pressure(n2)+pressure(n3)+pressure(n4))*cos(ang)
          fy=fy+area*0.25_rk*(pressure(n1)+pressure(n2)+pressure(n3)+pressure(n4))*sin(ang)
        end if
      end do
    end do
  end subroutine rb_solve_pad


  subroutine rb_lu_solve_band_signed(a,total_n,bandwidth,a_lower,index1,b,status)
    real(rk),intent(in)::a(:,:),a_lower(:,:)
    integer(ik),intent(in)::total_n,bandwidth,index1(:)
    real(rk),intent(inout)::b(:)
    integer(ik),intent(out)::status
    integer::total_column,ll,k,i,ip
    real(rk)::tmp,dum
    status=RB_OK
    total_column=2*int(bandwidth)-1
    if(total_n<1 .or. total_n>size(a,1) .or. bandwidth<1 .or. size(a,2)<total_column .or. &
       size(a_lower,1)<total_n .or. size(index1)<total_n .or. size(b)<total_n)then
      status=RB_ERR_INPUT;return
    end if
    ll=int(bandwidth)-1
    do k=1,int(total_n)
      ip=int(index1(k))
      if(ip<1 .or. ip>total_n)then;status=RB_ERR_INPUT;return;end if
      if(ip/=k)then;tmp=b(k);b(k)=b(ip);b(ip)=tmp;end if
      if(ll<total_n)ll=ll+1
      do i=k+1,ll
        b(i)=b(i)-a_lower(k,i-k)*b(k)
      end do
    end do
    ll=1
    do i=int(total_n),1,-1
      dum=b(i)
      do k=2,ll
        dum=dum-a(i,k)*b(k+i-1)
      end do
      if(abs(a(i,1))<=tiny(1._rk))then;status=RB_ERR_INPUT;return;end if
      b(i)=dum/a(i,1)
      if(ll<total_column)ll=ll+1
    end do
  end subroutine rb_lu_solve_band_signed

end module rb_plain_journal_physics
