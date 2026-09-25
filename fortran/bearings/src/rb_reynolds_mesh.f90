module rb_reynolds_mesh
  use rb_kinds, only: rk, ik
  use rb_status, only: RB_OK, RB_ERR_INPUT
  implicit none(type, external)
  private

  public :: rb_reynolds_mesh_smooth

contains

  subroutine rb_reynolds_mesh_smooth(total_e_x, total_e_z, arc_length_rad, pad_length, axial_length, &
                                     x, x_rad, z, node_i0, node_j0, node_k0, node_l0, &
                                     e_length, e_width, dx, dz, bandwidth, status)
    integer(ik), intent(in) :: total_e_x, total_e_z
    real(rk), intent(in) :: arc_length_rad, pad_length, axial_length
    real(rk), intent(out) :: x(:), x_rad(:), z(:)
    integer(ik), intent(out) :: node_i0(:), node_j0(:), node_k0(:), node_l0(:)
    real(rk), intent(out) :: e_length(:), e_width(:), dx(:,:), dz(:,:)
    integer(ik), intent(out) :: bandwidth, status
    integer :: nx, nz, nn, ne, ix, iz, n, e, ni, nj, nk, nl
    real(rk) :: lx, lrad, wz

    status = RB_OK
    bandwidth = 0_ik
    nx = int(total_e_x)
    nz = int(total_e_z)
    nn = (nx+1)*(nz+1)
    ne = nx*nz

    if (nx < 1 .or. nz < 1 .or. arc_length_rad <= 0._rk .or. &
        pad_length <= 0._rk .or. axial_length <= 0._rk .or. &
        size(x) < nn .or. size(x_rad) < nn .or. size(z) < nn .or. &
        size(node_i0) < ne .or. size(node_j0) < ne .or. size(node_k0) < ne .or. size(node_l0) < ne .or. &
        size(e_length) < ne .or. size(e_width) < ne .or. size(dx,1) < ne .or. size(dx,2) < 4 .or. &
        size(dz,1) < ne .or. size(dz,2) < 4) then
      status = RB_ERR_INPUT
      return
    end if

    lx = pad_length/real(nx,rk)
    lrad = arc_length_rad/real(nx,rk)
    wz = axial_length/real(nz,rk)

    ! ROSS node ordering: circumferential station outer loop, axial node
    ! inner loop. Stored node ids remain 0-based.
    n = 0
    do ix = 0, nx
      do iz = 0, nz
        n = n + 1
        x(n) = real(ix,rk)*lx
        x_rad(n) = real(ix,rk)*lrad
        z(n) = real(iz,rk)*wz
      end do
    end do

    e = 0
    do ix = 0, nx-1
      do iz = 0, nz-1
        e = e + 1
        ni = ix*(nz+1) + iz
        nj = ni + nz + 1
        nk = nj + 1
        nl = ni + 1

        node_i0(e) = int(ni,ik)
        node_j0(e) = int(nj,ik)
        node_k0(e) = int(nk,ik)
        node_l0(e) = int(nl,ik)

        e_length(e) = lx
        e_width(e) = wz
        dx(e,:) = [-1._rk/(2._rk*lx), 1._rk/(2._rk*lx), 1._rk/(2._rk*lx), -1._rk/(2._rk*lx)]
        dz(e,:) = [-1._rk/(2._rk*wz), -1._rk/(2._rk*wz), 1._rk/(2._rk*wz), 1._rk/(2._rk*wz)]
      end do
    end do

    bandwidth = int((nz+1)+1,ik)
  end subroutine rb_reynolds_mesh_smooth

end module rb_reynolds_mesh
