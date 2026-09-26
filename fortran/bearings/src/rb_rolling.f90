module rb_rolling
  use rb_kinds, only: rk, ik
  use rb_status, only: RB_OK, RB_ERR_INPUT
  implicit none(type, external)
  private

  public :: rb_ball_coefficients, rb_roller_coefficients

contains

  pure real(rk) function rb_quadratic_ratio(x, x1, x2, x3, y1, y2, y3) result(y)
    real(rk), intent(in) :: x, x1, x2, x3, y1, y2, y3
    real(rk) :: l1, l2, l3

    ! With the three ROSS reference points this is the unique quadratic
    ! interpolant/extrapolant used by scipy interp1d(kind="quadratic").
    l1 = (x-x2)*(x-x3)/((x1-x2)*(x1-x3))
    l2 = (x-x1)*(x-x3)/((x2-x1)*(x2-x3))
    l3 = (x-x1)*(x-x2)/((x3-x1)*(x3-x2))
    y = y1*l1 + y2*l2 + y3*l3
  end function rb_quadratic_ratio

  subroutine rb_ball_coefficients(n_balls, d_balls, static_load, alpha, use_cxx, cxx_in, use_cyy, cyy_in, &
                                  kxx, kyy, cxx, cyy, status)
    real(rk), intent(in) :: n_balls, d_balls, static_load, alpha
    logical, intent(in) :: use_cxx, use_cyy
    real(rk), intent(in) :: cxx_in, cyy_in
    real(rk), intent(out) :: kxx, kyy, cxx, cyy
    integer(ik), intent(out) :: status
    real(rk), parameter :: Kb = 13.0e6_rk
    real(rk) :: ca, ratio

    status = RB_OK
    kxx = 0._rk; kyy = 0._rk; cxx = 0._rk; cyy = 0._rk
    ca = cos(alpha)
    if (n_balls <= 0._rk .or. d_balls <= 0._rk .or. static_load < 0._rk .or. ca < 0._rk) then
      status = RB_ERR_INPUT
      return
    end if

    kyy = Kb * n_balls**(2._rk/3._rk) * d_balls**(1._rk/3._rk) * &
          static_load**(1._rk/3._rk) * ca**(5._rk/3._rk)

    ratio = rb_quadratic_ratio(n_balls, 8._rk, 12._rk, 16._rk, 0.46_rk, 0.64_rk, 0.73_rk)
    kxx = ratio * kyy

    if (use_cxx) then
      cxx = cxx_in
    else
      cxx = 1.25e-5_rk * kxx
    end if
    if (use_cyy) then
      cyy = cyy_in
    else
      cyy = 1.25e-5_rk * kyy
    end if
  end subroutine rb_ball_coefficients

  subroutine rb_roller_coefficients(n_rollers, l_rollers, static_load, alpha, use_cxx, cxx_in, use_cyy, cyy_in, &
                                    kxx, kyy, cxx, cyy, status)
    real(rk), intent(in) :: n_rollers, l_rollers, static_load, alpha
    logical, intent(in) :: use_cxx, use_cyy
    real(rk), intent(in) :: cxx_in, cyy_in
    real(rk), intent(out) :: kxx, kyy, cxx, cyy
    integer(ik), intent(out) :: status
    real(rk), parameter :: Kb = 1.0e9_rk
    real(rk) :: ca, ratio

    status = RB_OK
    kxx = 0._rk; kyy = 0._rk; cxx = 0._rk; cyy = 0._rk
    ca = cos(alpha)
    if (n_rollers <= 0._rk .or. l_rollers <= 0._rk .or. static_load < 0._rk .or. ca < 0._rk) then
      status = RB_ERR_INPUT
      return
    end if

    kyy = Kb * n_rollers**0.9_rk * l_rollers**0.8_rk * static_load**0.1_rk * ca**1.9_rk

    ratio = rb_quadratic_ratio(n_rollers, 8._rk, 12._rk, 16._rk, 0.49_rk, 0.66_rk, 0.74_rk)
    kxx = ratio * kyy

    if (use_cxx) then
      cxx = cxx_in
    else
      cxx = 1.25e-5_rk * kxx
    end if
    if (use_cyy) then
      cyy = cyy_in
    else
      cyy = 1.25e-5_rk * kyy
    end if
  end subroutine rb_roller_coefficients

end module rb_rolling
