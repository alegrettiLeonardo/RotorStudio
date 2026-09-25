module rb_kinds
  use, intrinsic :: iso_fortran_env, only: real64, int32
  implicit none(type, external)
  integer, parameter :: rk = real64
  integer, parameter :: ik = int32
end module rb_kinds
