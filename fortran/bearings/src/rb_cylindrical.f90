module rb_cylindrical
  use rb_kinds, only: rk, ik
  use rb_status, only: RB_OK, RB_ERR_INPUT, RB_ERR_CONVERGENCE
  implicit none(type, external)
  private

  public :: rb_cylindrical_coefficients

contains

  pure real(rk) function rb_cyl_poly(x, s) result(p)
    real(rk), intent(in) :: x, s
    real(rk) :: pi2
    pi2 = acos(-1._rk)**2
    ! numpy.polynomial.Polynomial coefficients used by current ROSS:
    ! [1, -(4+pi^2*s^2), 6-s^2*(16-pi^2), -4, 1]
    p = 1._rk - (4._rk + pi2*s*s)*x + &
        (6._rk - s*s*(16._rk-pi2))*x*x - 4._rk*x**3 + x**4
  end function rb_cyl_poly

  subroutine rb_equilibrium_root(s, root, status)
    real(rk), intent(in) :: s
    real(rk), intent(out) :: root
    integer(ik), intent(out) :: status
    real(rk) :: lo, hi, mid, flo, fmid
    integer :: iter

    status = RB_OK
    root = 0._rk
    if (s <= 0._rk) then
      status = RB_ERR_INPUT
      return
    end if

    lo = 0._rk
    hi = 1._rk
    flo = rb_cyl_poly(lo, s)

    if (flo*rb_cyl_poly(hi, s) >= 0._rk) then
      status = RB_ERR_CONVERGENCE
      return
    end if

    do iter = 1, 200
      mid = 0.5_rk*(lo + hi)
      fmid = rb_cyl_poly(mid, s)
      if (abs(fmid) <= 1.0e-15_rk .or. (hi-lo) <= 2.0e-15_rk) exit
      if (flo*fmid > 0._rk) then
        lo = mid
        flo = fmid
      else
        hi = mid
      end if
    end do

    root = 0.5_rk*(lo + hi)
    if (.not.(root > 0._rk .and. root < 1._rk)) status = RB_ERR_CONVERGENCE
  end subroutine rb_equilibrium_root

  subroutine rb_cylindrical_coefficients(speed, weight, bearing_length, journal_diameter, radial_clearance, &
                                         oil_viscosity, modified_sommerfeld, sommerfeld, eccentricity, &
                                         attitude_angle, K, C, status)
    real(rk), intent(in) :: speed, weight, bearing_length, journal_diameter
    real(rk), intent(in) :: radial_clearance, oil_viscosity
    real(rk), intent(out) :: modified_sommerfeld, sommerfeld, eccentricity, attitude_angle
    real(rk), intent(out) :: K(2,2), C(2,2)
    integer(ik), intent(out) :: status
    real(rk) :: root, e, pi_, h0
    real(rk) :: auu, auv, avu, avv, buu, buv, bvu, bvv

    K = 0._rk
    C = 0._rk
    modified_sommerfeld = 0._rk
    sommerfeld = 0._rk
    eccentricity = 0._rk
    attitude_angle = 0._rk
    status = RB_OK

    if (speed <= 0._rk .or. weight <= 0._rk .or. bearing_length <= 0._rk .or. &
        journal_diameter <= 0._rk .or. radial_clearance <= 0._rk .or. oil_viscosity <= 0._rk) then
      status = RB_ERR_INPUT
      return
    end if

    pi_ = acos(-1._rk)
    modified_sommerfeld = journal_diameter * speed * oil_viscosity * bearing_length**3 / &
                          (8._rk * radial_clearance**2 * weight)
    sommerfeld = (modified_sommerfeld/pi_) * (journal_diameter/bearing_length)**2

    call rb_equilibrium_root(modified_sommerfeld, root, status)
    if (status /= RB_OK) return

    e = sqrt(root)
    eccentricity = e
    attitude_angle = atan(pi_*sqrt(1._rk-e*e)/(4._rk*e))

    h0 = 1._rk / (pi_**2*(1._rk-e*e) + 16._rk*e*e)**1.5_rk
    auu = h0 * 4._rk * (pi_**2*(2._rk-e*e) + 16._rk*e*e)
    auv = h0 * pi_ * (pi_**2*(1._rk-e*e)**2 - 16._rk*e**4) / &
          (e*sqrt(1._rk-e*e))
    avu = -h0 * pi_ * (pi_**2*(1._rk-e*e)*(1._rk+2._rk*e*e) + &
          32._rk*e*e*(1._rk+e*e)) / (e*sqrt(1._rk-e*e))
    avv = h0 * 4._rk * (pi_**2*(1._rk+2._rk*e*e) + &
          32._rk*e*e*(1._rk+e*e)/(1._rk-e*e))
    buu = h0 * 2._rk*pi_*sqrt(1._rk-e*e) * &
          (pi_**2*(1._rk+2._rk*e*e)-16._rk*e*e) / e
    buv = -h0 * 8._rk * (pi_**2*(1._rk+2._rk*e*e)-16._rk*e*e)
    bvu = buv
    bvv = h0 * 2._rk*pi_ * (pi_**2*(1._rk-e*e)**2 + 48._rk*e*e) / &
          (e*sqrt(1._rk-e*e))

    K(1,1) = weight/radial_clearance * auu
    K(1,2) = weight/radial_clearance * auv
    K(2,1) = weight/radial_clearance * avu
    K(2,2) = weight/radial_clearance * avv

    C(1,1) = weight/(radial_clearance*speed) * buu
    C(1,2) = weight/(radial_clearance*speed) * buv
    C(2,1) = weight/(radial_clearance*speed) * bvu
    C(2,2) = weight/(radial_clearance*speed) * bvv
  end subroutine rb_cylindrical_coefficients

end module rb_cylindrical
