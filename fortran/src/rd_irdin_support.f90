module rd_irdin_support
  use rd_kinds, only: rk, ik
  use, intrinsic :: ieee_arithmetic, only: ieee_is_finite
  implicit none(type, external)
  private
  integer(ik), parameter, public :: I4_OK=0_ik
  integer(ik), parameter, public :: I4_INVALID_INPUT=10_ik
  integer(ik), parameter, public :: I4_INVALID_DIMENSION=12_ik
  integer(ik), parameter, public :: I4_INSUFFICIENT_CAPACITY=13_ik
  integer(ik), parameter, public :: I4_NONFINITE_RESULT=14_ik
  public :: irdin_support_matrices
contains
  subroutine irdin_support_matrices(kb, cb, ks, cs, support_mass, m, c, k, status)
    real(rk), intent(in) :: kb(2,2), cb(2,2), ks(2,2), cs(2,2)
    real(rk), intent(in) :: support_mass
    real(rk), intent(out) :: m(4,4), c(4,4), k(4,4)
    integer(ik), intent(out) :: status
    status=I4_INVALID_INPUT
    if (.not. ieee_is_finite(support_mass) .or. support_mass <= 0.0_rk) return
    if (.not. all(ieee_is_finite(kb))) return
    if (.not. all(ieee_is_finite(cb))) return
    if (.not. all(ieee_is_finite(ks))) return
    if (.not. all(ieee_is_finite(cs))) return
    m=0.0_rk; c=0.0_rk; k=0.0_rk
    m(3,3)=support_mass; m(4,4)=support_mass
    k(1:2,1:2)=kb
    k(1:2,3:4)=-kb
    k(3:4,1:2)=-kb
    k(3:4,3:4)=kb+ks
    c(1:2,1:2)=cb
    c(1:2,3:4)=-cb
    c(3:4,1:2)=-cb
    c(3:4,3:4)=cb+cs
    if (.not. all(ieee_is_finite(m)) .or. .not. all(ieee_is_finite(c)) .or. .not. all(ieee_is_finite(k))) then
      status=I4_NONFINITE_RESULT
      return
    end if
    status=I4_OK
  end subroutine
end module rd_irdin_support
