module rb_fixed_geometry
  use rb_kinds, only: rk, ik
  use rb_status, only: RB_OK, RB_ERR_INPUT
  implicit none(type, external)
  private

  public :: rb_partial_arc_geometry
  public :: rb_elliptical_geometry
  public :: rb_offset_halves_geometry
  public :: rb_multi_lobe_geometry
  public :: rb_pressure_dam_geometry
  public :: rb_plain_journal_geometry

contains

  subroutine rb_partial_arc_geometry(pad_arc_in, arc_center, preload_in, offset_in, &
                                     n_pads, pivot_angle, pad_arc, preload, offset, status)
    real(rk), intent(in) :: pad_arc_in, arc_center, preload_in, offset_in
    integer(ik), intent(out) :: n_pads, status
    real(rk), intent(out) :: pivot_angle(1), pad_arc(1), preload(1), offset(1)

    status = RB_OK
    n_pads = 0
    if (pad_arc_in <= 0._rk) then
      status = RB_ERR_INPUT
      return
    end if
    n_pads = 1
    pivot_angle(1) = arc_center
    pad_arc(1) = pad_arc_in
    preload(1) = preload_in
    offset(1) = offset_in
  end subroutine rb_partial_arc_geometry

  subroutine rb_elliptical_geometry(pad_arc_in, preload_in, n_pads, pivot_angle, pad_arc, preload, offset, status)
    real(rk), intent(in) :: pad_arc_in, preload_in
    integer(ik), intent(out) :: n_pads, status
    real(rk), intent(out) :: pivot_angle(2), pad_arc(2), preload(2), offset(2)
    real(rk), parameter :: pi_ = acos(-1._rk)

    status = RB_OK
    n_pads = 0
    if (pad_arc_in <= 0._rk) then
      status = RB_ERR_INPUT
      return
    end if

    n_pads = 2
    pivot_angle = [pi_/2._rk, 3._rk*pi_/2._rk]
    pad_arc = pad_arc_in
    preload = preload_in
    offset = 0.5_rk
  end subroutine rb_elliptical_geometry

  subroutine rb_offset_halves_geometry(pad_arc_in, preload_in, offset_in, n_pads, &
                                       pivot_angle, pad_arc, preload, offset, status)
    real(rk), intent(in) :: pad_arc_in, preload_in, offset_in
    integer(ik), intent(out) :: n_pads, status
    real(rk), intent(out) :: pivot_angle(2), pad_arc(2), preload(2), offset(2)
    real(rk), parameter :: pi_ = acos(-1._rk)

    status = RB_OK
    n_pads = 0
    if (pad_arc_in <= 0._rk) then
      status = RB_ERR_INPUT
      return
    end if

    n_pads = 2
    pivot_angle = [pi_/2._rk, 3._rk*pi_/2._rk]
    pad_arc = pad_arc_in
    preload = preload_in
    offset = offset_in
  end subroutine rb_offset_halves_geometry

  subroutine rb_multi_lobe_geometry(n_lobes, pad_arc_in, preload_in, offset_in, first_lobe_angle, &
                                    use_first_lobe_angle, pivot_angle, pad_arc, preload, offset, status)
    integer(ik), intent(in) :: n_lobes
    real(rk), intent(in) :: pad_arc_in, preload_in(n_lobes), offset_in(n_lobes), first_lobe_angle
    logical, intent(in) :: use_first_lobe_angle
    real(rk), intent(out) :: pivot_angle(n_lobes), pad_arc(n_lobes), preload(n_lobes), offset(n_lobes)
    integer(ik), intent(out) :: status
    real(rk) :: first
    integer :: i

    status = RB_OK
    if (n_lobes < 2 .or. pad_arc_in <= 0._rk) then
      status = RB_ERR_INPUT
      return
    end if

    if (use_first_lobe_angle) then
      first = first_lobe_angle
    else
      first = acos(-1._rk)/real(n_lobes,rk)
    end if

    do i = 1, n_lobes
      pivot_angle(i) = first + real(i-1,rk)*(2._rk*acos(-1._rk)/real(n_lobes,rk))
      pad_arc(i) = pad_arc_in
      preload(i) = preload_in(i)
      offset(i) = offset_in(i)
    end do
  end subroutine rb_multi_lobe_geometry

  subroutine rb_pressure_dam_geometry(pad_arc_in, dam_arc, dam_axial_length, dam_depth, &
                                      dam_on_top, dam_on_bottom, preload_in, n_pads, &
                                      pivot_angle, pad_arc, preload, offset, track_arc, &
                                      track_axial_length, track_depth, status)
    real(rk), intent(in) :: pad_arc_in, dam_arc, dam_axial_length, dam_depth, preload_in
    logical, intent(in) :: dam_on_top, dam_on_bottom
    integer(ik), intent(out) :: n_pads, status
    real(rk), intent(out) :: pivot_angle(2), pad_arc(2), preload(2), offset(2)
    real(rk), intent(out) :: track_arc(2), track_axial_length(2), track_depth(2)
    real(rk), parameter :: pi_ = acos(-1._rk)

    status = RB_OK
    n_pads = 0
    if (pad_arc_in <= 0._rk .or. dam_arc <= 0._rk .or. dam_axial_length <= 0._rk .or. dam_depth <= 0._rk) then
      status = RB_ERR_INPUT
      return
    end if

    n_pads = 2
    pivot_angle = [pi_/2._rk, 3._rk*pi_/2._rk]
    pad_arc = pad_arc_in
    preload = preload_in
    offset = 0.5_rk
    track_arc = 0._rk
    track_axial_length = 0._rk
    track_depth = 0._rk

    if (dam_on_top) then
      track_arc(1) = dam_arc
      track_axial_length(1) = dam_axial_length
      track_depth(1) = dam_depth
    end if
    if (dam_on_bottom) then
      track_arc(2) = dam_arc
      track_axial_length(2) = dam_axial_length
      track_depth(2) = dam_depth
    end if
  end subroutine rb_pressure_dam_geometry

  subroutine rb_plain_journal_geometry(n_pads, pad_arc_in, preload_in, pad_axial_length_in, journal_diameter, &
                                       pad_thickness_in, use_pad_thickness, pivot_angle, pad_arc, preload, offset, &
                                       pad_axial_length, pad_thickness, status)
    integer(ik), intent(in) :: n_pads
    real(rk), intent(in) :: pad_arc_in, preload_in, pad_axial_length_in, journal_diameter, pad_thickness_in
    logical, intent(in) :: use_pad_thickness
    real(rk), intent(out) :: pivot_angle(n_pads), pad_arc(n_pads), preload(n_pads), offset(n_pads)
    real(rk), intent(out) :: pad_axial_length(n_pads), pad_thickness
    integer(ik), intent(out) :: status
    real(rk) :: step, first
    integer :: i

    status = RB_OK
    if (n_pads < 1 .or. pad_arc_in <= 0._rk .or. pad_axial_length_in <= 0._rk .or. journal_diameter <= 0._rk) then
      status = RB_ERR_INPUT
      return
    end if

    step = 2._rk*acos(-1._rk)/real(n_pads,rk)
    first = acos(-1._rk)/real(n_pads,rk)
    do i = 1, n_pads
      pivot_angle(i) = first + real(i-1,rk)*step
      pad_arc(i) = pad_arc_in
      preload(i) = preload_in
      offset(i) = 0.5_rk
      pad_axial_length(i) = pad_axial_length_in
    end do

    if (use_pad_thickness) then
      if (pad_thickness_in <= 0._rk) then
        status = RB_ERR_INPUT
        return
      end if
      pad_thickness = pad_thickness_in
    else
      pad_thickness = journal_diameter/4._rk
    end if
  end subroutine rb_plain_journal_geometry

end module rb_fixed_geometry
