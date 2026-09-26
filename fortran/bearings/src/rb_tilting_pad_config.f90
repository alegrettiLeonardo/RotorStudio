module rb_tilting_pad_config
  use rb_kinds, only: rk, ik
  use rb_status, only: RB_OK, RB_ERR_INPUT, RB_ERR_UNSUPPORTED
  implicit none(type, external)
  private

  integer(ik), parameter, public :: RB_TP_CONVENTIONAL = 1_ik
  integer(ik), parameter, public :: RB_TP_INLET_GROOVE = 2_ik
  integer(ik), parameter, public :: RB_TP_SPRAY_BAR = 3_ik

  integer(ik), parameter, public :: RB_TP_MATCH_ECCENTRICITY = 1_ik
  integer(ik), parameter, public :: RB_TP_MATCH_LOAD = 2_ik

  public :: rb_tilting_pad_prepare

contains

  subroutine rb_tilting_pad_prepare(n_pads, journal_diameter, radial_clearance, pad_thickness, &
                                    pivot_angle, pad_arc, pad_axial_length, preload, offset, &
                                    bearing_type, equilibrium_type, eccentricity, attitude_angle, &
                                    use_xy, xj, yj, total_ex_film, total_ez_film, total_ey_pad, &
                                    initial_position, status)
    integer(ik), intent(in) :: n_pads, bearing_type, equilibrium_type
    integer(ik), intent(in) :: total_ex_film, total_ez_film, total_ey_pad
    real(rk), intent(in) :: journal_diameter, radial_clearance, pad_thickness
    real(rk), intent(in) :: pivot_angle(n_pads), pad_arc(n_pads)
    real(rk), intent(in) :: pad_axial_length(n_pads), preload(n_pads), offset(n_pads)
    real(rk), intent(in) :: eccentricity, attitude_angle, xj, yj
    logical, intent(in) :: use_xy
    real(rk), intent(out) :: initial_position(2)
    integer(ik), intent(out) :: status
    integer :: i

    status = RB_OK
    initial_position = 0._rk

    if (n_pads < 1 .or. journal_diameter <= 0._rk .or. radial_clearance <= 0._rk .or. pad_thickness <= 0._rk) then
      status = RB_ERR_INPUT
      return
    end if

    if (bearing_type /= RB_TP_CONVENTIONAL .and. bearing_type /= RB_TP_INLET_GROOVE .and. &
        bearing_type /= RB_TP_SPRAY_BAR) then
      status = RB_ERR_UNSUPPORTED
      return
    end if

    if (equilibrium_type /= RB_TP_MATCH_ECCENTRICITY .and. equilibrium_type /= RB_TP_MATCH_LOAD) then
      status = RB_ERR_UNSUPPORTED
      return
    end if

    ! Current ROSS fluid-film meshing requires even circumferential, axial
    ! and radial-pad element counts for the tilting-pad wrapper examples.
    if (total_ex_film < 2 .or. mod(total_ex_film,2_ik) /= 0 .or. &
        total_ez_film < 2 .or. mod(total_ez_film,2_ik) /= 0 .or. &
        total_ey_pad < 2 .or. mod(total_ey_pad,2_ik) /= 0) then
      status = RB_ERR_INPUT
      return
    end if

    do i = 1, n_pads
      if (pad_arc(i) <= 0._rk .or. pad_axial_length(i) <= 0._rk) then
        status = RB_ERR_INPUT
        return
      end if
      if (preload(i) < 0._rk .or. preload(i) >= 1._rk) then
        status = RB_ERR_INPUT
        return
      end if
      if (offset(i) < 0._rk .or. offset(i) > 1._rk) then
        status = RB_ERR_INPUT
        return
      end if
    end do

    if (use_xy) then
      initial_position = [xj, yj]
    else
      if (eccentricity < 0._rk .or. eccentricity >= 1._rk) then
        status = RB_ERR_INPUT
        return
      end if
      initial_position(1) = eccentricity*cos(attitude_angle)
      initial_position(2) = eccentricity*sin(attitude_angle)
    end if
  end subroutine rb_tilting_pad_prepare

end module rb_tilting_pad_config
