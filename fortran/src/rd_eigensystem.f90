module rd_eigensystem
  use rd_kinds, only: rk,ik
  use rd_status, only: RD_OK
  use rd_lapack, only: solve_real,eig_real
  implicit none(type, external); private
  public::stationary_eigs, second_order_eigs, matlab_complex_sort, matlab_complex_sort_vectors
contains
  subroutine stationary_eigs(M,C,K,wr,wi,status)
    real(rk),intent(in)::M(:,:),C(:,:),K(:,:);real(rk),intent(out)::wr(:),wi(:);integer(ik),intent(out)::status
    integer::n,i;real(rk),allocatable::Ac(:,:),XK(:,:),XC(:,:),vr(:,:)
    n=size(M,1);allocate(Ac(n,n),XK(n,n),XC(n,n),vr(2*n,2*n)); XK=M;XC=M
    Ac=K;call solve_real(XK,Ac,status);if(status/=RD_OK)return;XK=Ac
    Ac=C;call solve_real(XC,Ac,status);if(status/=RD_OK)return;XC=Ac
    deallocate(Ac);allocate(Ac(2*n,2*n));Ac=0
    do i=1,n;Ac(i,n+i)=1;enddo
    Ac(n+1:2*n,1:n)=-XK;Ac(n+1:2*n,n+1:2*n)=-XC
    call eig_real(Ac,wr,wi,vr,status)
    if(status==RD_OK) call matlab_complex_sort(wr,wi)
  end subroutine

  subroutine second_order_eigs(M,C,K,w,Vdisp,status)
    real(rk),intent(in)::M(:,:),C(:,:),K(:,:)
    complex(rk),intent(out)::w(:),Vdisp(:,:)
    integer(ik),intent(out)::status
    integer::n,i
    real(rk),allocatable::Mr(:,:),XK(:,:),XC(:,:),A(:,:),wr(:),wi(:),vr(:,:)
    n=size(M,1)
    allocate(Mr(n,n),XK(n,n),XC(n,n),A(2*n,2*n),wr(2*n),wi(2*n),vr(2*n,2*n))
    Mr=M;XK=K
    call solve_real(Mr,XK,status);if(status/=RD_OK)return
    Mr=M;XC=C
    call solve_real(Mr,XC,status);if(status/=RD_OK)return
    A=0._rk
    do i=1,n;A(i,n+i)=1._rk;enddo
    A(n+1:2*n,1:n)=-XK;A(n+1:2*n,n+1:2*n)=-XC

    ! V2 chr_root calls EIG on this real state matrix.  Follow the same
    ! real-LAPACK path (DGEEV) and reconstruct MATLAB/Octave complex vectors
    ! from LAPACK's paired real columns instead of forcing the matrix through
    ! ZGEEV.  This matters for very nearly circular whirl orbits, where tiny
    ! cross-driver eigenvector perturbations can dominate kappa while leaving
    ! eigenvalues and MAC unchanged.
    call eig_real(A,wr,wi,vr,status);if(status/=RD_OK)return

    i=1
    do while(i<=2*n)
      if(wi(i)>0._rk .and. i<2*n)then
        w(i)=cmplx(wr(i),wi(i),rk)
        w(i+1)=cmplx(wr(i+1),wi(i+1),rk)
        Vdisp(:,i)=cmplx(vr(1:n,i),vr(1:n,i+1),rk)
        Vdisp(:,i+1)=cmplx(vr(1:n,i),-vr(1:n,i+1),rk)
        i=i+2
      else if(wi(i)<0._rk .and. i>1)then
        ! Defensive fallback for a negative-imaginary column not consumed as
        ! part of the preceding LAPACK conjugate pair.
        w(i)=cmplx(wr(i),wi(i),rk)
        Vdisp(:,i)=conjg(Vdisp(:,i-1))
        i=i+1
      else
        w(i)=cmplx(wr(i),0._rk,rk)
        Vdisp(:,i)=cmplx(vr(1:n,i),0._rk,rk)
        i=i+1
      endif
    enddo
    call matlab_complex_sort_vectors(w,Vdisp)
  end subroutine

  subroutine matlab_complex_sort(wr,wi)
    real(rk),intent(inout)::wr(:),wi(:);integer::i,j,n;real(rk)::tr,ti,mi,mj,ai,aj
    n=size(wr)
    do i=1,n-1;do j=i+1,n
      mi=hypot(wr(i),wi(i));mj=hypot(wr(j),wi(j));ai=atan2(wi(i),wr(i));aj=atan2(wi(j),wr(j))
      if(mj<mi .or. (abs(mj-mi)<=epsilon(1._rk)*max(1._rk,mi) .and. aj<ai)) then
        tr=wr(i);ti=wi(i);wr(i)=wr(j);wi(i)=wi(j);wr(j)=tr;wi(j)=ti
      endif
    enddo;enddo
  end subroutine

  subroutine matlab_complex_sort_vectors(w,V)
    complex(rk),intent(inout)::w(:),V(:,:)
    integer::i,j,n;complex(rk)::tw;complex(rk),allocatable::tv(:);real(rk)::mi,mj,ai,aj
    n=size(w);allocate(tv(size(V,1)))
    do i=1,n-1;do j=i+1,n
      mi=abs(w(i));mj=abs(w(j));ai=atan2(aimag(w(i)),real(w(i),rk));aj=atan2(aimag(w(j)),real(w(j),rk))
      if(mj<mi .or. (abs(mj-mi)<=epsilon(1._rk)*max(1._rk,mi) .and. aj<ai)) then
        tw=w(i);w(i)=w(j);w(j)=tw;tv=V(:,i);V(:,i)=V(:,j);V(:,j)=tv
      endif
    enddo;enddo
  end subroutine
end module rd_eigensystem
