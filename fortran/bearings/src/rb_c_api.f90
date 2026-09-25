module rb_c_api
  use, intrinsic :: iso_c_binding, only: c_int, c_double
  use rb_kinds, only: rk, ik
  use rb_status, only: RB_OK, RB_ERR_INPUT
  use rb_interpolation, only: rb_interp1, rb_interp2
  use rb_rolling, only: rb_ball_coefficients, rb_roller_coefficients
  use rb_cylindrical, only: rb_cylindrical_coefficients
  use rb_squeeze_film_damper, only: rb_sfd_coefficients
  use rb_fixed_geometry, only: rb_elliptical_geometry, rb_offset_halves_geometry, rb_plain_journal_geometry
  use rb_tilting_pad_config, only: rb_tilting_pad_prepare
  implicit none(type, external)
  private

  public :: rb_interp1_c, rb_interp2_c
  public :: rb_ball_coefficients_c, rb_roller_coefficients_c
  public :: rb_cylindrical_coefficients_c, rb_sfd_coefficients_c
  public :: rb_elliptical_geometry_c, rb_offset_halves_geometry_c, rb_plain_journal_geometry_c
  public :: rb_tilting_pad_prepare_c

contains

  integer(c_int) function rb_interp1_c(n, x, y, xq, method, yq) bind(C, name="rb_interp1_c")
    integer(c_int), value :: n, method
    real(c_double), intent(in) :: x(*), y(*)
    real(c_double), value :: xq
    real(c_double), intent(out) :: yq
    real(rk), allocatable :: xr(:), yr(:)
    real(rk) :: out
    integer(ik) :: st

    if (n < 1_c_int) then
      rb_interp1_c = int(RB_ERR_INPUT, c_int)
      yq = 0.0_c_double
      return
    end if

    allocate(xr(n), yr(n))
    xr = real(x(1:n), rk)
    yr = real(y(1:n), rk)
    call rb_interp1(int(n,ik), xr, yr, real(xq,rk), int(method,ik), out, st)
    yq = real(out, c_double)
    rb_interp1_c = int(st, c_int)
  end function rb_interp1_c

  integer(c_int) function rb_interp2_c(ns, speed, nf, frequency, values, speed_q, frequency_q, method, value_q) &
      bind(C, name="rb_interp2_c")
    integer(c_int), value :: ns, nf, method
    real(c_double), intent(in) :: speed(*), frequency(*), values(*)
    real(c_double), value :: speed_q, frequency_q
    real(c_double), intent(out) :: value_q
    real(rk), allocatable :: sr(:), fr(:), vr(:,:)
    real(rk) :: out
    integer(ik) :: st
    integer :: i, j, idx

    if (ns < 1_c_int .or. nf < 1_c_int) then
      rb_interp2_c = int(RB_ERR_INPUT, c_int)
      value_q = 0.0_c_double
      return
    end if

    allocate(sr(ns), fr(nf), vr(ns,nf))
    sr = real(speed(1:ns), rk)
    fr = real(frequency(1:nf), rk)
    idx = 0
    do j = 1, nf
      do i = 1, ns
        idx = idx + 1
        vr(i,j) = real(values(idx), rk)
      end do
    end do

    call rb_interp2(int(ns,ik), sr, int(nf,ik), fr, vr, real(speed_q,rk), real(frequency_q,rk), &
                    int(method,ik), out, st)
    value_q = real(out, c_double)
    rb_interp2_c = int(st, c_int)
  end function rb_interp2_c

  integer(c_int) function rb_ball_coefficients_c(n_balls, d_balls, static_load, alpha, &
      use_cxx, cxx_in, use_cyy, cyy_in, kxx, kyy, cxx, cyy) bind(C, name="rb_ball_coefficients_c")
    real(c_double), value :: n_balls, d_balls, static_load, alpha, cxx_in, cyy_in
    integer(c_int), value :: use_cxx, use_cyy
    real(c_double), intent(out) :: kxx, kyy, cxx, cyy
    real(rk) :: kxx_r, kyy_r, cxx_r, cyy_r
    integer(ik) :: st

    call rb_ball_coefficients(real(n_balls,rk), real(d_balls,rk), real(static_load,rk), real(alpha,rk), &
                              use_cxx /= 0_c_int, real(cxx_in,rk), use_cyy /= 0_c_int, real(cyy_in,rk), &
                              kxx_r, kyy_r, cxx_r, cyy_r, st)
    kxx = real(kxx_r,c_double)
    kyy = real(kyy_r,c_double)
    cxx = real(cxx_r,c_double)
    cyy = real(cyy_r,c_double)
    rb_ball_coefficients_c = int(st,c_int)
  end function rb_ball_coefficients_c

  integer(c_int) function rb_roller_coefficients_c(n_rollers, l_rollers, static_load, alpha, &
      use_cxx, cxx_in, use_cyy, cyy_in, kxx, kyy, cxx, cyy) bind(C, name="rb_roller_coefficients_c")
    real(c_double), value :: n_rollers, l_rollers, static_load, alpha, cxx_in, cyy_in
    integer(c_int), value :: use_cxx, use_cyy
    real(c_double), intent(out) :: kxx, kyy, cxx, cyy
    real(rk) :: kxx_r, kyy_r, cxx_r, cyy_r
    integer(ik) :: st

    call rb_roller_coefficients(real(n_rollers,rk), real(l_rollers,rk), real(static_load,rk), real(alpha,rk), &
                                use_cxx /= 0_c_int, real(cxx_in,rk), use_cyy /= 0_c_int, real(cyy_in,rk), &
                                kxx_r, kyy_r, cxx_r, cyy_r, st)
    kxx = real(kxx_r,c_double)
    kyy = real(kyy_r,c_double)
    cxx = real(cxx_r,c_double)
    cyy = real(cyy_r,c_double)
    rb_roller_coefficients_c = int(st,c_int)
  end function rb_roller_coefficients_c

  integer(c_int) function rb_cylindrical_coefficients_c(speed, weight, bearing_length, journal_diameter, &
      radial_clearance, oil_viscosity, modified_sommerfeld, sommerfeld, eccentricity, attitude_angle, &
      kxx, kxy, kyx, kyy, cxx, cxy, cyx, cyy) bind(C, name="rb_cylindrical_coefficients_c")
    real(c_double), value :: speed, weight, bearing_length, journal_diameter, radial_clearance, oil_viscosity
    real(c_double), intent(out) :: modified_sommerfeld, sommerfeld, eccentricity, attitude_angle
    real(c_double), intent(out) :: kxx, kxy, kyx, kyy, cxx, cxy, cyx, cyy
    real(rk) :: ms_r, som_r, ecc_r, att_r, K(2,2), C(2,2)
    integer(ik) :: st

    call rb_cylindrical_coefficients(real(speed,rk), real(weight,rk), real(bearing_length,rk), &
                                     real(journal_diameter,rk), real(radial_clearance,rk), real(oil_viscosity,rk), &
                                     ms_r, som_r, ecc_r, att_r, K, C, st)
    modified_sommerfeld = real(ms_r,c_double)
    sommerfeld = real(som_r,c_double)
    eccentricity = real(ecc_r,c_double)
    attitude_angle = real(att_r,c_double)
    kxx = real(K(1,1),c_double)
    kxy = real(K(1,2),c_double)
    kyx = real(K(2,1),c_double)
    kyy = real(K(2,2),c_double)
    cxx = real(C(1,1),c_double)
    cxy = real(C(1,2),c_double)
    cyx = real(C(2,1),c_double)
    cyy = real(C(2,2),c_double)
    rb_cylindrical_coefficients_c = int(st,c_int)
  end function rb_cylindrical_coefficients_c

  integer(c_int) function rb_sfd_coefficients_c(frequency, axial_length, journal_diameter, radial_clearance, &
      eccentricity_ratio, viscosity, geometry, cavitation, stiffness, damping, theta, p_max) &
      bind(C, name="rb_sfd_coefficients_c")
    real(c_double), value :: frequency, axial_length, journal_diameter, radial_clearance
    real(c_double), value :: eccentricity_ratio, viscosity
    integer(c_int), value :: geometry, cavitation
    real(c_double), intent(out) :: stiffness, damping, theta, p_max
    real(rk) :: k_r, c_r, t_r, p_r
    integer(ik) :: st

    call rb_sfd_coefficients(real(frequency,rk), real(axial_length,rk), real(journal_diameter,rk), &
                             real(radial_clearance,rk), real(eccentricity_ratio,rk), real(viscosity,rk), &
                             int(geometry,ik), cavitation /= 0_c_int, k_r, c_r, t_r, p_r, st)
    stiffness = real(k_r,c_double)
    damping = real(c_r,c_double)
    theta = real(t_r,c_double)
    p_max = real(p_r,c_double)
    rb_sfd_coefficients_c = int(st,c_int)
  end function rb_sfd_coefficients_c

  integer(c_int) function rb_elliptical_geometry_c(pad_arc_in, preload_in, pivot_angle, pad_arc, preload, offset) &
      bind(C, name="rb_elliptical_geometry_c")
    real(c_double), value :: pad_arc_in, preload_in
    real(c_double), intent(out) :: pivot_angle(2), pad_arc(2), preload(2), offset(2)
    real(rk) :: pivot_r(2), arc_r(2), pre_r(2), off_r(2)
    integer(ik) :: np, st

    call rb_elliptical_geometry(real(pad_arc_in,rk), real(preload_in,rk), np, pivot_r, arc_r, pre_r, off_r, st)
    pivot_angle = real(pivot_r,c_double)
    pad_arc = real(arc_r,c_double)
    preload = real(pre_r,c_double)
    offset = real(off_r,c_double)
    rb_elliptical_geometry_c = int(st,c_int)
  end function rb_elliptical_geometry_c

  integer(c_int) function rb_offset_halves_geometry_c(pad_arc_in, preload_in, offset_in, &
      pivot_angle, pad_arc, preload, offset) bind(C, name="rb_offset_halves_geometry_c")
    real(c_double), value :: pad_arc_in, preload_in, offset_in
    real(c_double), intent(out) :: pivot_angle(2), pad_arc(2), preload(2), offset(2)
    real(rk) :: pivot_r(2), arc_r(2), pre_r(2), off_r(2)
    integer(ik) :: np, st

    call rb_offset_halves_geometry(real(pad_arc_in,rk), real(preload_in,rk), real(offset_in,rk), &
                                   np, pivot_r, arc_r, pre_r, off_r, st)
    pivot_angle = real(pivot_r,c_double)
    pad_arc = real(arc_r,c_double)
    preload = real(pre_r,c_double)
    offset = real(off_r,c_double)
    rb_offset_halves_geometry_c = int(st,c_int)
  end function rb_offset_halves_geometry_c

  integer(c_int) function rb_plain_journal_geometry_c(n_pads, pad_arc_in, preload_in, pad_axial_length_in, &
      journal_diameter, pad_thickness_in, use_pad_thickness, pivot_angle, pad_arc, preload, offset, &
      pad_axial_length, pad_thickness) bind(C, name="rb_plain_journal_geometry_c")
    integer(c_int), value :: n_pads, use_pad_thickness
    real(c_double), value :: pad_arc_in, preload_in, pad_axial_length_in, journal_diameter, pad_thickness_in
    real(c_double), intent(out) :: pivot_angle(*), pad_arc(*), preload(*), offset(*), pad_axial_length(*)
    real(c_double), intent(out) :: pad_thickness
    real(rk), allocatable :: pivot_r(:), arc_r(:), pre_r(:), off_r(:), len_r(:)
    real(rk) :: thick_r
    integer(ik) :: st

    if (n_pads < 1_c_int) then
      rb_plain_journal_geometry_c = int(RB_ERR_INPUT,c_int)
      pad_thickness = 0.0_c_double
      return
    end if
    allocate(pivot_r(n_pads), arc_r(n_pads), pre_r(n_pads), off_r(n_pads), len_r(n_pads))
    call rb_plain_journal_geometry(int(n_pads,ik), real(pad_arc_in,rk), real(preload_in,rk), &
                                   real(pad_axial_length_in,rk), real(journal_diameter,rk), &
                                   real(pad_thickness_in,rk), use_pad_thickness /= 0_c_int, &
                                   pivot_r, arc_r, pre_r, off_r, len_r, thick_r, st)
    pivot_angle(1:n_pads) = real(pivot_r,c_double)
    pad_arc(1:n_pads) = real(arc_r,c_double)
    preload(1:n_pads) = real(pre_r,c_double)
    offset(1:n_pads) = real(off_r,c_double)
    pad_axial_length(1:n_pads) = real(len_r,c_double)
    pad_thickness = real(thick_r,c_double)
    rb_plain_journal_geometry_c = int(st,c_int)
  end function rb_plain_journal_geometry_c

  integer(c_int) function rb_tilting_pad_prepare_c(n_pads, journal_diameter, radial_clearance, pad_thickness, &
      pivot_angle, pad_arc, pad_axial_length, preload, offset, bearing_type, equilibrium_type, eccentricity, &
      attitude_angle, use_xy, xj, yj, total_ex_film, total_ez_film, total_ey_pad, initial_position) &
      bind(C, name="rb_tilting_pad_prepare_c")
    integer(c_int), value :: n_pads, bearing_type, equilibrium_type, use_xy
    integer(c_int), value :: total_ex_film, total_ez_film, total_ey_pad
    real(c_double), value :: journal_diameter, radial_clearance, pad_thickness
    real(c_double), intent(in) :: pivot_angle(*), pad_arc(*), pad_axial_length(*), preload(*), offset(*)
    real(c_double), value :: eccentricity, attitude_angle, xj, yj
    real(c_double), intent(out) :: initial_position(2)
    real(rk), allocatable :: pivot_r(:), arc_r(:), len_r(:), pre_r(:), off_r(:)
    real(rk) :: pos_r(2)
    integer(ik) :: st

    if (n_pads < 1_c_int) then
      rb_tilting_pad_prepare_c = int(RB_ERR_INPUT,c_int)
      initial_position = 0.0_c_double
      return
    end if
    allocate(pivot_r(n_pads), arc_r(n_pads), len_r(n_pads), pre_r(n_pads), off_r(n_pads))
    pivot_r = real(pivot_angle(1:n_pads),rk)
    arc_r = real(pad_arc(1:n_pads),rk)
    len_r = real(pad_axial_length(1:n_pads),rk)
    pre_r = real(preload(1:n_pads),rk)
    off_r = real(offset(1:n_pads),rk)

    call rb_tilting_pad_prepare(int(n_pads,ik), real(journal_diameter,rk), real(radial_clearance,rk), &
                                real(pad_thickness,rk), pivot_r, arc_r, len_r, pre_r, off_r, &
                                int(bearing_type,ik), int(equilibrium_type,ik), real(eccentricity,rk), &
                                real(attitude_angle,rk), use_xy /= 0_c_int, real(xj,rk), real(yj,rk), &
                                int(total_ex_film,ik), int(total_ez_film,ik), int(total_ey_pad,ik), pos_r, st)
    initial_position = real(pos_r,c_double)
    rb_tilting_pad_prepare_c = int(st,c_int)
  end function rb_tilting_pad_prepare_c

end module rb_c_api
