module rd_eigensystem
  use rd_kinds, only: rk,ik
  use rd_status, only: RD_OK
  use rd_lapack, only: solve_real,eig_real,solve_complex,eig_complex
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
    complex(rk),allocatable::Mc(:,:),XK(:,:),XC(:,:),A(:,:),vr(:,:)
    n=size(M,1)
    allocate(Mc(n,n),XK(n,n),XC(n,n),A(2*n,2*n),vr(2*n,2*n))
    Mc=cmplx(M,0._rk,rk);XK=cmplx(K,0._rk,rk)
    call solve_complex(Mc,XK,status);if(status/=RD_OK)return
    Mc=cmplx(M,0._rk,rk);XC=cmplx(C,0._rk,rk)
    call solve_complex(Mc,XC,status);if(status/=RD_OK)return
    A=(0._rk,0._rk)
    do i=1,n;A(i,n+i)=(1._rk,0._rk);enddo
    A(n+1:2*n,1:n)=-XK;A(n+1:2*n,n+1:2*n)=-XC
    call eig_complex(A,w,vr,status);if(status/=RD_OK)return
    Vdisp=vr(1:n,:)
    call matlab_complex_sort_vectors(w,Vdisp)
  end subroutine

  subroutine matlab_complex_sort(wr,wi)
    real(rk),intent(inout)::wr(:),wi(:);integer::i,j,n;real(rk)::tr,ti,mi,mj,ai,aj
    n=size(wr)
    do i=1,n-1;do j=i+1,n
      mi=hypot(wr(i),wi(i));mj=hypot(wr(j),wi(j));ai=atan2(wi(i),wr(i));aj=atan2(wi(j),wr(j))
      if(mj<mi .or. (mj==mi .and. aj<ai)) then
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
      if(mj<mi .or. (mj==mi .and. aj<ai)) then
        tw=w(i);w(i)=w(j);w(j)=tw;tv=V(:,i);V(:,i)=V(:,j);V(:,j)=tv
      endif
    enddo;enddo
  end subroutine
end module rd_eigensystem
