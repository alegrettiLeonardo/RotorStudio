module rb_status
  use rb_kinds, only: ik
  implicit none(type, external)
  integer(ik), parameter :: RB_OK = 0_ik
  integer(ik), parameter :: RB_ERR_INPUT = 1_ik
  integer(ik), parameter :: RB_ERR_UNSUPPORTED = 2_ik
  integer(ik), parameter :: RB_ERR_CONVERGENCE = 3_ik
  integer(ik), parameter :: RB_ERR_CANCELLED = 4_ik
end module rb_status
