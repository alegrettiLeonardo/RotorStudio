module rb_reynolds_element
  use rb_kinds, only: rk, ik
  use rb_status, only: RB_OK, RB_ERR_INPUT
  implicit none(type, external)
  private

  public :: rb_reynolds_q4_element

contains

  subroutine rb_reynolds_q4_element(k_x, k_z, q, l_e, w_e, e_matrix, e_column, status)
    real(rk), intent(in) :: k_x, k_z, q, l_e, w_e
    real(rk), intent(out) :: e_matrix(4,4), e_column(4)
    integer(ik), intent(out) :: status
    real(rk) :: a11, a12, a13, a14, rhs

    e_matrix = 0._rk
    e_column = 0._rk
    status = RB_OK

    if (l_e <= 0._rk .or. w_e <= 0._rk) then
      status = RB_ERR_INPUT
      return
    end if

    ! Source-faithful Q4 Reynolds element used by current ROSS
    ! pressure.element_press / press_assemble_all_jit (Allaire stencil).
    a11 = (k_x*w_e)/(3._rk*l_e) + (k_z*l_e)/(3._rk*w_e)
    a12 = -(k_x*w_e)/(3._rk*l_e) + (k_z*l_e)/(6._rk*w_e)
    a13 = -(k_x*w_e)/(6._rk*l_e) - (k_z*l_e)/(6._rk*w_e)
    a14 = (k_x*w_e)/(6._rk*l_e) - (k_z*l_e)/(3._rk*w_e)
    rhs = q*l_e*w_e*0.25_rk

    e_matrix(1,:) = [a11,a12,a13,a14]
    e_matrix(2,:) = [a12,a11,a14,a13]
    e_matrix(3,:) = [a13,a14,a11,a12]
    e_matrix(4,:) = [a14,a13,a12,a11]
    e_column = rhs
  end subroutine rb_reynolds_q4_element

end module rb_reynolds_element
