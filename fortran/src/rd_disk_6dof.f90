! SPDX-License-Identifier: Apache-2.0
! ROSS-derived formulas: Copyright 2022 Petroleo Brasileiro S.A.
! Native translation for RotorStudio B1, 2026. See validation/b1/NATIVE.md.
! Authority: petrobras/ross@6320eab9f890f1b3cc1710d508b446fe063ca68d
! disk_element.py DiskElement.M/G/Kdt. Isolated rigid disk, not PointMass.
module rd_disk_6dof
  use iso_c_binding, only: c_double,c_int
  use, intrinsic :: ieee_arithmetic, only: ieee_is_finite
  use rd_shaft_6dof, only: B1_OK,B1_INVALID_INPUT
  implicit none(type, external)
  private
  public :: disk_6dof_matrices
contains
  subroutine disk_6dof_matrices(m,Id,Ip,Mo,Go,Ko,status)
    real(c_double), intent(in) :: m,Id,Ip
    real(c_double), intent(inout) :: Mo(6,6),Go(6,6),Ko(6,6)
    integer(c_int), intent(out) :: status
    real(c_double) :: Mx(6,6),Gx(6,6),Kx(6,6)
    integer :: i
    status=B1_INVALID_INPUT
    if (.not.all(ieee_is_finite([m,Id,Ip]))) return
    ! Declared B1 scope is a nondegenerate rigid disk. Zero inertia is rejected;
    ! accepting such a limit would not qualify PointMass and is not implied here.
    if (m<=0 .or. Id<=0 .or. Ip<=0) return
    Mx=0; Gx=0; Kx=0
    do i=1,3
      Mx(i,i)=m
    end do
    Mx(4,4)=Id; Mx(5,5)=Id; Mx(6,6)=Ip
    Gx(4,5)=Ip; Gx(5,4)=-Ip
    Kx(5,4)=Ip
    ! Kdt(4,5) is zero: there is no mirrored acceleration term.
    Mo=Mx; Go=Gx; Ko=Kx
    status=B1_OK
  end subroutine
end module rd_disk_6dof
