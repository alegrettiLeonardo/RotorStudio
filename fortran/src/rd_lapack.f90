module rd_lapack
  use rd_kinds, only: rk, ik
  use rd_status, only: RD_OK, RD_ERR_LAPACK
  implicit none(type, external)
  private
  public :: solve_real, solve_complex, eig_real, eig_complex

  interface
    subroutine dgesv(n,nrhs,a,lda,ipiv,b,ldb,info)
      import rk
      integer :: n,nrhs,lda,ldb,info,ipiv(*)
      real(rk) :: a(lda,*),b(ldb,*)
    end subroutine dgesv
    subroutine zgesv(n,nrhs,a,lda,ipiv,b,ldb,info)
      import rk
      integer :: n,nrhs,lda,ldb,info,ipiv(*)
      complex(rk) :: a(lda,*),b(ldb,*)
    end subroutine zgesv
    subroutine dgeev(jobvl,jobvr,n,a,lda,wr,wi,vl,ldvl,vr,ldvr,work,lwork,info)
      import rk
      character :: jobvl,jobvr
      integer :: n,lda,ldvl,ldvr,lwork,info
      real(rk) :: a(lda,*),wr(*),wi(*),vl(ldvl,*),vr(ldvr,*),work(*)
    end subroutine dgeev
    subroutine zgeev(jobvl,jobvr,n,a,lda,w,vl,ldvl,vr,ldvr,work,lwork,rwork,info)
      import rk
      character :: jobvl,jobvr
      integer :: n,lda,ldvl,ldvr,lwork,info
      complex(rk) :: a(lda,*),w(*),vl(ldvl,*),vr(ldvr,*),work(*)
      real(rk) :: rwork(*)
    end subroutine zgeev
  end interface
contains
  subroutine solve_real(A,B,status)
    real(rk),intent(inout) :: A(:,:),B(:,:)
    integer(ik),intent(out) :: status
    integer :: n,nrhs,info
    integer,allocatable :: ipiv(:)
    n=size(A,1); nrhs=size(B,2)
    allocate(ipiv(n))
    call dgesv(n,nrhs,A,n,ipiv,B,n,info)
    status=merge(RD_OK,RD_ERR_LAPACK,info==0)
  end subroutine solve_real

  subroutine solve_complex(A,B,status)
    complex(rk),intent(inout) :: A(:,:),B(:,:)
    integer(ik),intent(out) :: status
    integer :: n,nrhs,info
    integer,allocatable :: ipiv(:)
    n=size(A,1); nrhs=size(B,2)
    allocate(ipiv(n))
    call zgesv(n,nrhs,A,n,ipiv,B,n,info)
    status=merge(RD_OK,RD_ERR_LAPACK,info==0)
  end subroutine solve_complex

  subroutine eig_real(A,wr,wi,vr,status)
    real(rk),intent(inout) :: A(:,:)
    real(rk),intent(out) :: wr(:),wi(:),vr(:,:)
    integer(ik),intent(out) :: status
    integer :: n,info,lwork
    real(rk),allocatable :: work(:)
    real(rk) :: vl(1,1)
    n=size(A,1); lwork=max(1,8*n)
    allocate(work(lwork))
    call dgeev('N','V',n,A,n,wr,wi,vl,1,vr,n,work,lwork,info)
    status=merge(RD_OK,RD_ERR_LAPACK,info==0)
  end subroutine eig_real

  subroutine eig_complex(A,w,vr,status)
    complex(rk),intent(inout) :: A(:,:)
    complex(rk),intent(out) :: w(:),vr(:,:)
    integer(ik),intent(out) :: status
    integer :: n,info,lwork
    complex(rk),allocatable :: work(:)
    complex(rk) :: vl(1,1)
    real(rk),allocatable :: rwork(:)
    n=size(A,1); lwork=max(1,4*n)
    allocate(work(lwork),rwork(max(1,2*n)))
    call zgeev('N','V',n,A,n,w,vl,1,vr,n,work,lwork,rwork,info)
    status=merge(RD_OK,RD_ERR_LAPACK,info==0)
  end subroutine eig_complex
end module rd_lapack
