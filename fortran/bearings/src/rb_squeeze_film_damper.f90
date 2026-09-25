module rb_squeeze_film_damper
  use rb_kinds, only: rk, ik
  use rb_status, only: RB_OK, RB_ERR_INPUT, RB_ERR_UNSUPPORTED
  implicit none(type, external)
  private

  integer(ik), parameter, public :: RB_SFD_GROOVE = 1_ik
  integer(ik), parameter, public :: RB_SFD_END_SEALS = 2_ik
  integer(ik), parameter, public :: RB_SFD_GROOVE_END_SEALS = 3_ik

  public :: rb_sfd_coefficients

contains

  subroutine rb_sfd_coefficients(frequency, axial_length, journal_diameter, radial_clearance, &
                                 eccentricity_ratio, viscosity, geometry, cavitation, &
                                 stiffness, damping, theta, p_max, status)
    real(rk), intent(in) :: frequency, axial_length, journal_diameter, radial_clearance
    real(rk), intent(in) :: eccentricity_ratio, viscosity
    integer(ik), intent(in) :: geometry
    logical, intent(in) :: cavitation
    real(rk), intent(out) :: stiffness, damping, theta, p_max
    integer(ik), intent(out) :: status
    real(rk) :: radius, e, theta_deg, pi_

    stiffness = 0._rk
    damping = 0._rk
    theta = 0._rk
    p_max = 0._rk
    status = RB_OK
    pi_ = acos(-1._rk)

    if (frequency < 0._rk .or. axial_length <= 0._rk .or. journal_diameter <= 0._rk .or. &
        radial_clearance <= 0._rk .or. viscosity <= 0._rk) then
      status = RB_ERR_INPUT
      return
    end if

    e = eccentricity_ratio
    if (e < 0._rk .or. e >= 1._rk) then
      status = RB_ERR_INPUT
      return
    end if
    radius = journal_diameter/2._rk

    select case (geometry)
    case (RB_SFD_END_SEALS)
      damping = 12._rk*pi_*axial_length*(radius/radial_clearance)**3*viscosity
      damping = damping / ((2._rk+e*e)*sqrt(1._rk-e*e))

      stiffness = 24._rk*viscosity*axial_length*(radius/radial_clearance)**3*e*frequency
      stiffness = stiffness / ((2._rk+e*e)*(1._rk-e*e))

      theta_deg = -80.45_rk*e + 268.98_rk
      theta = theta_deg*pi_/180._rk

      p_max = -2._rk*e*(2._rk+e*cos(theta))*sin(theta)
      p_max = p_max / ((2._rk+e*e)*(1._rk+e*cos(theta))**2)
      p_max = p_max * 6._rk*viscosity*frequency*(radius/radial_clearance)**2

      if (cavitation) then
        stiffness = 0._rk
      else
        damping = 2._rk*damping
        stiffness = 0._rk
      end if

    case (RB_SFD_GROOVE)
      if (cavitation) then
        damping = viscosity*axial_length**3*radius/(2._rk*radial_clearance**3)
        damping = damping*pi_/(1._rk-e*e)**1.5_rk
        damping = damping/4._rk

        stiffness = 2._rk*viscosity*frequency*radius*(axial_length/radial_clearance)**3*e
        stiffness = stiffness/(1._rk-e*e)**2
        stiffness = stiffness/4._rk
      end if

      theta_deg = 270.443_rk - 191.831_rk*e + 218.223_rk*e**2 - 114.803_rk*e**3
      theta = theta_deg*pi_/180._rk

      p_max = -1.5_rk*(axial_length/radial_clearance)**2*viscosity*frequency*e*sin(theta)
      p_max = p_max/(1._rk+e*cos(theta))**3
      p_max = p_max/2._rk

      if (.not.cavitation) then
        stiffness = 0._rk
        damping = viscosity*(axial_length/radial_clearance)**3*radius*pi_
        damping = damping/(1._rk-e*e)**1.5_rk
      end if

    case (RB_SFD_GROOVE_END_SEALS)
      if (cavitation) then
        damping = viscosity*axial_length**3*radius/(2._rk*radial_clearance**3)
        damping = damping*pi_/(1._rk-e*e)**1.5_rk

        stiffness = 2._rk*viscosity*frequency*radius*(axial_length/radial_clearance)**3*e
        stiffness = stiffness/(1._rk-e*e)**2
      end if

      theta_deg = 270.443_rk - 191.831_rk*e + 218.223_rk*e**2 - 114.803_rk*e**3
      theta = theta_deg*pi_/180._rk

      p_max = -1.5_rk*(axial_length/radial_clearance)**2*viscosity*frequency*e*sin(theta)
      p_max = p_max/(1._rk+e*cos(theta))**3

      if (.not.cavitation) then
        stiffness = 0._rk
        damping = viscosity*(axial_length/radial_clearance)**3*radius*pi_
        damping = damping/(1._rk-e*e)**1.5_rk
      end if

    case default
      status = RB_ERR_UNSUPPORTED
      return
    end select
  end subroutine rb_sfd_coefficients

end module rb_squeeze_film_damper
