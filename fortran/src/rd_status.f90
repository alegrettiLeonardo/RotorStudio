module rd_status
  use rd_kinds, only: ik
  implicit none(type, external)
  private
  integer(ik), parameter, public :: RD_OK=0, RD_ERR_INPUT=10, RD_ERR_UNSUPPORTED=20, RD_ERR_LAPACK=30
end module rd_status
