! ROSS forced-response semantics; direct solve using the qualified A2 D builder.
module rd_forced_response
 use, intrinsic::iso_fortran_env,only:int64
 use, intrinsic::ieee_arithmetic,only:ieee_is_finite
 use rd_kinds,only:rk,ik
 use rd_status,only:RD_OK,RD_ERR_INPUT,RD_ERR_LAPACK
 use rd_dynamic_stiffness,only:build_dynamic_stiffness
 use rd_lapack,only:solve_complex
 implicit none(type,external)
 private
 public::forced_response,forced_size_valid
 interface
  subroutine zgecon(norm,n,a,lda,anorm,rcond,work,rwork,info)
   import rk
   character::norm
   integer::n,lda,info
   complex(rk)::a(lda,*),work(*)
   real(rk)::anorm,rcond,rwork(*)
  end subroutine
 end interface
contains
 logical function forced_size_valid(nn,nf)
 integer,intent(in)::nn,nf
 forced_size_valid=.false.
 if(nn<2.or.nn>128.or.nf<1.or.nf>10000)return
 ! Includes force/result split buffers, complex reconstruction, coefficients and workspace.
 forced_size_valid=(320_int64*(4_int64*nn)*nf+160_int64*(4_int64*nn)**2<=536870912_int64)
 end function
 subroutine forced_response(nn,z,ns,sh,nd,di,nb,nodes,nf,freq,policy,fixed,coeff,fd,ff,fr,fi,qr,qi,vr,vi,ar,ai,residual,condition,status)
 integer(ik),intent(in)::nn,ns,nd,nb,nf,policy,nodes(nb),fd,ff
 real(rk),intent(in)::z(nn),sh(11,ns),di(6,nd),freq(nf),fixed,coeff(12,nb,nf),fr(fd,ff),fi(fd,ff)
 real(rk),intent(out)::qr(4*nn,nf),qi(4*nn,nf),vr(4*nn,nf),vi(4*nn,nf),ar(4*nn,nf),ai(4*nn,nf),residual(nf),condition(nf)
 integer(ik),intent(out)::status
 real(rk),allocatable::M(:,:),C(:,:),G(:,:),K(:,:),Mb(:,:),Cb(:,:),Kb(:,:),rwork(:)
 complex(rk),allocatable::D(:,:),A(:,:),q(:,:),force(:),error(:),work(:)
 integer::n,i,err,info
 real(rk)::speed,w,denom,rcond,anorm,normd,normq,normf
 status=RD_ERR_INPUT
 if(.not.forced_size_valid(nn,nf).or.policy<0.or.policy>1.or.ns/=nn-1.or.nd<0.or.nd>1024.or.nb<0.or.nb>2*nn)return
 if(fd/=4*nn.or.ff/=nf)return
 if(.not.all(ieee_is_finite(freq)).or..not.ieee_is_finite(fixed).or.any(freq<0))return
 if(.not.all(ieee_is_finite(fr)).or..not.all(ieee_is_finite(fi)))return
 n=4*nn
 allocate(M(n,n),C(n,n),G(n,n),K(n,n),Mb(n,n),Cb(n,n),Kb(n,n),D(n,n),A(n,n),q(n,1),force(n),error(n),work(2*n),rwork(2*n),stat=err)
 if(err/=0)return
 do i=1,nf
  w=freq(i);speed=w
  if(policy==1)speed=fixed
  call build_dynamic_stiffness(nn,z,ns,sh,nd,di,nb,nodes,coeff(:,:,i),speed,w,M,C,G,K,Mb,Cb,Kb,D,status)
  if(status/=RD_OK)return
  A=D;force=cmplx(fr(:,i),fi(:,i),rk);q(:,1)=force
  call solve_complex(A,q,status)
  if(status/=RD_OK)return
  anorm=maxval(sum(abs(D),dim=1))
  call zgecon('1',n,A,n,anorm,rcond,work,rwork,info)
  if(info/=0.or..not.ieee_is_finite(rcond).or.rcond<=n*epsilon(1._rk))then;status=RD_ERR_LAPACK;return;endif
  condition(i)=1/rcond
  if(.not.all(ieee_is_finite(real(q))).or..not.all(ieee_is_finite(aimag(q))))then;status=RD_ERR_LAPACK;return;endif
  error=matmul(D,q(:,1))-force
  normd=maxval(sum(abs(D),dim=2));normq=maxval(abs(q));normf=maxval(abs(force))
  denom=normd*normq+normf
  if(.not.ieee_is_finite(denom).or..not.all(ieee_is_finite(abs(error))))then;status=RD_ERR_LAPACK;return;endif
  residual(i)=0
  if(denom>0)residual(i)=maxval(abs(error))/denom
  if(.not.ieee_is_finite(residual(i)).or.residual(i)>1.e-12_rk)then;status=RD_ERR_LAPACK;return;endif
  qr(:,i)=real(q(:,1));qi(:,i)=aimag(q(:,1))
  vr(:,i)=-w*qi(:,i);vi(:,i)=w*qr(:,i)
  ar(:,i)=-w*w*qr(:,i);ai(:,i)=-w*w*qi(:,i)
  if(.not.all(ieee_is_finite(ar(:,i))).or..not.all(ieee_is_finite(ai(:,i))).or. &
     .not.all(ieee_is_finite(vr(:,i))).or..not.all(ieee_is_finite(vi(:,i))))then;status=RD_ERR_LAPACK;return;endif
 enddo
 status=RD_OK
 end subroutine
end module
