module rd_eigensystem
  use rd_kinds, only: rk, ik
  use rd_status, only: RD_OK
  use rd_lapack, only: solve_real, eig_real
  implicit none(type, external)
  private
  public :: stationary_eigs, stationary_eigensystem
contains
  subroutine stationary_eigs(M,C,K,wr,wi,status)
    real(rk),intent(in) :: M(:,:),C(:,:),K(:,:)
    real(rk),intent(out) :: wr(:),wi(:)
    integer(ik),intent(out) :: status
    complex(rk),allocatable :: w(:),u(:,:)
    integer :: i,n
    n=size(M,1)
    allocate(w(2*n),u(n,2*n))
    call stationary_eigensystem(M,C,K,w,u,status)
    if (status/=RD_OK) return
    do i=1,2*n
      wr(i)=real(w(i),rk)
      wi(i)=aimag(w(i))
    end do
  end subroutine stationary_eigs

  subroutine stationary_eigensystem(M,C,K,w,u,status)
    real(rk),intent(in) :: M(:,:),C(:,:),K(:,:)
    complex(rk),intent(out) :: w(:),u(:,:)
    integer(ik),intent(out) :: status
    integer :: n,i,j
    real(rk),allocatable :: Awork(:,:),XK(:,:),XC(:,:),wr(:),wi(:),vr(:,:)
    complex(rk),allocatable :: vstate(:,:)

    n=size(M,1)
    allocate(XK(n,n),XC(n,n),Awork(n,n))
    XK=M; XC=M
    Awork=K
    call solve_real(XK,Awork,status)
    if (status/=RD_OK) return
    XK=Awork
    Awork=C
    call solve_real(XC,Awork,status)
    if (status/=RD_OK) return
    XC=Awork

    deallocate(Awork)
    allocate(Awork(2*n,2*n),wr(2*n),wi(2*n),vr(2*n,2*n),vstate(2*n,2*n))
    Awork=0._rk
    do i=1,n
      Awork(i,n+i)=1._rk
    end do
    Awork(n+1:2*n,1:n)=-XK
    Awork(n+1:2*n,n+1:2*n)=-XC
    call eig_real(Awork,wr,wi,vr,status)
    if (status/=RD_OK) return

    ! Reconstruct complex eigenvectors from LAPACK DGEEV's real storage.
    j=1
    do while (j<=2*n)
      if (wi(j)>0._rk .and. j<2*n) then
        w(j)=cmplx(wr(j),wi(j),rk)
        w(j+1)=cmplx(wr(j+1),wi(j+1),rk)
        vstate(:,j)=cmplx(vr(:,j),vr(:,j+1),rk)
        vstate(:,j+1)=conjg(vstate(:,j))
        j=j+2
      else if (wi(j)<0._rk .and. j>1) then
        ! Normally consumed together with the preceding positive-imaginary root.
        w(j)=cmplx(wr(j),wi(j),rk)
        if (all(abs(vstate(:,j))==0._rk)) vstate(:,j)=cmplx(vr(:,j),0._rk,rk)
        j=j+1
      else
        w(j)=cmplx(wr(j),wi(j),rk)
        vstate(:,j)=cmplx(vr(:,j),0._rk,rk)
        j=j+1
      end if
    end do

    call matlab_complex_sort_with_vectors(w,vstate)
    u=vstate(1:n,:)
  end subroutine stationary_eigensystem

  subroutine matlab_complex_sort_with_vectors(w,v)
    complex(rk),intent(inout) :: w(:),v(:,:)
    integer :: i,j
    complex(rk) :: tmp
    complex(rk),allocatable :: vtmp(:)
    real(rk) :: mi,mj,ai,aj
    allocate(vtmp(size(v,1)))
    do i=1,size(w)-1
      do j=i+1,size(w)
        mi=abs(w(i)); mj=abs(w(j))
        ai=atan2(aimag(w(i)),real(w(i),rk)); aj=atan2(aimag(w(j)),real(w(j),rk))
        if (mj<mi .or. (abs(mj-mi)<=epsilon(1._rk)*max(1._rk,mi) .and. aj<ai)) then
          tmp=w(i); w(i)=w(j); w(j)=tmp
          vtmp=v(:,i); v(:,i)=v(:,j); v(:,j)=vtmp
        end if
      end do
    end do
  end subroutine matlab_complex_sort_with_vectors
end module rd_eigensystem
