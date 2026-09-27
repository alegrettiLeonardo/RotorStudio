! Simple Newmark authority: ROSS utils.py at 6320eab9. No nonlinear RHS.
module rd_newmark
 use, intrinsic::ieee_arithmetic,only:ieee_is_finite
 use rd_kinds,only:rk,ik
 implicit none(type,external)
 private
 public::newmark_step
 interface
 subroutine dgetrf(m,n,a,lda,ipiv,info)
 import rk
 integer,intent(in)::m,n,lda
 real(rk),intent(inout)::a(lda,*)
 integer,intent(out)::ipiv(*),info
 end subroutine
 subroutine dgetrs(trans,n,nrhs,a,lda,ipiv,b,ldb,info)
 import rk
 character,intent(in)::trans
 integer,intent(in)::n,nrhs,lda,ldb,ipiv(*)
 real(rk),intent(in)::a(lda,*)
 real(rk),intent(inout)::b(ldb,*)
 integer,intent(out)::info
 end subroutine
 subroutine dgecon(norm,n,a,lda,anorm,rcond,work,iwork,info)
 import rk
 character,intent(in)::norm
 integer,intent(in)::n,lda
 real(rk),intent(in)::a(lda,*),anorm
 real(rk),intent(out)::rcond,work(*)
 integer,intent(out)::iwork(*),info
 end subroutine
 end interface
contains
 subroutine newmark_step(n,M,C,K,F,dt,gamma,beta,tol,q0,v0,a0,q,v,a,iterations,residual,absolute_residual,condition,status)
 integer(ik),intent(in)::n
 real(rk),intent(in)::M(n,n),C(n,n),K(n,n),F(n),dt,gamma,beta,tol,q0(n),v0(n),a0(n)
 real(rk),intent(out)::q(n),v(n),a(n),residual,absolute_residual,condition
 integer(ik),intent(out)::iterations,status
 real(rk),allocatable::J(:,:),rhs(:,:),r(:),work(:)
 integer,allocatable::piv(:),iw(:)
 integer::err,info
 real(rk)::anorm,rcond,den
 status=10;iterations=0;residual=0;absolute_residual=0;condition=0
 if(n<1.or.n>512)return
 if(.not.all(ieee_is_finite([dt,gamma,beta,tol])))return
 if(dt<=0.or.gamma<=0.or.beta<=0.or.tol<=0)return
 if(.not.all(ieee_is_finite(M)).or..not.all(ieee_is_finite(C)).or..not.all(ieee_is_finite(K)))return
 if(.not.all(ieee_is_finite(F)).or..not.all(ieee_is_finite(q0)).or..not.all(ieee_is_finite(v0)).or..not.all(ieee_is_finite(a0)))return
 allocate(J(n,n),rhs(n,1),r(n),work(4*n),piv(n),iw(n),stat=err);if(err/=0)return
 a=0;v=v0+a0*(1-gamma)*dt;q=q0+v0*dt+a0*(0.5_rk-beta)*dt**2
 J=M+C*gamma*dt+K*beta*dt**2
 status=30
 if(.not.all(ieee_is_finite(J)))return
 anorm=maxval(sum(abs(J),dim=1))
 if(.not.ieee_is_finite(anorm))return
 call dgetrf(n,n,J,n,piv,info);if(info/=0)return
 call dgecon('1',n,J,n,anorm,rcond,work,iw,info)
 if(info/=0.or..not.ieee_is_finite(rcond))return
 if(rcond<=n*epsilon(1._rk))return
 condition=1/rcond
 do
 r=F-(matmul(M,a)+matmul(C,v)+matmul(K,q))
 if(.not.all(ieee_is_finite(r)))return
 absolute_residual=norm2(r)
 den=maxval(sum(abs(M),dim=2))*maxval(abs(a))+maxval(sum(abs(C),dim=2))*maxval(abs(v))+ &
 maxval(sum(abs(K),dim=2))*maxval(abs(q))+maxval(abs(F))
 if(.not.all(ieee_is_finite([den,absolute_residual])))return
 residual=0;if(den>0)residual=maxval(abs(r))/den
 if(absolute_residual<tol)exit
 if(iterations>=50)then;status=40;return;endif
 iterations=iterations+1;rhs(:,1)=r
 call dgetrs('N',n,1,J,n,piv,rhs,n,info);if(info/=0)return
 a=a+rhs(:,1);v=v+rhs(:,1)*gamma*dt;q=q+rhs(:,1)*beta*dt**2
 if(.not.all(ieee_is_finite(a)).or..not.all(ieee_is_finite(v)).or..not.all(ieee_is_finite(q)))return
 enddo
 status=0
 end subroutine
end module
