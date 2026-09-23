module rd_eigensystem
  use rd_kinds, only: rk,ik
  use rd_status, only: RD_OK
  use rd_lapack, only: solve_real,eig_real
  implicit none(type, external); private; public::stationary_eigs
contains
  subroutine stationary_eigs(M,C,K,wr,wi,status)
    real(rk),intent(in)::M(:,:),C(:,:),K(:,:);real(rk),intent(out)::wr(:),wi(:);integer(ik),intent(out)::status
    integer::n,i,j;real(rk),allocatable::Ac(:,:),XK(:,:),XC(:,:),vr(:,:)
    n=size(M,1);allocate(Ac(n,n),XK(n,n),XC(n,n),vr(2*n,2*n)); XK=M;XC=M
    Ac=K;call solve_real(XK,Ac,status);if(status/=RD_OK)return;XK=Ac
    Ac=C;call solve_real(XC,Ac,status);if(status/=RD_OK)return;XC=Ac
    deallocate(Ac);allocate(Ac(2*n,2*n));Ac=0
    do i=1,n;Ac(i,n+i)=1;enddo
    Ac(n+1:2*n,1:n)=-XK;Ac(n+1:2*n,n+1:2*n)=-XC
    call eig_real(Ac,wr,wi,vr,status)
    if(status==RD_OK) call matlab_complex_sort(wr,wi)
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
end module rd_eigensystem
