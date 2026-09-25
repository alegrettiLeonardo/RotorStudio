program test_ross_bearings_native
  use rb_kinds, only: rk, ik
  use rb_status, only: RB_OK, RB_ERR_INPUT
  use rb_interpolation, only: rb_interp1, rb_interp2, RB_INTERP_PCHIP, RB_INTERP_LINEAR
  use rb_rolling, only: rb_ball_coefficients, rb_roller_coefficients
  use rb_cylindrical, only: rb_cylindrical_coefficients
  use rb_squeeze_film_damper, only: rb_sfd_coefficients, RB_SFD_GROOVE_END_SEALS
  use rb_fixed_geometry, only: rb_partial_arc_geometry, rb_elliptical_geometry, rb_offset_halves_geometry, &
                               rb_multi_lobe_geometry, rb_pressure_dam_geometry, rb_plain_journal_geometry
  use rb_tilting_pad_config, only: rb_tilting_pad_prepare, RB_TP_CONVENTIONAL, RB_TP_MATCH_LOAD
  use rb_reynolds_element, only: rb_reynolds_q4_element
  use rb_reynolds_banded, only: rb_lu_factor_band, rb_lu_solve_band_cavitating
  implicit none(type, external)

  integer(ik) :: st
  real(rk) :: yq, kxx, kyy, cxx, cyy
  real(rk) :: K(2,2), C(2,2), ms, som, ecc, att
  real(rk) :: k_sfd, c_sfd, theta, pmax
  real(rk), parameter :: pi_ = acos(-1._rk)

  call test_interpolation()
  call test_rolling()
  call test_cylindrical()
  call test_fixed_geometry()
  call test_tilting_pad_config()
  call test_reynolds_element()
  call test_reynolds_banded()
  call test_sfd()

  print *, 'PASS standalone ROSS bearing native gates BF1/BF2/BF3/BF4/BF5a/BF5band/BF5cfg/BF7'

contains

  logical function close_rel(a, b, rtol, atol)
    real(rk), intent(in) :: a, b, rtol, atol
    close_rel = abs(a-b) <= atol + rtol*abs(b)
  end function close_rel

  subroutine assert_close(a, b, rtol, atol, code)
    real(rk), intent(in) :: a, b, rtol, atol
    integer, intent(in) :: code
    if (.not.close_rel(a,b,rtol,atol)) then
      print *, 'assert_close failed', code, a, b, abs(a-b)
      error stop code
    end if
  end subroutine assert_close

  subroutine test_interpolation()
    real(rk) :: x2(2), y2(2)
    real(rk) :: speed(5), damping(5), v
    real(rk) :: freq(5), table(5,5)
    integer :: i, j

    x2 = [100._rk, 300._rk]
    y2 = [1.0e6_rk, 3.0e6_rk]
    call rb_interp1(2_ik, x2, y2, 200._rk, RB_INTERP_PCHIP, yq, st)
    if (st /= RB_OK) error stop 101
    call assert_close(yq, 2.0e6_rk, 1e-14_rk, 1e-9_rk, 102)

    call rb_interp1(2_ik, x2, y2, 400._rk, RB_INTERP_PCHIP, yq, st)
    if (st /= RB_OK) error stop 103
    call assert_close(yq, 4.0e6_rk, 1e-14_rk, 1e-9_rk, 104)

    speed = [100._rk, 200._rk, 300._rk, 400._rk, 500._rk]
    damping = [30._rk, 12._rk, 7._rk, 5.5_rk, 5._rk]
    do i = 1, 5
      call rb_interp1(5_ik, speed, damping, speed(i), RB_INTERP_PCHIP, v, st)
      if (st /= RB_OK) error stop 105
      call assert_close(v, damping(i), 1e-14_rk, 1e-13_rk, 106)
    end do

    ! ROSS grid interpolation is separable: speed first, then frequency.
    freq = [10._rk, 20._rk, 30._rk, 40._rk, 50._rk]
    do i = 1, 5
      do j = 1, 5
        table(i,j) = speed(i)*freq(j)
      end do
    end do

    call rb_interp2(5_ik, speed, 5_ik, freq, table, 250._rk, 25._rk, RB_INTERP_LINEAR, yq, st)
    if (st /= RB_OK) error stop 107
    call assert_close(yq, 6250._rk, 1e-14_rk, 1e-12_rk, 108)

    call rb_interp2(5_ik, speed, 5_ik, freq, table, 250._rk, 25._rk, RB_INTERP_PCHIP, yq, st)
    if (st /= RB_OK) error stop 109
    call assert_close(yq, 6250._rk, 1e-12_rk, 1e-10_rk, 110)
  end subroutine test_interpolation

  subroutine test_rolling()
    call rb_ball_coefficients(8._rk, 0.03_rk, 500._rk, pi_/6._rk, &
                              .false., 0._rk, .false., 0._rk, kxx, kyy, cxx, cyy, st)
    if (st /= RB_OK) error stop 201
    ! ROSS upstream tests use numpy.assert_allclose defaults (rtol=1e-7).
    ! Their published fixture values are rounded, so match the same oracle tolerance.
    call assert_close(kxx, 4.64168838e7_rk, 1e-7_rk, 1e-2_rk, 202)
    call assert_close(kyy, 1.00906269e8_rk, 1e-7_rk, 1e-2_rk, 203)
    call assert_close(cxx, 580.2110481_rk, 1e-7_rk, 1e-6_rk, 204)
    call assert_close(cyy, 1261.32836543_rk, 1e-7_rk, 1e-6_rk, 205)

    call rb_roller_coefficients(8._rk, 0.03_rk, 500._rk, pi_/6._rk, &
                                .false., 0._rk, .false., 0._rk, kxx, kyy, cxx, cyy, st)
    if (st /= RB_OK) error stop 206
    call assert_close(kxx, 2.72821927e8_rk, 1e-7_rk, 1e-1_rk, 207)
    call assert_close(kyy, 5.56779444e8_rk, 1e-7_rk, 1e-1_rk, 208)
    call assert_close(cxx, 3410.27409251_rk, 1e-7_rk, 1e-5_rk, 209)
    call assert_close(cyy, 6959.74304593_rk, 1e-7_rk, 1e-5_rk, 210)
  end subroutine test_rolling

  subroutine test_cylindrical()
    real(rk) :: speed

    speed = 1500._rk * 2._rk*pi_/60._rk
    call rb_cylindrical_coefficients(speed, 525._rk, 0.03_rk, 0.1_rk, 0.0001_rk, 0.1_rk, &
                                     ms, som, ecc, att, K, C, st)
    if (st /= RB_OK) error stop 301

    call assert_close(ms, 1.009798_rk, 2e-6_rk, 2e-7_rk, 302)
    call assert_close(som, 3.571429_rk, 2e-6_rk, 2e-7_rk, 303)
    call assert_close(ecc, 0.266298_rk, 2e-5_rk, 2e-7_rk, 304)
    call assert_close(att, 0.198931_rk, 2e-5_rk, 2e-7_rk, 305)

    call assert_close(K(1,1)/1e6_rk, 12.80796_rk, 2e-6_rk, 2e-5_rk, 306)
    call assert_close(K(1,2)/1e6_rk, 16.393593_rk, 2e-6_rk, 2e-5_rk, 307)
    call assert_close(K(2,1)/1e6_rk, -25.060393_rk, 2e-6_rk, 2e-5_rk, 308)
    call assert_close(K(2,2)/1e6_rk, 8.815303_rk, 2e-6_rk, 2e-5_rk, 309)

    call assert_close(C(1,1)/1e3_rk, 232.89693_rk, 2e-6_rk, 2e-5_rk, 310)
    call assert_close(C(1,2)/1e3_rk, -81.924371_rk, 2e-6_rk, 2e-5_rk, 311)
    call assert_close(C(2,1)/1e3_rk, -81.924371_rk, 2e-6_rk, 2e-5_rk, 312)
    call assert_close(C(2,2)/1e3_rk, 294.911619_rk, 2e-6_rk, 2e-5_rk, 313)

    call rb_cylindrical_coefficients(0._rk, 525._rk, 0.03_rk, 0.1_rk, 0.0001_rk, 0.1_rk, &
                                     ms, som, ecc, att, K, C, st)
    if (st /= RB_ERR_INPUT) error stop 314
  end subroutine test_cylindrical

  subroutine test_fixed_geometry()
    integer(ik) :: np
    real(rk) :: pivot2(2), arc2(2), pre2(2), off2(2)
    real(rk) :: track_arc(2), track_len(2), track_depth(2)
    real(rk) :: pre3_in(3), off3_in(3), pre3(3), off3(3), pivot3(3), arc3(3)
    real(rk) :: p1(1), a1(1), pr1(1), o1(1)
    real(rk) :: pj_pivot(4), pj_arc(4), pj_pre(4), pj_off(4), pj_len(4), pj_thick

    call rb_partial_arc_geometry(pi_/2._rk, 3._rk*pi_/2._rk, 0._rk, 0.5_rk, &
                                 np, p1, a1, pr1, o1, st)
    if (st /= RB_OK .or. np /= 1) error stop 351
    call assert_close(p1(1), 3._rk*pi_/2._rk, 1e-14_rk, 1e-14_rk, 352)

    call rb_elliptical_geometry(150._rk*pi_/180._rk, 0.5_rk, np, pivot2, arc2, pre2, off2, st)
    if (st /= RB_OK .or. np /= 2) error stop 353
    call assert_close(pivot2(1), pi_/2._rk, 1e-14_rk, 1e-14_rk, 354)
    call assert_close(pivot2(2), 3._rk*pi_/2._rk, 1e-14_rk, 1e-14_rk, 355)
    call assert_close(pre2(1), 0.5_rk, 1e-14_rk, 1e-14_rk, 356)
    call assert_close(off2(2), 0.5_rk, 1e-14_rk, 1e-14_rk, 357)

    call rb_offset_halves_geometry(150._rk*pi_/180._rk, 0.4_rk, 0.6_rk, np, &
                                   pivot2, arc2, pre2, off2, st)
    if (st /= RB_OK .or. np /= 2) error stop 358
    call assert_close(off2(1), 0.6_rk, 1e-14_rk, 1e-14_rk, 359)

    pre3_in = [0.3_rk, 0.4_rk, 0.5_rk]
    off3_in = [0.45_rk, 0.5_rk, 0.55_rk]
    call rb_multi_lobe_geometry(3_ik, 100._rk*pi_/180._rk, pre3_in, off3_in, 0._rk, .false., &
                                pivot3, arc3, pre3, off3, st)
    if (st /= RB_OK) error stop 360
    call assert_close(pivot3(1), pi_/3._rk, 1e-14_rk, 1e-14_rk, 361)
    call assert_close(pivot3(2), pi_, 1e-14_rk, 1e-14_rk, 362)
    call assert_close(pivot3(3), 5._rk*pi_/3._rk, 1e-14_rk, 1e-14_rk, 363)

    call rb_pressure_dam_geometry(150._rk*pi_/180._rk, pi_/2._rk, 0.1_rk, 250e-6_rk, &
                                  .true., .false., 0._rk, np, pivot2, arc2, pre2, off2, &
                                  track_arc, track_len, track_depth, st)
    if (st /= RB_OK .or. np /= 2) error stop 364
    call assert_close(track_arc(1), pi_/2._rk, 1e-14_rk, 1e-14_rk, 365)
    call assert_close(track_arc(2), 0._rk, 1e-14_rk, 1e-14_rk, 366)

    call rb_plain_journal_geometry(4_ik, 80._rk*pi_/180._rk, 0.1_rk, 0.05_rk, 0.2_rk, &
                                   0._rk, .false., pj_pivot, pj_arc, pj_pre, pj_off, pj_len, pj_thick, st)
    if (st /= RB_OK) error stop 367
    call assert_close(pj_pivot(1), pi_/4._rk, 1e-14_rk, 1e-14_rk, 368)
    call assert_close(pj_pivot(4), 7._rk*pi_/4._rk, 1e-14_rk, 1e-14_rk, 369)
    call assert_close(pj_thick, 0.05_rk, 1e-14_rk, 1e-14_rk, 370)
  end subroutine test_fixed_geometry

  subroutine test_tilting_pad_config()
    real(rk) :: pivot(5), arc(5), plen(5), pre(5), off(5), pos(2)

    pivot = [18._rk,90._rk,162._rk,234._rk,306._rk] * pi_/180._rk
    arc = 60._rk*pi_/180._rk
    plen = 50.8e-3_rk
    pre = 0.5_rk
    off = 0.5_rk

    call rb_tilting_pad_prepare(5_ik,101.6e-3_rk,74.9e-6_rk,12.7e-3_rk, &
                                pivot,arc,plen,pre,off,RB_TP_CONVENTIONAL,RB_TP_MATCH_LOAD, &
                                0.3_rk,3._rk*pi_/2._rk,.false.,0._rk,0._rk,20_ik,10_ik,10_ik,pos,st)
    if (st /= RB_OK) error stop 371
    call assert_close(pos(1), 0._rk, 1e-14_rk, 1e-14_rk, 372)
    call assert_close(pos(2), -0.3_rk, 1e-14_rk, 1e-14_rk, 373)

    call rb_tilting_pad_prepare(5_ik,101.6e-3_rk,74.9e-6_rk,12.7e-3_rk, &
                                pivot,arc,plen,pre,off,RB_TP_CONVENTIONAL,RB_TP_MATCH_LOAD, &
                                0.3_rk,3._rk*pi_/2._rk,.true.,0.12_rk,-0.21_rk,20_ik,10_ik,10_ik,pos,st)
    if (st /= RB_OK) error stop 374
    call assert_close(pos(1), 0.12_rk, 1e-14_rk, 1e-14_rk, 375)
    call assert_close(pos(2), -0.21_rk, 1e-14_rk, 1e-14_rk, 376)

    call rb_tilting_pad_prepare(5_ik,101.6e-3_rk,74.9e-6_rk,12.7e-3_rk, &
                                pivot,arc,plen,pre,off,RB_TP_CONVENTIONAL,RB_TP_MATCH_LOAD, &
                                0.3_rk,3._rk*pi_/2._rk,.false.,0._rk,0._rk,21_ik,10_ik,10_ik,pos,st)
    if (st /= RB_ERR_INPUT) error stop 377
  end subroutine test_tilting_pad_config

  subroutine test_reynolds_element()
    real(rk) :: em(4,4), ec(4)

    call rb_reynolds_q4_element(2._rk,3._rk,5._rk,0.4_rk,0.2_rk,em,ec,st)
    if (st /= RB_OK) error stop 381
    call assert_close(em(1,1), 7._rk/3._rk, 1e-14_rk, 1e-14_rk, 382)
    call assert_close(em(1,2), 2._rk/3._rk, 1e-14_rk, 1e-14_rk, 383)
    call assert_close(em(1,3), -7._rk/6._rk, 1e-14_rk, 1e-14_rk, 384)
    call assert_close(em(1,4), -11._rk/6._rk, 1e-14_rk, 1e-14_rk, 385)
    call assert_close(em(2,1), em(1,2), 1e-14_rk, 1e-14_rk, 386)
    call assert_close(em(4,4), em(1,1), 1e-14_rk, 1e-14_rk, 387)
    call assert_close(ec(1), 0.1_rk, 1e-14_rk, 1e-14_rk, 388)
    call assert_close(ec(4), 0.1_rk, 1e-14_rk, 1e-14_rk, 389)

    call rb_reynolds_q4_element(2._rk,3._rk,5._rk,0._rk,0.2_rk,em,ec,st)
    if (st /= RB_ERR_INPUT) error stop 390
  end subroutine test_reynolds_element

  subroutine test_reynolds_banded()
    real(rk) :: a(3,3), al(3,1), bvec(3)
    integer(ik) :: piv(3)

    ! Symmetric tridiagonal system in ROSS band storage, diagonal at column 2:
    ! [4 1 0; 1 4 1; 0 1 3] * x = [6 6 4].
    a = 0._rk
    a(1,2) = 4._rk; a(1,3) = 1._rk
    a(2,1) = 1._rk; a(2,2) = 4._rk; a(2,3) = 1._rk
    a(3,1) = 1._rk; a(3,2) = 3._rk
    bvec = [6._rk,6._rk,4._rk]

    call rb_lu_factor_band(a,3_ik,2_ik,al,piv,st)
    if (st /= RB_OK) error stop 391
    call rb_lu_solve_band_cavitating(a,3_ik,2_ik,al,piv,bvec,0._rk,st)
    if (st /= RB_OK) error stop 392
    call assert_close(bvec(1),52._rk/41._rk,1e-13_rk,1e-13_rk,393)
    call assert_close(bvec(2),38._rk/41._rk,1e-13_rk,1e-13_rk,394)
    call assert_close(bvec(3),42._rk/41._rk,1e-13_rk,1e-13_rk,395)
  end subroutine test_reynolds_banded

  subroutine test_sfd()
    real(rk), parameter :: reyn_to_pas = 6894.757293168_rk
    real(rk) :: frequency, viscosity

    frequency = 18600._rk * 2._rk*pi_/60._rk
    viscosity = 4.05640e-6_rk * reyn_to_pas

    call rb_sfd_coefficients(frequency, 0.9_rk*0.0254_rk, 5.1_rk*0.0254_rk, &
                             0.003_rk*0.0254_rk, 0.5_rk, viscosity, &
                             RB_SFD_GROOVE_END_SEALS, .true., &
                             k_sfd, c_sfd, theta, pmax, st)
    if (st /= RB_OK) error stop 401

    call assert_close(k_sfd, 1.69362187e8_rk, 1e-4_rk, 1e1_rk, 402)
    call assert_close(c_sfd, 118283.83590277865_rk, 1e-4_rk, 1e-2_rk, 403)
    call assert_close(pmax, 10248075.8971382_rk, 1e-4_rk, 1._rk, 404)
  end subroutine test_sfd

end program test_ross_bearings_native
