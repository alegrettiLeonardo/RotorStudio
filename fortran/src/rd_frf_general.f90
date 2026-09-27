! ROSS-derived full-order receptance semantics; see third_party/ROSS_NOTICE.md.
module rd_frf_general
 use, intrinsic::iso_fortran_env,only:int64
 use, intrinsic::ieee_arithmetic,only:ieee_is_finite
 use rd_kinds,only:rk,ik
 use rd_status,only:RD_OK,RD_ERR_INPUT,RD_ERR_LAPACK
 use rd_dynamic_stiffness,only:build_dynamic_stiffness
 use rd_lapack,only:solve_complex
 implicit none(type,external)
 private
 public::general_frf,frf_size_valid
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
 logical function frf_size_valid(nn,nf)
 integer,intent(in)::nn,nf
 frf_size_valid=.false.
 if(nn<2.or.nn>128.or.nf<1.or.nf>10000)return
 ! Six real response buffers + complex reconstructed responses + native workspace,
 ! conservatively bounded to 512 MiB. int64 multiplication occurs after dimension caps.
 frf_size_valid=(192_int64*(4_int64*nn)**2*nf+160_int64*(4_int64*nn)**2<=536870912_int64)
 end function
 subroutine general_frf(nn,z,ns,sh,nd,di,nb,nodes,nf,freq,policy,fixed,coeff,hr,hi,vr,vi,ar,ai,residual,status)
 integer(ik),intent(in)::nn,ns,nd,nb,nf,policy,nodes(nb)
 real(rk),intent(in)::z(nn),sh(11,ns),di(6,nd),freq(nf),fixed,coeff(12,nb,nf)
 real(rk),intent(out)::hr(4*nn,4*nn,nf),hi(4*nn,4*nn,nf),vr(4*nn,4*nn,nf),vi(4*nn,4*nn,nf),ar(4*nn,4*nn,nf),ai(4*nn,4*nn,nf),residual(nf)
 integer(ik),intent(out)::status
 real(rk),allocatable::M(:,:),C(:,:),G(:,:),K(:,:),Mb(:,:),Cb(:,:),Kb(:,:)
 complex(rk),allocatable::D(:,:),A(:,:),H(:,:),identity(:,:),error(:,:),condition_work(:)
 integer::n,i,j,err,info
 real(rk),allocatable::condition_rwork(:)
 real(rk)::speed,w,denom,rcond,anorm
 status=RD_ERR_INPUT
 if(.not.frf_size_valid(nn,nf).or.policy<0.or.policy>2.or.ns/=nn-1.or.nd<0.or.nd>1024.or.nb<0.or.nb>2*nn)return
 if(.not.all(ieee_is_finite(freq)).or..not.ieee_is_finite(fixed))return
 if(any(freq<0))return
 n=4*nn
 allocate(M(n,n),C(n,n),G(n,n),K(n,n),Mb(n,n),Cb(n,n),Kb(n,n),D(n,n),A(n,n),H(n,n),identity(n,n),error(n,n),condition_work(2*n),condition_rwork(2*n),stat=err)
 if(err/=0)return
 identity=0;do j=1,n;identity(j,j)=1;enddo
 do i=1,nf
  w=freq(i)
  select case(policy)
  case(0);speed=w
  case(1);speed=fixed
  case(2);speed=0
  end select
  call build_dynamic_stiffness(nn,z,ns,sh,nd,di,nb,nodes,coeff(:,:,i),speed,w,M,C,G,K,Mb,Cb,Kb,D,status)
  if(status/=RD_OK)return
  if(w==0.and.all(coeff(9:12,:,i)==0))then;status=RD_ERR_LAPACK;return;endif
  A=D;H=identity
  call solve_complex(A,H,status)
  if(status/=RD_OK)return
  ! DGESV/ZGESV can accept floating-point remnants of a rigid-body singularity.
  ! Reuse its LU factors to estimate reciprocal condition before accepting H.
  anorm=maxval(sum(abs(D),dim=1))
  call zgecon('1',n,A,n,anorm,rcond,condition_work,condition_rwork,info)
  if(info/=0.or..not.ieee_is_finite(rcond).or.rcond<=n*epsilon(1._rk))then;status=RD_ERR_LAPACK;return;endif
  if(.not.all(ieee_is_finite(real(H))).or..not.all(ieee_is_finite(aimag(H))))then;status=RD_ERR_LAPACK;return;endif
  error=matmul(D,H)-identity
  denom=maxval(sum(abs(D),dim=2))*maxval(sum(abs(H),dim=2))+1
  residual(i)=maxval(sum(abs(error),dim=2))/denom
  if(.not.ieee_is_finite(residual(i)).or.residual(i)>1.e-10_rk)then;status=RD_ERR_LAPACK;return;endif
  hr(:,:,i)=real(H);hi(:,:,i)=aimag(H)
  vr(:,:,i)=-w*aimag(H);vi(:,:,i)=w*real(H)
  ar(:,:,i)=-w*w*real(H);ai(:,:,i)=-w*w*aimag(H)
  if(.not.all(ieee_is_finite(ar(:,:,i))).or..not.all(ieee_is_finite(ai(:,:,i))).or. &
     .not.all(ieee_is_finite(vr(:,:,i))).or..not.all(ieee_is_finite(vi(:,:,i))))then;status=RD_ERR_LAPACK;return;endif
 enddo
 status=RD_OK
 end subroutine
end module
