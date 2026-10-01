module rd_irdin_support_analysis
  use rd_kinds, only: rk, ik
  use rd_status, only: RD_OK, RD_ERR_INPUT, RD_ERR_LAPACK
  use rd_eigensystem, only: second_order_eigs
  use rd_lapack, only: solve_complex
  use, intrinsic :: ieee_arithmetic, only: ieee_is_finite
  implicit none(type, external)
  private
  public :: irdin_expanded_modal, irdin_expanded_synchronous
contains
  subroutine irdin_expanded_modal(m,c,k,w,v,status)
    real(rk),intent(in)::m(:,:),c(:,:),k(:,:)
    complex(rk),intent(out)::w(:),v(:,:)
    integer(ik),intent(out)::status
    integer::n
    status=RD_ERR_INPUT
    n=size(m,1)
    if(n<1.or.size(m,2)/=n)return
    if(size(c,1)/=n.or.size(c,2)/=n.or.size(k,1)/=n.or.size(k,2)/=n)return
    if(size(w)<2*n.or.size(v,1)<n.or.size(v,2)<2*n)return
    if(.not.all(ieee_is_finite(m)).or..not.all(ieee_is_finite(c)).or..not.all(ieee_is_finite(k)))return
    call second_order_eigs(m,c,k,w(1:2*n),v(1:n,1:2*n),status)
    if(status/=RD_OK)return
    if(.not.all(ieee_is_finite(real(w(1:2*n),rk))).or..not.all(ieee_is_finite(aimag(w(1:2*n)))))then
      status=RD_ERR_LAPACK;return
    endif
    if(.not.all(ieee_is_finite(real(v(1:n,1:2*n),rk))).or..not.all(ieee_is_finite(aimag(v(1:n,1:2*n)))))then
      status=RD_ERR_LAPACK;return
    endif
  end subroutine

  subroutine irdin_expanded_synchronous(nnode,m,c,k,omega,nforce,nodes,mag,phase,q,residual,status)
    integer(ik),intent(in)::nnode,nforce,nodes(nforce)
    real(rk),intent(in)::m(:,:),c(:,:),k(:,:),omega,mag(nforce),phase(nforce)
    complex(rk),intent(out)::q(:)
    real(rk),intent(out)::residual
    integer(ik),intent(out)::status
    integer::n,i,j
    real(rk)::normd,normq,normf,denom
    complex(rk)::p,jot
    complex(rk),allocatable::d(:,:),a(:,:),rhs(:,:),force(:),err(:)
    status=RD_ERR_INPUT;residual=0._rk
    n=size(m,1)
    if(nnode<1.or.n<4*nnode.or.nforce<1)return
    if(size(m,2)/=n.or.size(c,1)/=n.or.size(c,2)/=n.or.size(k,1)/=n.or.size(k,2)/=n)return
    if(size(q)<n)return
    if(.not.ieee_is_finite(omega).or.omega<0._rk)return
    if(.not.all(ieee_is_finite(m)).or..not.all(ieee_is_finite(c)).or..not.all(ieee_is_finite(k)))return
    if(.not.all(ieee_is_finite(mag)).or..not.all(ieee_is_finite(phase)))return
    if(any(nodes<1).or.any(nodes>nnode))return
    allocate(d(n,n),a(n,n),rhs(n,1),force(n),err(n))
    d=cmplx(k-omega*omega*m,omega*c,rk)
    a=d;force=(0._rk,0._rk);jot=(0._rk,1._rk)
    do i=1,nforce
      p=cmplx(cos(phase(i)),sin(phase(i)),rk)*mag(i)*omega*omega
      j=4*nodes(i)-3
      ! Historical resp_f convention: X=-i*P, legacy Z/domain Y=+P.
      force(j)=force(j)-jot*p
      force(j+1)=force(j+1)+p
    enddo
    rhs(:,1)=force
    call solve_complex(a,rhs,status)
    if(status/=RD_OK)return
    q(1:n)=rhs(:,1)
    if(.not.all(ieee_is_finite(real(q(1:n),rk))).or..not.all(ieee_is_finite(aimag(q(1:n)))))then
      status=RD_ERR_LAPACK;return
    endif
    err=matmul(d,q(1:n))-force
    normd=maxval(sum(abs(d),dim=2));normq=maxval(abs(q(1:n)));normf=maxval(abs(force))
    denom=normd*normq+normf
    residual=0._rk
    if(denom>0._rk)residual=maxval(abs(err))/denom
    if(.not.ieee_is_finite(residual).or.residual>1.e-12_rk)then
      status=RD_ERR_LAPACK;return
    endif
    status=RD_OK
  end subroutine
end module
