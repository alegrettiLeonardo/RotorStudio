module rd_irdin_support_c_api
  use iso_c_binding, only: c_double, c_int, c_int64_t
  use rd_irdin_support, only: irdin_support_matrices, I4_OK, I4_INVALID_DIMENSION, I4_INSUFFICIENT_CAPACITY
  implicit none(type, external)
  private
  public :: rd_irdin_support_matrices_v1
contains
  function rd_irdin_support_matrices_v1(support_mass,kb_in,cb_in,ks_in,cs_in, &
      m_out,ldm,capm,c_out,ldc,capc,k_out,ldk,capk) &
      bind(C,name="rd_irdin_support_matrices_v1") result(status)
    real(c_double), value, intent(in) :: support_mass
    real(c_double), intent(in) :: kb_in(*),cb_in(*),ks_in(*),cs_in(*)
    real(c_double), intent(inout) :: m_out(*),c_out(*),k_out(*)
    integer(c_int), value, intent(in) :: ldm,capm,ldc,capc,ldk,capk
    integer(c_int) :: status
    real(c_double) :: kb(2,2),cb(2,2),ks(2,2),cs(2,2),m(4,4),c(4,4),k(4,4)
    integer :: i,j
    integer(c_int64_t) :: off
    status=I4_INVALID_DIMENSION
    if (ldm<4 .or. ldc<4 .or. ldk<4) return
    status=I4_INSUFFICIENT_CAPACITY
    if (int(capm,c_int64_t)<int(3*ldm+4,c_int64_t)) return
    if (int(capc,c_int64_t)<int(3*ldc+4,c_int64_t)) return
    if (int(capk,c_int64_t)<int(3*ldk+4,c_int64_t)) return
    do j=1,2
      do i=1,2
        off=int((j-1)*2+i,c_int64_t)
        kb(i,j)=kb_in(off); cb(i,j)=cb_in(off); ks(i,j)=ks_in(off); cs(i,j)=cs_in(off)
      end do
    end do
    call irdin_support_matrices(kb,cb,ks,cs,support_mass,m,c,k,status)
    if (status/=I4_OK) return
    do j=1,4
      do i=1,4
        off=int((j-1)*ldm+i,c_int64_t); m_out(off)=m(i,j)
        off=int((j-1)*ldc+i,c_int64_t); c_out(off)=c(i,j)
        off=int((j-1)*ldk+i,c_int64_t); k_out(off)=k(i,j)
      end do
    end do
  end function
end module rd_irdin_support_c_api
