module rd_api541_torsional_response
  use, intrinsic :: ieee_arithmetic, only: ieee_is_finite
  use rd_kinds, only: rk, ik
  use rd_status, only: RD_OK, RD_ERR_INPUT
  use rd_lapack, only: solve_complex
  use rd_api541_torsional, only: api541_torsional_matrices
  implicit none(type, external)
  private
  public :: api541_torsional_harmonic_response
contains

  subroutine api541_torsional_harmonic_response(n,inertia,stiffness,damping,nf,omega,fr,fi,qr,qi,tr,ti,status)
    integer(ik),intent(in)::n,nf
    real(rk),intent(in)::inertia(n),stiffness(n-1),damping(n-1),omega(nf)
    real(rk),intent(in)::fr(n,nf),fi(n,nf)
    real(rk),intent(out)::qr(n,nf),qi(n,nf),tr(n-1,nf),ti(n-1,nf)
    integer(ik),intent(out)::status
    real(rk),allocatable::m(:,:),c(:,:),k(:,:)
    complex(rk),allocatable::d(:,:),rhs(:,:),q(:),tc(:)
    complex(rk)::zspring
    integer::j,i

    status=RD_ERR_INPUT
    if(n<2 .or. n>128 .or. nf<1 .or. nf>10000)return
    if(.not.all(ieee_is_finite(omega)).or.any(omega<=0._rk))return
    if(.not.all(ieee_is_finite(fr)).or..not.all(ieee_is_finite(fi)))return

    allocate(m(n,n),c(n,n),k(n,n),d(n,n),rhs(n,1),q(n),tc(n-1))
    call api541_torsional_matrices(n,inertia,stiffness,damping,m,c,k,status)
    if(status/=RD_OK)return

    do j=1,nf
      d=cmplx(k-omega(j)*omega(j)*m,omega(j)*c,rk)
      rhs(:,1)=cmplx(fr(:,j),fi(:,j),rk)
      call solve_complex(d,rhs,status)
      if(status/=RD_OK)return
      q=rhs(:,1)
      if(.not.all(ieee_is_finite(real(q))).or..not.all(ieee_is_finite(aimag(q))))then
        status=RD_ERR_INPUT;return
      endif
      qr(:,j)=real(q,rk);qi(:,j)=aimag(q)
      do i=1,n-1
        zspring=cmplx(stiffness(i),omega(j)*damping(i),rk)
        tc(i)=zspring*(q(i)-q(i+1))
      enddo
      tr(:,j)=real(tc,rk);ti(:,j)=aimag(tc)
    enddo
    status=RD_OK
  end subroutine

end module
