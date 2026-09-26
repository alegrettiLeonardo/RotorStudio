module rb_interpolation
  use rb_kinds, only: rk, ik
  use rb_status, only: RB_OK, RB_ERR_INPUT, RB_ERR_UNSUPPORTED
  implicit none(type, external)
  private

  integer(ik), parameter, public :: RB_INTERP_PCHIP = 1_ik
  integer(ik), parameter, public :: RB_INTERP_LINEAR = 2_ik

  public :: rb_interp1, rb_interp2, rb_pchip_slopes, rb_validate_axis

contains

  subroutine rb_validate_axis(n, x, status)
    integer(ik), intent(in) :: n
    real(rk), intent(in) :: x(n)
    integer(ik), intent(out) :: status
    integer :: i

    status = RB_OK
    if (n < 1) then
      status = RB_ERR_INPUT
      return
    end if
    do i = 2, n
      if (x(i) <= x(i-1)) then
        status = RB_ERR_INPUT
        return
      end if
    end do
  end subroutine rb_validate_axis

  pure real(rk) function rb_edge_slope(h0, h1, m0, m1) result(d)
    real(rk), intent(in) :: h0, h1, m0, m1

    d = ((2._rk*h0 + h1)*m0 - h0*m1) / (h0 + h1)
    if (d*m0 <= 0._rk) then
      d = 0._rk
    else if (m0*m1 < 0._rk .and. abs(d) > abs(3._rk*m0)) then
      d = 3._rk*m0
    end if
  end function rb_edge_slope

  subroutine rb_pchip_slopes(n, x, y, d, status)
    integer(ik), intent(in) :: n
    real(rk), intent(in) :: x(n), y(n)
    real(rk), intent(out) :: d(n)
    integer(ik), intent(out) :: status
    real(rk), allocatable :: h(:), delta(:)
    real(rk) :: w1, w2
    integer :: i

    call rb_validate_axis(n, x, status)
    if (status /= RB_OK) return

    if (n == 1) then
      d(1) = 0._rk
      return
    end if

    allocate(h(n-1), delta(n-1))
    do i = 1, n-1
      h(i) = x(i+1) - x(i)
      delta(i) = (y(i+1) - y(i)) / h(i)
    end do

    if (n == 2) then
      d(1) = delta(1)
      d(2) = delta(1)
      return
    end if

    d(1) = rb_edge_slope(h(1), h(2), delta(1), delta(2))

    do i = 2, n-1
      if (delta(i-1) == 0._rk .or. delta(i) == 0._rk .or. delta(i-1)*delta(i) <= 0._rk) then
        d(i) = 0._rk
      else
        w1 = 2._rk*h(i) + h(i-1)
        w2 = h(i) + 2._rk*h(i-1)
        d(i) = (w1 + w2) / (w1/delta(i-1) + w2/delta(i))
      end if
    end do

    d(n) = rb_edge_slope(h(n-1), h(n-2), delta(n-1), delta(n-2))
  end subroutine rb_pchip_slopes

  subroutine rb_locate_interval(n, x, xq, idx)
    integer(ik), intent(in) :: n
    real(rk), intent(in) :: x(n), xq
    integer, intent(out) :: idx
    integer :: lo, hi, mid

    if (xq <= x(1)) then
      idx = 1
      return
    end if
    if (xq >= x(n)) then
      idx = n-1
      return
    end if

    lo = 1
    hi = n
    do while (hi - lo > 1)
      mid = (lo + hi) / 2
      if (xq < x(mid)) then
        hi = mid
      else
        lo = mid
      end if
    end do
    idx = lo
  end subroutine rb_locate_interval

  subroutine rb_interp1(n, x, y, xq, method, yq, status)
    integer(ik), intent(in) :: n, method
    real(rk), intent(in) :: x(n), y(n), xq
    real(rk), intent(out) :: yq
    integer(ik), intent(out) :: status
    real(rk), allocatable :: d(:)
    real(rk) :: h, t, h00, h10, h01, h11, slope
    integer :: i

    call rb_validate_axis(n, x, status)
    if (status /= RB_OK) return

    if (n == 1) then
      yq = y(1)
      return
    end if

    if (method /= RB_INTERP_PCHIP .and. method /= RB_INTERP_LINEAR) then
      status = RB_ERR_UNSUPPORTED
      return
    end if

    call rb_locate_interval(n, x, xq, i)

    if (method == RB_INTERP_LINEAR .or. n == 2) then
      slope = (y(i+1) - y(i)) / (x(i+1) - x(i))
      yq = y(i) + slope*(xq - x(i))
      return
    end if

    allocate(d(n))
    call rb_pchip_slopes(n, x, y, d, status)
    if (status /= RB_OK) return

    ! Current ROSS uses PCHIP only inside the tabulated range and extends
    ! linearly from the endpoint derivative outside the range.
    if (xq < x(1)) then
      yq = y(1) + d(1)*(xq - x(1))
      return
    end if
    if (xq > x(n)) then
      yq = y(n) + d(n)*(xq - x(n))
      return
    end if

    h = x(i+1) - x(i)
    t = (xq - x(i)) / h
    h00 = 2._rk*t**3 - 3._rk*t**2 + 1._rk
    h10 = t**3 - 2._rk*t**2 + t
    h01 = -2._rk*t**3 + 3._rk*t**2
    h11 = t**3 - t**2
    yq = h00*y(i) + h10*h*d(i) + h01*y(i+1) + h11*h*d(i+1)
  end subroutine rb_interp1

  subroutine rb_interp2(ns, speed, nf, frequency, values, speed_q, frequency_q, method, value_q, status)
    integer(ik), intent(in) :: ns, nf, method
    real(rk), intent(in) :: speed(ns), frequency(nf), values(ns,nf)
    real(rk), intent(in) :: speed_q, frequency_q
    real(rk), intent(out) :: value_q
    integer(ik), intent(out) :: status
    real(rk), allocatable :: row(:)
    integer :: j
    integer(ik) :: st

    call rb_validate_axis(ns, speed, status)
    if (status /= RB_OK) return
    call rb_validate_axis(nf, frequency, status)
    if (status /= RB_OK) return

    allocate(row(nf))
    do j = 1, nf
      call rb_interp1(ns, speed, values(:,j), speed_q, method, row(j), st)
      if (st /= RB_OK) then
        status = st
        return
      end if
    end do

    call rb_interp1(nf, frequency, row, frequency_q, method, value_q, status)
  end subroutine rb_interp2

end module rb_interpolation
