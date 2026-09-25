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
  use rb_reynolds_element, only: rb_reynolds_q4_element
  use rb_pressure_isoviscous, only: rb_pressure_smooth_isoviscous
  use rb_dynamic_reduction, only: rb_dynamic_reduce_tilts
  use rb_plain_journal_physics, only: rb_plain_journal_isoviscous
  use rb_tilting_pad_physics, only: rb_tilting_pad_isoviscous
  use rb_native_multiphysics, only: rb_plain_journal_multiphysics, rb_tilting_pad_multiphysics, rb_plain_journal_fixed_state
  implicit none(type, external)
  private

  public :: rb_interp1_c, rb_interp2_c
  public :: rb_ball_coefficients_c, rb_roller_coefficients_c
  public :: rb_cylindrical_coefficients_c, rb_sfd_coefficients_c
  public :: rb_elliptical_geometry_c, rb_offset_halves_geometry_c, rb_plain_journal_geometry_c
  public :: rb_tilting_pad_prepare_c, rb_reynolds_q4_element_c
  public :: rb_pressure_smooth_isoviscous_c, rb_dynamic_reduce_tilts_c
  public :: rb_plain_journal_isoviscous_c, rb_tilting_pad_isoviscous_c
  public :: rb_plain_journal_multiphysics_c, rb_tilting_pad_multiphysics_c
  public :: rb_plain_journal_multiphysics_pack_c, rb_tilting_pad_multiphysics_pack_c
  public :: rb_plain_journal_multiphysics_fields_pack_c, rb_tilting_pad_multiphysics_fields_pack_c
  public :: rb_plain_journal_fixed_state_pack_c

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

  integer(c_int) function rb_reynolds_q4_element_c(k_x, k_z, q, l_e, w_e, e_matrix, e_column) &
      bind(C, name="rb_reynolds_q4_element_c")
    real(c_double), value :: k_x, k_z, q, l_e, w_e
    real(c_double), intent(out) :: e_matrix(16), e_column(4)
    real(rk) :: em(4,4), ec(4)
    integer(ik) :: st
    integer :: i, j, idx

    call rb_reynolds_q4_element(real(k_x,rk), real(k_z,rk), real(q,rk), real(l_e,rk), real(w_e,rk), em, ec, st)
    idx = 0
    do j = 1, 4
      do i = 1, 4
        idx = idx + 1
        e_matrix(idx) = real(em(i,j),c_double)
      end do
    end do
    e_column = real(ec,c_double)
    rb_reynolds_q4_element_c = int(st,c_int)
  end function rb_reynolds_q4_element_c

  integer(c_int) function rb_pressure_smooth_isoviscous_c(total_e_x, total_e_z, arc_length_rad, &
      pad_length, axial_length, h_n, viscosity, speed_surface, press_cavitate, pressure) &
      bind(C, name="rb_pressure_smooth_isoviscous_c")
    integer(c_int), value :: total_e_x, total_e_z
    real(c_double), value :: arc_length_rad, pad_length, axial_length
    real(c_double), intent(in) :: h_n(*)
    real(c_double), value :: viscosity, speed_surface, press_cavitate
    real(c_double), intent(out) :: pressure(*)
    integer :: nn
    real(rk), allocatable :: hr(:), pr(:)
    integer(ik) :: st

    if (total_e_x < 1_c_int .or. total_e_z < 1_c_int) then
      rb_pressure_smooth_isoviscous_c = int(RB_ERR_INPUT,c_int)
      return
    end if
    nn = (int(total_e_x)+1)*(int(total_e_z)+1)
    allocate(hr(nn),pr(nn))
    hr = real(h_n(1:nn),rk)
    call rb_pressure_smooth_isoviscous(int(total_e_x,ik),int(total_e_z,ik),real(arc_length_rad,rk), &
                                       real(pad_length,rk),real(axial_length,rk),hr,real(viscosity,rk), &
                                       real(speed_surface,rk),real(press_cavitate,rk),pr,st)
    pressure(1:nn) = real(pr,c_double)
    rb_pressure_smooth_isoviscous_c = int(st,c_int)
  end function rb_pressure_smooth_isoviscous_c

  integer(c_int) function rb_dynamic_reduce_tilts_c(n_pads, k_journal, c_journal, &
      k_deltax, k_deltay, k_xdelta, k_ydelta, k_deltadelta, &
      c_deltax, c_deltay, c_xdelta, c_ydelta, c_deltadelta, &
      pad_length, pad_thickness, axial_length, pad_density, excit_rad, k_rotate, &
      k_reduced, c_reduced, ip) bind(C, name="rb_dynamic_reduce_tilts_c")
    integer(c_int), value :: n_pads
    real(c_double), intent(in) :: k_journal(4), c_journal(4)
    real(c_double), intent(in) :: k_deltax(*), k_deltay(*), k_xdelta(*), k_ydelta(*), k_deltadelta(*)
    real(c_double), intent(in) :: c_deltax(*), c_deltay(*), c_xdelta(*), c_ydelta(*), c_deltadelta(*)
    real(c_double), intent(in) :: pad_length(*), axial_length(*), k_rotate(*)
    real(c_double), value :: pad_thickness, pad_density, excit_rad
    real(c_double), intent(out) :: k_reduced(4), c_reduced(4), ip(*)
    real(rk) :: kj(2,2), cj(2,2), kr(2,2), cr(2,2)
    real(rk), allocatable :: kdx(:), kdy(:), kxd(:), kyd(:), kdd(:)
    real(rk), allocatable :: cdx(:), cdy(:), cxd(:), cyd(:), cdd(:)
    real(rk), allocatable :: plen(:), alen(:), krot(:), ipr(:)
    integer(ik) :: st
    integer :: n

    n = int(n_pads)
    if (n < 1) then
      rb_dynamic_reduce_tilts_c = int(RB_ERR_INPUT,c_int)
      return
    end if

    ! Matrix payload is Fortran column-major: [xx,yx,xy,yy], matching
    ! the native 2x2 storage used throughout this library.
    kj = reshape(real(k_journal,rk),[2,2])
    cj = reshape(real(c_journal,rk),[2,2])
    allocate(kdx(n),kdy(n),kxd(n),kyd(n),kdd(n),cdx(n),cdy(n),cxd(n),cyd(n),cdd(n))
    allocate(plen(n),alen(n),krot(n),ipr(n))
    kdx=real(k_deltax(1:n),rk); kdy=real(k_deltay(1:n),rk)
    kxd=real(k_xdelta(1:n),rk); kyd=real(k_ydelta(1:n),rk); kdd=real(k_deltadelta(1:n),rk)
    cdx=real(c_deltax(1:n),rk); cdy=real(c_deltay(1:n),rk)
    cxd=real(c_xdelta(1:n),rk); cyd=real(c_ydelta(1:n),rk); cdd=real(c_deltadelta(1:n),rk)
    plen=real(pad_length(1:n),rk); alen=real(axial_length(1:n),rk); krot=real(k_rotate(1:n),rk)

    call rb_dynamic_reduce_tilts(int(n,ik),kj,cj,kdx,kdy,kxd,kyd,kdd,cdx,cdy,cxd,cyd,cdd, &
                                 plen,real(pad_thickness,rk),alen,real(pad_density,rk), &
                                 real(excit_rad,rk),krot,kr,cr,ipr,st)
    k_reduced = [real(kr(1,1),c_double),real(kr(2,1),c_double), &
                 real(kr(1,2),c_double),real(kr(2,2),c_double)]
    c_reduced = [real(cr(1,1),c_double),real(cr(2,1),c_double), &
                 real(cr(1,2),c_double),real(cr(2,2),c_double)]
    ip(1:n)=real(ipr,c_double)
    rb_dynamic_reduce_tilts_c = int(st,c_int)
  end function rb_dynamic_reduce_tilts_c

  integer(c_int) function rb_plain_journal_isoviscous_c(speed, weight, fxs_load, fys_load, &
      journal_diameter, radial_clearance, viscosity, n_pads, pivot_angle, pad_arc, pad_axial_length, &
      preload, offset, total_e_x, total_e_z, xj_ratio_initial, yj_ratio_initial, relax_p, &
      max_iterations, force_tolerance, xj_ratio, yj_ratio, k_out, c_out, fx_hydro, fy_hydro, &
      p_max, iterations) bind(C, name="rb_plain_journal_isoviscous_c")
    real(c_double), value :: speed, weight, fxs_load, fys_load, journal_diameter, radial_clearance, viscosity
    integer(c_int), value :: n_pads, total_e_x, total_e_z, max_iterations
    real(c_double), intent(in) :: pivot_angle(*), pad_arc(*), pad_axial_length(*), preload(*), offset(*)
    real(c_double), value :: xj_ratio_initial, yj_ratio_initial, relax_p, force_tolerance
    real(c_double), intent(out) :: xj_ratio, yj_ratio, k_out(4), c_out(4), fx_hydro, fy_hydro, p_max
    integer(c_int), intent(out) :: iterations
    real(rk), allocatable :: pivot_r(:), arc_r(:), axial_r(:), pre_r(:), off_r(:)
    real(rk) :: xr, yr, kr(2,2), cr(2,2), fxr, fyr, pmaxr
    integer(ik) :: st, itr
    integer :: i, j, idx

    if (n_pads < 1_c_int) then
      rb_plain_journal_isoviscous_c = int(RB_ERR_INPUT,c_int)
      iterations = 0_c_int
      return
    end if

    allocate(pivot_r(n_pads), arc_r(n_pads), axial_r(n_pads), pre_r(n_pads), off_r(n_pads))
    pivot_r = real(pivot_angle(1:n_pads),rk)
    arc_r = real(pad_arc(1:n_pads),rk)
    axial_r = real(pad_axial_length(1:n_pads),rk)
    pre_r = real(preload(1:n_pads),rk)
    off_r = real(offset(1:n_pads),rk)

    call rb_plain_journal_isoviscous(real(speed,rk),real(weight,rk),real(fxs_load,rk),real(fys_load,rk), &
                                     real(journal_diameter,rk),real(radial_clearance,rk),real(viscosity,rk), &
                                     int(n_pads,ik),pivot_r,arc_r,axial_r,pre_r,off_r,int(total_e_x,ik), &
                                     int(total_e_z,ik),real(xj_ratio_initial,rk),real(yj_ratio_initial,rk), &
                                     real(relax_p,rk),int(max_iterations,ik),real(force_tolerance,rk), &
                                     xr,yr,kr,cr,fxr,fyr,pmaxr,itr,st)
    xj_ratio = real(xr,c_double)
    yj_ratio = real(yr,c_double)
    idx=0
    do j=1,2
      do i=1,2
        idx=idx+1
        k_out(idx)=real(kr(i,j),c_double)
        c_out(idx)=real(cr(i,j),c_double)
      end do
    end do
    fx_hydro=real(fxr,c_double)
    fy_hydro=real(fyr,c_double)
    p_max=real(pmaxr,c_double)
    iterations=int(itr,c_int)
    rb_plain_journal_isoviscous_c=int(st,c_int)
  end function rb_plain_journal_isoviscous_c


  integer(c_int) function rb_tilting_pad_isoviscous_c(speed, excitation_frequency, weight, fxs_load, fys_load, &
      journal_diameter, radial_clearance, viscosity, pad_thickness, pad_density, n_pads, pivot_angle, pad_arc, &
      pad_axial_length, preload, offset, k_rotate, total_e_x, total_e_z, xj_ratio_initial, yj_ratio_initial, &
      relax_p, max_iterations, force_tolerance, xj_ratio, yj_ratio, tilt_angle, k_out, c_out, fx_hydro, &
      fy_hydro, p_max, iterations) bind(C, name="rb_tilting_pad_isoviscous_c")
    real(c_double), value :: speed, excitation_frequency, weight, fxs_load, fys_load
    real(c_double), value :: journal_diameter, radial_clearance, viscosity, pad_thickness, pad_density
    integer(c_int), value :: n_pads, total_e_x, total_e_z, max_iterations
    real(c_double), intent(in) :: pivot_angle(*), pad_arc(*), pad_axial_length(*), preload(*), offset(*), k_rotate(*)
    real(c_double), value :: xj_ratio_initial, yj_ratio_initial, relax_p, force_tolerance
    real(c_double), intent(out) :: xj_ratio, yj_ratio, tilt_angle(*), k_out(4), c_out(4)
    real(c_double), intent(out) :: fx_hydro, fy_hydro, p_max
    integer(c_int), intent(out) :: iterations
    real(rk), allocatable :: piv_r(:), arc_r(:), axial_r(:), pre_r(:), off_r(:), krot_r(:), tilt_r(:)
    real(rk) :: xr, yr, kr(2,2), cr(2,2), fxr, fyr, pmaxr
    integer(ik) :: st, itr
    integer :: i, j, idx

    if (n_pads < 1_c_int) then
      rb_tilting_pad_isoviscous_c=int(RB_ERR_INPUT,c_int)
      iterations=0_c_int
      return
    end if
    allocate(piv_r(n_pads),arc_r(n_pads),axial_r(n_pads),pre_r(n_pads),off_r(n_pads),krot_r(n_pads),tilt_r(n_pads))
    piv_r=real(pivot_angle(1:n_pads),rk)
    arc_r=real(pad_arc(1:n_pads),rk)
    axial_r=real(pad_axial_length(1:n_pads),rk)
    pre_r=real(preload(1:n_pads),rk)
    off_r=real(offset(1:n_pads),rk)
    krot_r=real(k_rotate(1:n_pads),rk)

    call rb_tilting_pad_isoviscous(real(speed,rk),real(excitation_frequency,rk),real(weight,rk), &
                                   real(fxs_load,rk),real(fys_load,rk),real(journal_diameter,rk), &
                                   real(radial_clearance,rk),real(viscosity,rk),real(pad_thickness,rk), &
                                   real(pad_density,rk),int(n_pads,ik),piv_r,arc_r,axial_r,pre_r,off_r,krot_r, &
                                   int(total_e_x,ik),int(total_e_z,ik),real(xj_ratio_initial,rk), &
                                   real(yj_ratio_initial,rk),real(relax_p,rk),int(max_iterations,ik), &
                                   real(force_tolerance,rk),xr,yr,tilt_r,kr,cr,fxr,fyr,pmaxr,itr,st)
    xj_ratio=real(xr,c_double)
    yj_ratio=real(yr,c_double)
    tilt_angle(1:n_pads)=real(tilt_r,c_double)
    idx=0
    do j=1,2
      do i=1,2
        idx=idx+1
        k_out(idx)=real(kr(i,j),c_double)
        c_out(idx)=real(cr(i,j),c_double)
      end do
    end do
    fx_hydro=real(fxr,c_double);fy_hydro=real(fyr,c_double);p_max=real(pmaxr,c_double)
    iterations=int(itr,c_int)
    rb_tilting_pad_isoviscous_c=int(st,c_int)
  end function rb_tilting_pad_isoviscous_c



  integer(c_int) function rb_plain_journal_multiphysics_c(speed,weight,fxs_load,fys_load,d,cb,mu1,mu2,t1,t2,rho,cp,klube, &
      thermal_type,deform_type,pad_thickness,kpad,epad,nupad,alphapad,temp_supply,temp_journal,temp_ambient,convec_edges, &
      convec_back,n_pads,pivot_angle,pad_arc,pad_axial_length,preload,offset,total_e_x,total_e_z,total_e_y_pad,total_e_y_film, &
      xj_ratio_initial,yj_ratio_initial,relax_p,relax_t,max_iterations,outer_iterations,force_tolerance,field_tolerance, &
      xj_ratio,yj_ratio,k_out,c_out,fx_hydro,fy_hydro,p_max,t_max,t_out,deform_max,iterations) &
      bind(C,name="rb_plain_journal_multiphysics_c")
    real(c_double),value::speed,weight,fxs_load,fys_load,d,cb,mu1,mu2,t1,t2,rho,cp,klube
    integer(c_int),value::thermal_type,deform_type
    real(c_double),value::pad_thickness,kpad,epad,nupad,alphapad,temp_supply,temp_journal,temp_ambient,convec_edges,convec_back
    integer(c_int),value::n_pads,total_e_x,total_e_z,total_e_y_pad,total_e_y_film
    real(c_double),intent(in)::pivot_angle(*),pad_arc(*),pad_axial_length(*),preload(*),offset(*)
    real(c_double),value::xj_ratio_initial,yj_ratio_initial,relax_p,relax_t,force_tolerance,field_tolerance
    integer(c_int),value::max_iterations,outer_iterations
    real(c_double),intent(out)::xj_ratio,yj_ratio,k_out(4),c_out(4),fx_hydro,fy_hydro,p_max,t_max,t_out,deform_max
    integer(c_int),intent(out)::iterations
    real(rk),allocatable::piv(:),arc(:),alen(:),pre(:),off(:)
    real(rk)::xr,yr,k(2,2),cc(2,2),fx,fy,pm,tm,to,dm
    integer(ik)::st,it
    integer::n
    n=int(n_pads)
    if(n<1)then
      rb_plain_journal_multiphysics_c=int(RB_ERR_INPUT,c_int);iterations=0_c_int;return
    end if
    allocate(piv(n),arc(n),alen(n),pre(n),off(n))
    piv=real(pivot_angle(1:n),rk);arc=real(pad_arc(1:n),rk);alen=real(pad_axial_length(1:n),rk)
    pre=real(preload(1:n),rk);off=real(offset(1:n),rk)
    call rb_plain_journal_multiphysics(real(speed,rk),real(weight,rk),real(fxs_load,rk),real(fys_load,rk),real(d,rk), &
      real(cb,rk),real(mu1,rk),real(mu2,rk),real(t1,rk),real(t2,rk),real(rho,rk),real(cp,rk),real(klube,rk), &
      int(thermal_type,ik),int(deform_type,ik),real(pad_thickness,rk),real(kpad,rk),real(epad,rk),real(nupad,rk), &
      real(alphapad,rk),real(temp_supply,rk),real(temp_journal,rk),real(temp_ambient,rk),real(convec_edges,rk), &
      real(convec_back,rk),int(n_pads,ik),piv,arc,alen,pre,off,int(total_e_x,ik),int(total_e_z,ik),int(total_e_y_pad,ik), &
      int(total_e_y_film,ik),real(xj_ratio_initial,rk),real(yj_ratio_initial,rk),real(relax_p,rk),real(relax_t,rk), &
      int(max_iterations,ik),int(outer_iterations,ik),real(force_tolerance,rk),real(field_tolerance,rk),xr,yr,k,cc, &
      fx,fy,pm,tm,to,dm,it,st)
    xj_ratio=real(xr,c_double);yj_ratio=real(yr,c_double)
    k_out=[real(k(1,1),c_double),real(k(2,1),c_double),real(k(1,2),c_double),real(k(2,2),c_double)]
    c_out=[real(cc(1,1),c_double),real(cc(2,1),c_double),real(cc(1,2),c_double),real(cc(2,2),c_double)]
    fx_hydro=real(fx,c_double);fy_hydro=real(fy,c_double);p_max=real(pm,c_double)
    t_max=real(tm,c_double);t_out=real(to,c_double);deform_max=real(dm,c_double);iterations=int(it,c_int)
    rb_plain_journal_multiphysics_c=int(st,c_int)
  end function rb_plain_journal_multiphysics_c


  integer(c_int) function rb_tilting_pad_multiphysics_c(speed,omega,weight,fxs_load,fys_load,d,cb,mu1,mu2,t1,t2,rho,cp,klube, &
      thermal_type,deform_type,pad_thickness,pad_density,kpad,epad,nupad,alphapad,temp_supply,temp_journal,temp_ambient, &
      convec_edges,convec_back,n_pads,pivot_angle,pad_arc,pad_axial_length,preload,offset,k_rotate,total_e_x,total_e_z, &
      total_e_y_pad,total_e_y_film,xj_ratio_initial,yj_ratio_initial,relax_p,relax_t,max_iterations,outer_iterations, &
      force_tolerance,field_tolerance,xj_ratio,yj_ratio,tilt_angle,k_out,c_out,fx_hydro,fy_hydro,p_max,t_max,t_out, &
      deform_max,iterations) bind(C,name="rb_tilting_pad_multiphysics_c")
    real(c_double),value::speed,omega,weight,fxs_load,fys_load,d,cb,mu1,mu2,t1,t2,rho,cp,klube
    integer(c_int),value::thermal_type,deform_type
    real(c_double),value::pad_thickness,pad_density,kpad,epad,nupad,alphapad,temp_supply,temp_journal,temp_ambient
    real(c_double),value::convec_edges,convec_back
    integer(c_int),value::n_pads,total_e_x,total_e_z,total_e_y_pad,total_e_y_film
    real(c_double),intent(in)::pivot_angle(*),pad_arc(*),pad_axial_length(*),preload(*),offset(*),k_rotate(*)
    real(c_double),value::xj_ratio_initial,yj_ratio_initial,relax_p,relax_t,force_tolerance,field_tolerance
    integer(c_int),value::max_iterations,outer_iterations
    real(c_double),intent(out)::xj_ratio,yj_ratio,tilt_angle(*),k_out(4),c_out(4)
    real(c_double),intent(out)::fx_hydro,fy_hydro,p_max,t_max,t_out,deform_max
    integer(c_int),intent(out)::iterations
    real(rk),allocatable::piv(:),arc(:),alen(:),pre(:),off(:),krot(:),tilt(:)
    real(rk)::xr,yr,k(2,2),cc(2,2),fx,fy,pm,tm,to,dm
    integer(ik)::st,it
    integer::n
    n=int(n_pads)
    if(n<1)then
      rb_tilting_pad_multiphysics_c=int(RB_ERR_INPUT,c_int);iterations=0_c_int;return
    end if
    allocate(piv(n),arc(n),alen(n),pre(n),off(n),krot(n),tilt(n))
    piv=real(pivot_angle(1:n),rk);arc=real(pad_arc(1:n),rk);alen=real(pad_axial_length(1:n),rk)
    pre=real(preload(1:n),rk);off=real(offset(1:n),rk);krot=real(k_rotate(1:n),rk)
    call rb_tilting_pad_multiphysics(real(speed,rk),real(omega,rk),real(weight,rk),real(fxs_load,rk),real(fys_load,rk), &
      real(d,rk),real(cb,rk),real(mu1,rk),real(mu2,rk),real(t1,rk),real(t2,rk),real(rho,rk),real(cp,rk),real(klube,rk), &
      int(thermal_type,ik),int(deform_type,ik),real(pad_thickness,rk),real(pad_density,rk),real(kpad,rk),real(epad,rk), &
      real(nupad,rk),real(alphapad,rk),real(temp_supply,rk),real(temp_journal,rk),real(temp_ambient,rk), &
      real(convec_edges,rk),real(convec_back,rk),int(n_pads,ik),piv,arc,alen,pre,off,krot,int(total_e_x,ik), &
      int(total_e_z,ik),int(total_e_y_pad,ik),int(total_e_y_film,ik),real(xj_ratio_initial,rk),real(yj_ratio_initial,rk), &
      real(relax_p,rk),real(relax_t,rk),int(max_iterations,ik),int(outer_iterations,ik),real(force_tolerance,rk), &
      real(field_tolerance,rk),xr,yr,tilt,k,cc,fx,fy,pm,tm,to,dm,it,st)
    xj_ratio=real(xr,c_double);yj_ratio=real(yr,c_double);tilt_angle(1:n)=real(tilt,c_double)
    k_out=[real(k(1,1),c_double),real(k(2,1),c_double),real(k(1,2),c_double),real(k(2,2),c_double)]
    c_out=[real(cc(1,1),c_double),real(cc(2,1),c_double),real(cc(1,2),c_double),real(cc(2,2),c_double)]
    fx_hydro=real(fx,c_double);fy_hydro=real(fy,c_double);p_max=real(pm,c_double)
    t_max=real(tm,c_double);t_out=real(to,c_double);deform_max=real(dm,c_double);iterations=int(it,c_int)
    rb_tilting_pad_multiphysics_c=int(st,c_int)
  end function rb_tilting_pad_multiphysics_c


  integer(c_int) function rb_plain_journal_multiphysics_pack_c(n_pads, rcfg, icfg, pivot_angle, pad_arc, pad_axial_length, &
      preload, offset, k_out, c_out, summary) bind(C,name="rb_plain_journal_multiphysics_pack_c")
    integer(c_int),value::n_pads
    real(c_double),intent(in)::rcfg(*),pivot_angle(*),pad_arc(*),pad_axial_length(*),preload(*),offset(*)
    integer(c_int),intent(in)::icfg(*)
    real(c_double),intent(out)::k_out(4),c_out(4),summary(9)
    real(rk),allocatable::piv(:),arc(:),alen(:),pre(:),off(:)
    real(rk)::xr,yr,k(2,2),cc(2,2),fx,fy,pm,tm,to,dm
    integer(ik)::st,it
    integer::n
    n=int(n_pads)
    if(n<1)then;rb_plain_journal_multiphysics_pack_c=int(RB_ERR_INPUT,c_int);summary=0._c_double;return;end if
    allocate(piv(n),arc(n),alen(n),pre(n),off(n))
    piv=real(pivot_angle(1:n),rk);arc=real(pad_arc(1:n),rk);alen=real(pad_axial_length(1:n),rk)
    pre=real(preload(1:n),rk);off=real(offset(1:n),rk)
    call rb_plain_journal_multiphysics(real(rcfg(1),rk),real(rcfg(2),rk),real(rcfg(3),rk),real(rcfg(4),rk), &
      real(rcfg(5),rk),real(rcfg(6),rk),real(rcfg(7),rk),real(rcfg(8),rk),real(rcfg(9),rk),real(rcfg(10),rk), &
      real(rcfg(11),rk),real(rcfg(12),rk),real(rcfg(13),rk),int(icfg(1),ik),int(icfg(2),ik),real(rcfg(14),rk), &
      real(rcfg(15),rk),real(rcfg(16),rk),real(rcfg(17),rk),real(rcfg(18),rk),real(rcfg(19),rk),real(rcfg(20),rk), &
      real(rcfg(21),rk),real(rcfg(22),rk),real(rcfg(23),rk),int(n_pads,ik),piv,arc,alen,pre,off,int(icfg(3),ik), &
      int(icfg(4),ik),int(icfg(5),ik),int(icfg(6),ik),real(rcfg(24),rk),real(rcfg(25),rk),real(rcfg(26),rk), &
      real(rcfg(27),rk),int(icfg(7),ik),int(icfg(8),ik),real(rcfg(28),rk),real(rcfg(29),rk),xr,yr,k,cc,fx,fy,pm,tm,to,dm,it,st,temp_reference_in=real(rcfg(30),rk), &
      ambient_press1_in=real(rcfg(31),rk),ambient_press2_in=real(rcfg(32),rk),hotoil_lamda_in=real(rcfg(33),rk))
    k_out=[real(k(1,1),c_double),real(k(2,1),c_double),real(k(1,2),c_double),real(k(2,2),c_double)]
    c_out=[real(cc(1,1),c_double),real(cc(2,1),c_double),real(cc(1,2),c_double),real(cc(2,2),c_double)]
    summary=[real(xr,c_double),real(yr,c_double),real(fx,c_double),real(fy,c_double),real(pm,c_double), &
             real(tm,c_double),real(to,c_double),real(dm,c_double),real(it,c_double)]
    rb_plain_journal_multiphysics_pack_c=int(st,c_int)
  end function rb_plain_journal_multiphysics_pack_c

  integer(c_int) function rb_tilting_pad_multiphysics_pack_c(n_pads, rcfg, icfg, pivot_angle, pad_arc, pad_axial_length, &
      preload, offset, k_rotate, tilt_angle, k_out, c_out, summary) bind(C,name="rb_tilting_pad_multiphysics_pack_c")
    integer(c_int),value::n_pads
    real(c_double),intent(in)::rcfg(*),pivot_angle(*),pad_arc(*),pad_axial_length(*),preload(*),offset(*),k_rotate(*)
    integer(c_int),intent(in)::icfg(*)
    real(c_double),intent(out)::tilt_angle(*),k_out(4),c_out(4),summary(9)
    real(rk),allocatable::piv(:),arc(:),alen(:),pre(:),off(:),krot(:),tilt(:)
    real(rk)::xr,yr,k(2,2),cc(2,2),fx,fy,pm,tm,to,dm
    integer(ik)::st,it
    integer::n
    n=int(n_pads)
    if(n<1)then;rb_tilting_pad_multiphysics_pack_c=int(RB_ERR_INPUT,c_int);summary=0._c_double;return;end if
    allocate(piv(n),arc(n),alen(n),pre(n),off(n),krot(n),tilt(n))
    piv=real(pivot_angle(1:n),rk);arc=real(pad_arc(1:n),rk);alen=real(pad_axial_length(1:n),rk)
    pre=real(preload(1:n),rk);off=real(offset(1:n),rk);krot=real(k_rotate(1:n),rk)
    call rb_tilting_pad_multiphysics(real(rcfg(1),rk),real(rcfg(2),rk),real(rcfg(3),rk),real(rcfg(4),rk), &
      real(rcfg(5),rk),real(rcfg(6),rk),real(rcfg(7),rk),real(rcfg(8),rk),real(rcfg(9),rk),real(rcfg(10),rk), &
      real(rcfg(11),rk),real(rcfg(12),rk),real(rcfg(13),rk),real(rcfg(14),rk),int(icfg(1),ik),int(icfg(2),ik), &
      real(rcfg(15),rk),real(rcfg(16),rk),real(rcfg(17),rk),real(rcfg(18),rk),real(rcfg(19),rk),real(rcfg(20),rk), &
      real(rcfg(21),rk),real(rcfg(22),rk),real(rcfg(23),rk),real(rcfg(24),rk),real(rcfg(25),rk),int(n_pads,ik), &
      piv,arc,alen,pre,off,krot,int(icfg(3),ik),int(icfg(4),ik),int(icfg(5),ik),int(icfg(6),ik),real(rcfg(26),rk), &
      real(rcfg(27),rk),real(rcfg(28),rk),real(rcfg(29),rk),int(icfg(7),ik),int(icfg(8),ik),real(rcfg(30),rk), &
      real(rcfg(31),rk),xr,yr,tilt,k,cc,fx,fy,pm,tm,to,dm,it,st,temp_reference_in=real(rcfg(32),rk), &
      ambient_press1_in=real(rcfg(33),rk),ambient_press2_in=real(rcfg(34),rk),hotoil_lamda_in=real(rcfg(35),rk))
    tilt_angle(1:n)=real(tilt,c_double)
    k_out=[real(k(1,1),c_double),real(k(2,1),c_double),real(k(1,2),c_double),real(k(2,2),c_double)]
    c_out=[real(cc(1,1),c_double),real(cc(2,1),c_double),real(cc(1,2),c_double),real(cc(2,2),c_double)]
    summary=[real(xr,c_double),real(yr,c_double),real(fx,c_double),real(fy,c_double),real(pm,c_double), &
             real(tm,c_double),real(to,c_double),real(dm,c_double),real(it,c_double)]
    rb_tilting_pad_multiphysics_pack_c=int(st,c_int)
  end function rb_tilting_pad_multiphysics_pack_c


  integer(c_int) function rb_plain_journal_multiphysics_fields_pack_c(n_pads, rcfg, icfg, pivot_angle, pad_arc, &
      pad_axial_length, preload, offset, k_out, c_out, summary, pressure_out, temperature_out, deformation_out) &
      bind(C,name="rb_plain_journal_multiphysics_fields_pack_c")
    integer(c_int),value::n_pads
    real(c_double),intent(in)::rcfg(*),pivot_angle(*),pad_arc(*),pad_axial_length(*),preload(*),offset(*)
    integer(c_int),intent(in)::icfg(*)
    real(c_double),intent(out)::k_out(4),c_out(4),summary(9),pressure_out(*),temperature_out(*),deformation_out(*)
    real(rk),allocatable::piv(:),arc(:),alen(:),pre(:),off(:),pf(:,:),tf(:,:),df(:,:)
    real(rk)::xr,yr,k(2,2),cc(2,2),fx,fy,pm,tm,to,dm
    integer(ik)::st,it
    integer::n,nn,nx,nz,p,i,idx
    n=int(n_pads)
    if(n<1)then
      rb_plain_journal_multiphysics_fields_pack_c=int(RB_ERR_INPUT,c_int);summary=0._c_double;return
    end if
    nx=int(icfg(3));nz=int(icfg(4));nn=(nx+1)*(nz+1)
    allocate(piv(n),arc(n),alen(n),pre(n),off(n),pf(nn,n),tf(nn,n),df(nx+1,n))
    piv=real(pivot_angle(1:n),rk);arc=real(pad_arc(1:n),rk);alen=real(pad_axial_length(1:n),rk)
    pre=real(preload(1:n),rk);off=real(offset(1:n),rk)
    pf=0._rk;tf=0._rk;df=0._rk
    call rb_plain_journal_multiphysics(real(rcfg(1),rk),real(rcfg(2),rk),real(rcfg(3),rk),real(rcfg(4),rk), &
      real(rcfg(5),rk),real(rcfg(6),rk),real(rcfg(7),rk),real(rcfg(8),rk),real(rcfg(9),rk),real(rcfg(10),rk), &
      real(rcfg(11),rk),real(rcfg(12),rk),real(rcfg(13),rk),int(icfg(1),ik),int(icfg(2),ik),real(rcfg(14),rk), &
      real(rcfg(15),rk),real(rcfg(16),rk),real(rcfg(17),rk),real(rcfg(18),rk),real(rcfg(19),rk),real(rcfg(20),rk), &
      real(rcfg(21),rk),real(rcfg(22),rk),real(rcfg(23),rk),int(n_pads,ik),piv,arc,alen,pre,off,int(icfg(3),ik), &
      int(icfg(4),ik),int(icfg(5),ik),int(icfg(6),ik),real(rcfg(24),rk),real(rcfg(25),rk),real(rcfg(26),rk), &
      real(rcfg(27),rk),int(icfg(7),ik),int(icfg(8),ik),real(rcfg(28),rk),real(rcfg(29),rk),xr,yr,k,cc,fx,fy,pm,tm,to,dm,it,st, &
      pf,tf,df,temp_reference_in=real(rcfg(30),rk),ambient_press1_in=real(rcfg(31),rk), &
      ambient_press2_in=real(rcfg(32),rk))
    k_out=[real(k(1,1),c_double),real(k(2,1),c_double),real(k(1,2),c_double),real(k(2,2),c_double)]
    c_out=[real(cc(1,1),c_double),real(cc(2,1),c_double),real(cc(1,2),c_double),real(cc(2,2),c_double)]
    summary=[real(xr,c_double),real(yr,c_double),real(fx,c_double),real(fy,c_double),real(pm,c_double), &
             real(tm,c_double),real(to,c_double),real(dm,c_double),real(it,c_double)]
    idx=0
    do p=1,n
      do i=1,nn
        idx=idx+1;pressure_out(idx)=real(pf(i,p),c_double);temperature_out(idx)=real(tf(i,p),c_double)
      end do
    end do
    idx=0
    do p=1,n
      do i=1,nx+1
        idx=idx+1;deformation_out(idx)=real(df(i,p),c_double)
      end do
    end do
    rb_plain_journal_multiphysics_fields_pack_c=int(st,c_int)
  end function rb_plain_journal_multiphysics_fields_pack_c


  integer(c_int) function rb_tilting_pad_multiphysics_fields_pack_c(n_pads, rcfg, icfg, pivot_angle, pad_arc, &
      pad_axial_length, preload, offset, k_rotate, tilt_angle, k_out, c_out, summary, pressure_out, temperature_out, &
      deformation_out) bind(C,name="rb_tilting_pad_multiphysics_fields_pack_c")
    integer(c_int),value::n_pads
    real(c_double),intent(in)::rcfg(*),pivot_angle(*),pad_arc(*),pad_axial_length(*),preload(*),offset(*),k_rotate(*)
    integer(c_int),intent(in)::icfg(*)
    real(c_double),intent(out)::tilt_angle(*),k_out(4),c_out(4),summary(9),pressure_out(*),temperature_out(*),deformation_out(*)
    real(rk),allocatable::piv(:),arc(:),alen(:),pre(:),off(:),krot(:),tilt(:),pf(:,:),tf(:,:),df(:,:)
    real(rk)::xr,yr,k(2,2),cc(2,2),fx,fy,pm,tm,to,dm
    integer(ik)::st,it
    integer::n,nn,nx,nz,p,i,idx
    n=int(n_pads)
    if(n<1)then
      rb_tilting_pad_multiphysics_fields_pack_c=int(RB_ERR_INPUT,c_int);summary=0._c_double;return
    end if
    nx=int(icfg(3));nz=int(icfg(4));nn=(nx+1)*(nz+1)
    allocate(piv(n),arc(n),alen(n),pre(n),off(n),krot(n),tilt(n),pf(nn,n),tf(nn,n),df(nx+1,n))
    piv=real(pivot_angle(1:n),rk);arc=real(pad_arc(1:n),rk);alen=real(pad_axial_length(1:n),rk)
    pre=real(preload(1:n),rk);off=real(offset(1:n),rk);krot=real(k_rotate(1:n),rk)
    pf=0._rk;tf=0._rk;df=0._rk
    call rb_tilting_pad_multiphysics(real(rcfg(1),rk),real(rcfg(2),rk),real(rcfg(3),rk),real(rcfg(4),rk), &
      real(rcfg(5),rk),real(rcfg(6),rk),real(rcfg(7),rk),real(rcfg(8),rk),real(rcfg(9),rk),real(rcfg(10),rk), &
      real(rcfg(11),rk),real(rcfg(12),rk),real(rcfg(13),rk),real(rcfg(14),rk),int(icfg(1),ik),int(icfg(2),ik), &
      real(rcfg(15),rk),real(rcfg(16),rk),real(rcfg(17),rk),real(rcfg(18),rk),real(rcfg(19),rk),real(rcfg(20),rk), &
      real(rcfg(21),rk),real(rcfg(22),rk),real(rcfg(23),rk),real(rcfg(24),rk),real(rcfg(25),rk),int(n_pads,ik), &
      piv,arc,alen,pre,off,krot,int(icfg(3),ik),int(icfg(4),ik),int(icfg(5),ik),int(icfg(6),ik),real(rcfg(26),rk), &
      real(rcfg(27),rk),real(rcfg(28),rk),real(rcfg(29),rk),int(icfg(7),ik),int(icfg(8),ik),real(rcfg(30),rk), &
      real(rcfg(31),rk),xr,yr,tilt,k,cc,fx,fy,pm,tm,to,dm,it,st,pf,tf,df,temp_reference_in=real(rcfg(32),rk), &
      ambient_press1_in=real(rcfg(33),rk),ambient_press2_in=real(rcfg(34),rk))
    tilt_angle(1:n)=real(tilt,c_double)
    k_out=[real(k(1,1),c_double),real(k(2,1),c_double),real(k(1,2),c_double),real(k(2,2),c_double)]
    c_out=[real(cc(1,1),c_double),real(cc(2,1),c_double),real(cc(1,2),c_double),real(cc(2,2),c_double)]
    summary=[real(xr,c_double),real(yr,c_double),real(fx,c_double),real(fy,c_double),real(pm,c_double), &
             real(tm,c_double),real(to,c_double),real(dm,c_double),real(it,c_double)]
    idx=0
    do p=1,n
      do i=1,nn
        idx=idx+1;pressure_out(idx)=real(pf(i,p),c_double);temperature_out(idx)=real(tf(i,p),c_double)
      end do
    end do
    idx=0
    do p=1,n
      do i=1,nx+1
        idx=idx+1;deformation_out(idx)=real(df(i,p),c_double)
      end do
    end do
    rb_tilting_pad_multiphysics_fields_pack_c=int(st,c_int)
  end function rb_tilting_pad_multiphysics_fields_pack_c


  integer(c_int) function rb_plain_journal_fixed_state_pack_c(n_pads,rcfg,icfg,pivot_angle,pad_arc,pad_axial_length, &
      preload,offset,k_out,summary,pressure_out) bind(C,name="rb_plain_journal_fixed_state_pack_c")
    integer(c_int),value::n_pads
    real(c_double),intent(in)::rcfg(*),pivot_angle(*),pad_arc(*),pad_axial_length(*),preload(*),offset(*)
    integer(c_int),intent(in)::icfg(*)
    real(c_double),intent(out)::k_out(4),summary(3),pressure_out(*)
    real(rk),allocatable::piv(:),arc(:),alen(:),pre(:),off(:),pf(:,:)
    real(rk)::k(2,2),fx,fy,pm
    integer(ik)::st
    integer::n,nx,nz,nn,p,i,idx
    n=int(n_pads);nx=int(icfg(1));nz=int(icfg(2));nn=(nx+1)*(nz+1)
    if(n<1 .or. nx<2 .or. nz<2)then
      rb_plain_journal_fixed_state_pack_c=int(RB_ERR_INPUT,c_int);summary=0._c_double;return
    end if
    allocate(piv(n),arc(n),alen(n),pre(n),off(n),pf(nn,n))
    piv=real(pivot_angle(1:n),rk);arc=real(pad_arc(1:n),rk);alen=real(pad_axial_length(1:n),rk)
    pre=real(preload(1:n),rk);off=real(offset(1:n),rk)
    call rb_plain_journal_fixed_state(real(rcfg(1),rk),real(rcfg(2),rk),real(rcfg(3),rk),real(rcfg(4),rk), &
      int(n_pads,ik),piv,arc,alen,pre,off,int(icfg(1),ik),int(icfg(2),ik),real(rcfg(5),rk),real(rcfg(6),rk), &
      pf,fx,fy,pm,k,st)
    k_out=[real(k(1,1),c_double),real(k(2,1),c_double),real(k(1,2),c_double),real(k(2,2),c_double)]
    summary=[real(fx,c_double),real(fy,c_double),real(pm,c_double)]
    idx=0
    do p=1,n
      do i=1,nn
        idx=idx+1;pressure_out(idx)=real(pf(i,p),c_double)
      end do
    end do
    rb_plain_journal_fixed_state_pack_c=int(st,c_int)
  end function rb_plain_journal_fixed_state_pack_c

end module rb_c_api
