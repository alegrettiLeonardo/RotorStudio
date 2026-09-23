module rd_status
  use rd_kinds, only: ik
  implicit none(type, external)
  private
  integer(ik), parameter, public :: RD_OK=0
  integer(ik), parameter, public :: RD_ERR_INPUT=10
  integer(ik), parameter, public :: RD_ERR_UNSUPPORTED=20
  integer(ik), parameter, public :: RD_ERR_LAPACK=30
  integer(ik), parameter, public :: RD_ERR_LEGACY_DEFECT=40
  integer(ik), parameter, public :: RD_ERR_CONVERGENCE=50
end module rd_status
