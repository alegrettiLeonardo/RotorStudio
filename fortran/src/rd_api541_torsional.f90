module rd_api541_torsional
  use, intrinsic :: ieee_arithmetic, only: ieee_is_finite
  use rd_kinds, only: rk, ik
  use rd_status, only: RD_OK, RD_ERR_INPUT, RD_ERR_LAPACK
  use rd_lapack, only: generalized_eig_real
  implicit none(type, external)
  private
  public :: api541_torsional_matrices, api541_torsional_modes
contains

  subroutine api541_torsional_matrices(n,inertia,stiffness,damping,m,c,k,status)
    integer(ik),intent(in)::n
    real(rk),intent(in)::inertia(n),stiffness(n-1),damping(n-1)
    real(rk),intent(out)::m(n,n),c(n,n),k(n,n)
    integer(ik),intent(out)::status
    integer::i

    status=RD_ERR_INPUT
    if(n<2 .or. n>128)return
    if(.not.all(ieee_is_finite(inertia)))return
    if(.not.all(ieee_is_finite(stiffness)))return
    if(.not.all(ieee_is_finite(damping)))return
    if(any(inertia<=0._rk))return
    if(any(stiffness<=0._rk))return
    if(any(damping<0._rk))return

    m=0._rk;c=0._rk;k=0._rk
    do i=1,n
      m(i,i)=inertia(i)
    enddo
    do i=1,n-1
      k(i,i)=k(i,i)+stiffness(i)
      k(i+1,i+1)=k(i+1,i+1)+stiffness(i)
      k(i,i+1)=k(i,i+1)-stiffness(i)
      k(i+1,i)=k(i+1,i)-stiffness(i)

      c(i,i)=c(i,i)+damping(i)
      c(i+1,i+1)=c(i+1,i+1)+damping(i)
      c(i,i+1)=c(i,i+1)-damping(i)
      c(i+1,i)=c(i+1,i)-damping(i)
    enddo
    status=RD_OK
  end subroutine

  subroutine api541_torsional_modes(n,inertia,stiffness,damping,m,c,k,frequency,modes,status)
    integer(ik),intent(in)::n
    real(rk),intent(in)::inertia(n),stiffness(n-1),damping(n-1)
    real(rk),intent(out)::m(n,n),c(n,n),k(n,n),frequency(n),modes(n,n)
    integer(ik),intent(out)::status
    real(rk),allocatable::a(:,:),b(:,:),alphar(:),alphai(:),beta(:),vr(:,:),lambda(:),tmpv(:)
    real(rk)::scale,tol_alpha,tol_beta,lambda_scale,tmp
    integer::i,j,best

    call api541_torsional_matrices(n,inertia,stiffness,damping,m,c,k,status)
    if(status/=RD_OK)return

    allocate(a(n,n),b(n,n),alphar(n),alphai(n),beta(n),vr(n,n),lambda(n),tmpv(n))
    a=k;b=m
    call generalized_eig_real(a,b,alphar,alphai,beta,vr,status)
    if(status/=RD_OK)return

    tol_alpha=1024._rk*epsilon(1._rk)*max(1._rk,maxval(abs(alphar)))
    tol_beta=1024._rk*epsilon(1._rk)*max(1._rk,maxval(abs(beta)))
    do i=1,n
      if(abs(alphai(i))>tol_alpha)then
        status=RD_ERR_LAPACK;return
      endif
      if(abs(beta(i))<=tol_beta)then
        status=RD_ERR_LAPACK;return
      endif
      lambda(i)=alphar(i)/beta(i)
    enddo
    lambda_scale=max(1._rk,maxval(abs(lambda)))
    do i=1,n
      if(lambda(i)<-1024._rk*epsilon(1._rk)*lambda_scale)then
        status=RD_ERR_LAPACK;return
      endif
      if(lambda(i)<0._rk)lambda(i)=0._rk
      frequency(i)=sqrt(lambda(i))
      modes(:,i)=vr(:,i)
      scale=maxval(abs(modes(:,i)))
      if(scale<=0._rk .or. .not.ieee_is_finite(scale))then
        status=RD_ERR_LAPACK;return
      endif
      modes(:,i)=modes(:,i)/scale
      do j=1,n
        if(abs(modes(j,i))>128._rk*epsilon(1._rk))then
          if(modes(j,i)<0._rk)modes(:,i)=-modes(:,i)
          exit
        endif
      enddo
    enddo

    ! Stable ascending frequency order with associated mode vectors.
    do i=1,n-1
      best=i
      do j=i+1,n
        if(frequency(j)<frequency(best))best=j
      enddo
      if(best/=i)then
        tmp=frequency(i);frequency(i)=frequency(best);frequency(best)=tmp
        tmpv=modes(:,i);modes(:,i)=modes(:,best);modes(:,best)=tmpv
      endif
    enddo

    if(.not.all(ieee_is_finite(frequency)).or..not.all(ieee_is_finite(modes)))then
      status=RD_ERR_LAPACK;return
    endif
    status=RD_OK
  end subroutine

end module
