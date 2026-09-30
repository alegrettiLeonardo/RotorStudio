! SPDX-License-Identifier: Apache-2.0
! Additive RotorStudio B1 C ABI. No A1-A8 entry point or dispatch is changed.
! Buffers are borrowed, nonoverlapping caller allocations of c_double.
! For a matrix of order n: ld>=n; capacity >= (n-1)*ld+n, in doubles.
! C zero-based address: row + ld*column. Padding and tails are never written.
! Capacity is a caller declaration, NOT introspection of the actual allocation.
module rd_6dof_element_c_api
  use iso_c_binding, only: c_double,c_int,c_int64_t
  use rd_shaft_6dof, only: shaft_6dof_matrices,B1_OK,B1_INVALID_DIMENSION,B1_INSUFFICIENT_CAPACITY
  use rd_disk_6dof, only: disk_6dof_matrices
  implicit none(type, external)
  private
  public :: rd_shaft_6dof_matrices_v1,rd_disk_6dof_matrices_v1
contains
  function check_layout(n,ld,capacity) result(status)
    integer(c_int), intent(in) :: n,ld(:),capacity(:)
    integer(c_int) :: status
    integer(c_int64_t) :: required
    integer :: j
    status=B1_INVALID_DIMENSION
    if (any(ld<n)) return
    status=B1_INSUFFICIENT_CAPACITY
    do j=1,size(ld)
      required=int(n-1,c_int64_t)*int(ld(j),c_int64_t)+int(n,c_int64_t)
      if (int(capacity(j),c_int64_t)<required) return
    end do
    status=B1_OK
  end function

  subroutine copy_matrix(a,b,ld,n)
    integer(c_int), intent(in) :: ld,n
    real(c_double), intent(in) :: a(n,n)
    real(c_double), intent(inout) :: b(*)
    integer :: i,j
    integer(c_int64_t) :: offset
    do j=1,n
      offset=int(j-1,c_int64_t)*int(ld,c_int64_t)
      do i=1,n
        b(offset+i)=a(i,j)
      end do
    end do
  end subroutine

  function rd_shaft_6dof_matrices_v1(L,idl,odl,idr,odr,rho,E,Gs,F,T,shear,rotary,gyro,method, &
                                   bm,ldm,capm,bk,ldk,capk,bg,ldg,capg,bs,lds,caps) &
                                   bind(C,name='rd_shaft_6dof_matrices_v1') result(status)
    real(c_double), value, intent(in) :: L,idl,odl,idr,odr,rho,E,Gs,F,T
    integer(c_int), value, intent(in) :: shear,rotary,gyro,method
    integer(c_int), value, intent(in) :: ldm,capm,ldk,capk,ldg,capg,lds,caps
    real(c_double), intent(inout) :: bm(*),bk(*),bg(*),bs(*)
    integer(c_int) :: status
    real(c_double) :: M(12,12),K(12,12),G(12,12),S(12,12)
    status=check_layout(12_c_int,[ldm,ldk,ldg,lds],[capm,capk,capg,caps])
    if (status/=B1_OK) return
    call shaft_6dof_matrices(L,idl,odl,idr,odr,rho,E,Gs,F,T,shear,rotary,gyro,method,M,K,G,S,status)
    if (status/=B1_OK) return
    call copy_matrix(M,bm,ldm,12_c_int)
    call copy_matrix(K,bk,ldk,12_c_int)
    call copy_matrix(G,bg,ldg,12_c_int)
    call copy_matrix(S,bs,lds,12_c_int)
  end function

  function rd_disk_6dof_matrices_v1(m,Id,Ip,bm,ldm,capm,bg,ldg,capg,bk,ldk,capk) &
                                  bind(C,name='rd_disk_6dof_matrices_v1') result(status)
    real(c_double), value, intent(in) :: m,Id,Ip
    integer(c_int), value, intent(in) :: ldm,capm,ldg,capg,ldk,capk
    real(c_double), intent(inout) :: bm(*),bg(*),bk(*)
    integer(c_int) :: status
    real(c_double) :: Mx(6,6),Gx(6,6),Kx(6,6)
    status=check_layout(6_c_int,[ldm,ldg,ldk],[capm,capg,capk])
    if (status/=B1_OK) return
    call disk_6dof_matrices(m,Id,Ip,Mx,Gx,Kx,status)
    if (status/=B1_OK) return
    call copy_matrix(Mx,bm,ldm,6_c_int)
    call copy_matrix(Gx,bg,ldg,6_c_int)
    call copy_matrix(Kx,bk,ldk,6_c_int)
  end function
end module rd_6dof_element_c_api
