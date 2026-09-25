module rb_dynamic_reduction
  use rb_kinds, only: rk, ik
  use rb_status, only: RB_OK, RB_ERR_INPUT
  implicit none(type, external)
  private

  public :: rb_dynamic_reduce_tilts

contains

  subroutine rb_dynamic_reduce_tilts(n_pads, k_journal, c_journal, &
                                     k_deltax, k_deltay, k_xdelta, k_ydelta, k_deltadelta, &
                                     c_deltax, c_deltay, c_xdelta, c_ydelta, c_deltadelta, &
                                     pad_length, pad_thickness, axial_length, pad_density, &
                                     excit_rad, k_rotate, k_reduced, c_reduced, ip, status)
    integer(ik), intent(in) :: n_pads
    real(rk), intent(in) :: k_journal(2,2), c_journal(2,2)
    real(rk), intent(in) :: k_deltax(n_pads), k_deltay(n_pads)
    real(rk), intent(in) :: k_xdelta(n_pads), k_ydelta(n_pads), k_deltadelta(n_pads)
    real(rk), intent(in) :: c_deltax(n_pads), c_deltay(n_pads)
    real(rk), intent(in) :: c_xdelta(n_pads), c_ydelta(n_pads), c_deltadelta(n_pads)
    real(rk), intent(in) :: pad_length(n_pads), pad_thickness, axial_length(n_pads), pad_density
    real(rk), intent(in) :: excit_rad, k_rotate(n_pads)
    real(rk), intent(out) :: k_reduced(2,2), c_reduced(2,2), ip(n_pads)
    integer(ik), intent(out) :: status

    complex(rk) :: ds(2,2), a1(2), a4(2), denom, iw
    real(rk) :: mass_pad
    integer :: p, i, j

    status = RB_OK
    k_reduced = 0._rk
    c_reduced = 0._rk
    ip = 0._rk

    if (n_pads < 1 .or. pad_thickness <= 0._rk .or. pad_density < 0._rk .or. excit_rad <= 0._rk) then
      status = RB_ERR_INPUT
      return
    end if
    if (any(pad_length <= 0._rk) .or. any(axial_length <= 0._rk)) then
      status = RB_ERR_INPUT
      return
    end if

    iw = cmplx(0._rk, excit_rad, kind=rk)
    do i = 1, 2
      do j = 1, 2
        ds(i,j) = cmplx(k_journal(i,j), excit_rad*c_journal(i,j), kind=rk)
      end do
    end do

    do p = 1, int(n_pads)
      mass_pad = pad_length(p)*pad_thickness*axial_length(p)*pad_density
      ip(p) = mass_pad*(pad_thickness**2 + pad_length(p)**2)/12._rk

      a1(1) = cmplx(k_xdelta(p), excit_rad*c_xdelta(p), kind=rk)
      a1(2) = cmplx(k_ydelta(p), excit_rad*c_ydelta(p), kind=rk)
      a4(1) = cmplx(k_deltax(p), excit_rad*c_deltax(p), kind=rk)
      a4(2) = cmplx(k_deltay(p), excit_rad*c_deltay(p), kind=rk)

      denom = cmplx(k_deltadelta(p) + k_rotate(p) - excit_rad**2*ip(p), &
                      excit_rad*c_deltadelta(p), kind=rk)
      if (abs(denom) <= tiny(1._rk)) then
        status = RB_ERR_INPUT
        return
      end if

      do i = 1, 2
        do j = 1, 2
          ds(i,j) = ds(i,j) - a1(i)*a4(j)/denom
        end do
      end do
    end do

    do i = 1, 2
      do j = 1, 2
        k_reduced(i,j) = real(ds(i,j),kind=rk)
        c_reduced(i,j) = aimag(ds(i,j))/excit_rad
      end do
    end do
  end subroutine rb_dynamic_reduce_tilts

end module rb_dynamic_reduction
