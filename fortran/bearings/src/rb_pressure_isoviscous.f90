module rb_pressure_isoviscous
  use rb_kinds, only: rk, ik
  use rb_status, only: RB_OK, RB_ERR_INPUT
  use rb_reynolds_mesh, only: rb_reynolds_mesh_smooth
  use rb_reynolds_element, only: rb_reynolds_q4_element
  use rb_reynolds_banded, only: rb_assemble_q4_banded, rb_include_pressure_bc, &
                                rb_lu_factor_band, rb_lu_solve_band_cavitating
  implicit none(type, external)
  private

  public :: rb_pressure_smooth_isoviscous

contains

  subroutine rb_pressure_smooth_isoviscous(total_e_x, total_e_z, arc_length_rad, pad_length, axial_length, &
                                           h_n, viscosity, speed_surface, press_cavitate, pressure, status)
    integer(ik), intent(in) :: total_e_x, total_e_z
    real(rk), intent(in) :: arc_length_rad, pad_length, axial_length
    real(rk), intent(in) :: h_n(:), viscosity, speed_surface, press_cavitate
    real(rk), intent(out) :: pressure(:)
    integer(ik), intent(out) :: status

    integer :: nx, nz, nn, ne, e, k, node, ix, iz, nbc, ncol
    integer(ik) :: bw, st
    real(rk), allocatable :: x(:), xr(:), z(:), el(:), ew(:), dx(:,:), dz(:,:)
    integer(ik), allocatable :: ni(:), nj(:), nk(:), nl(:), nodes(:)
    real(rk), allocatable :: a(:,:), rhs(:), al(:,:), em(:,:), ec(:), prescribed(:)
    integer(ik), allocatable :: piv(:), bc_idx(:)
    real(rk) :: h_e, dhdx_e, gamma_e, g_e, kx, kz, q
    logical :: is_360

    status = RB_OK
    pressure = 0._rk

    nx = int(total_e_x)
    nz = int(total_e_z)
    nn = (nx+1)*(nz+1)
    ne = nx*nz
    if (nx < 1 .or. nz < 1 .or. size(h_n) < nn .or. size(pressure) < nn .or. &
        viscosity <= 0._rk .or. pad_length <= 0._rk .or. axial_length <= 0._rk .or. arc_length_rad <= 0._rk) then
      status = RB_ERR_INPUT
      return
    end if
    if (minval(h_n(1:nn)) <= 0._rk) then
      status = RB_ERR_INPUT
      return
    end if

    allocate(x(nn),xr(nn),z(nn),el(ne),ew(ne),dx(ne,4),dz(ne,4))
    allocate(ni(ne),nj(ne),nk(ne),nl(ne))
    call rb_reynolds_mesh_smooth(total_e_x,total_e_z,arc_length_rad,pad_length,axial_length, &
                                 x,xr,z,ni,nj,nk,nl,el,ew,dx,dz,bw,st)
    if (st /= RB_OK) then
      status = st
      return
    end if

    ncol = 2*int(bw)-1
    allocate(a(nn,ncol),rhs(nn),al(nn,max(1,int(bw)-1)),piv(nn))
    allocate(em(4,4),ec(4),nodes(4))
    a = 0._rk
    rhs = 0._rk

    ! Constant-viscosity reduction of the generalized ROSS cross-film
    ! integrals: Gamma=-1/(12*mu), G=1/2.
    gamma_e = -1._rk/(12._rk*viscosity)
    g_e = 0.5_rk
    is_360 = abs(arc_length_rad-2._rk*acos(-1._rk)) < 1e-6_rk

    do e = 1, ne
      nodes = [ni(e),nj(e),nk(e),nl(e)]
      h_e = 0._rk
      dhdx_e = 0._rk
      do k = 1, 4
        node = int(nodes(k)) + 1
        h_e = h_e + 0.25_rk*h_n(node)
        dhdx_e = dhdx_e + dx(e,k)*h_n(node)
      end do
      kx = h_e**3*gamma_e
      kz = kx
      if (is_360) kx = 0._rk
      q = speed_surface*g_e*dhdx_e
      call rb_reynolds_q4_element(kx,kz,q,el(e),ew(e),em,ec,st)
      if (st /= RB_OK) then
        status = st
        return
      end if
      call rb_assemble_q4_banded(em,ec,nodes,bw,a,rhs,st)
      if (st /= RB_OK) then
        status = st
        return
      end if
    end do

    allocate(bc_idx(nn),prescribed(nn))
    nbc = 0
    do ix = 0, nx
      do iz = 0, nz
        node = ix*(nz+1) + iz
        if (iz == 0 .or. iz == nz .or. (.not.is_360 .and. (ix == 0 .or. ix == nx))) then
          nbc = nbc + 1
          bc_idx(nbc) = int(node,ik)
          prescribed(nbc) = 0._rk
        end if
      end do
    end do

    call rb_include_pressure_bc(a,rhs,bw,int(nbc,ik),bc_idx,prescribed,int(nn,ik),st)
    if (st /= RB_OK) then
      status = st
      return
    end if

    call rb_lu_factor_band(a,int(nn,ik),bw,al,piv,st)
    if (st /= RB_OK) then
      status = st
      return
    end if
    call rb_lu_solve_band_cavitating(a,int(nn,ik),bw,al,piv,rhs,press_cavitate,st)
    if (st /= RB_OK) then
      status = st
      return
    end if

    pressure(1:nn) = rhs(1:nn)
  end subroutine rb_pressure_smooth_isoviscous

end module rb_pressure_isoviscous
