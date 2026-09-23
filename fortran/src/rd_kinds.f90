module rd_kinds
  use, intrinsic :: iso_fortran_env, only : real64, int32
  implicit none(type, external)
  private
  integer, parameter, public :: rk = real64
  integer, parameter, public :: ik = int32
end module rd_kinds
