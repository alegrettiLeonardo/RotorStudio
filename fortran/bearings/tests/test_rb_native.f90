program test_ross_bearings_native
  use rb_kinds, only: rk, ik
  use rb_status, only: RB_OK, RB_ERR_INPUT
  use rb_interpolation, only: rb_interp1, rb_interp2, RB_INTERP_PCHIP, RB_INTERP_LINEAR
  use rb_rolling, only: rb_ball_coefficients, rb_roller_coefficients
  use rb_cylindrical, only: rb_cylindrical_coefficients
  use rb_squeeze_film_damper, only: rb_sfd_coefficients, RB_SFD_GROOVE_END_SEALS
  implicit none(type, external)

  integer(ik) :: st
  real(rk) :: yq, kxx, kyy, cxx, cyy
  real(rk) :: K(2,2), C(2,2), ms, som, ecc, att
  real(rk) :: k_sfd, c_sfd, theta, pmax
  real(rk), parameter :: pi_ = acos(-1._rk)

  call test_interpolation()
  call test_rolling()
  call test_cylindrical()
  call test_sfd()

  print *, 'PASS standalone ROSS bearing native gates BF1/BF2/BF3/BF7'

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
