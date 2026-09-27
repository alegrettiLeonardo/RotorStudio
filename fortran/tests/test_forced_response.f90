program test_forced
 use, intrinsic::ieee_arithmetic,only:ieee_value,ieee_quiet_nan
 use rd_kinds,only:rk,ik
 use rd_forced_response
 use rd_dynamic_stiffness,only:build_dynamic_stiffness
 use rd_frf_general
 implicit none
 integer,parameter::nn=3,n=12,nf=2
 real(rk)::z(nn),sh(11,2),disk(6,1),coeff(12,2,nf),freq(nf)
 real(rk)::fr(n,nf),fi(n,nf),qr(n,nf),qi(n,nf),vr(n,nf),vi(n,nf),ar(n,nf),ai(n,nf),res(nf),cond(nf)
 real(rk)::hr(n,n,nf),hi(n,n,nf),hv(n,n,nf),hvi(n,n,nf),ha(n,n,nf),hai(n,n,nf),hres(nf)
 real(rk)::M(n,n),C(n,n),G(n,n),K(n,n),Mb(n,n),Cb(n,n),Kb(n,n)
 complex(rk)::D(n,n),known(n),forcing(n)
 complex(rk)::q1(n,nf),q2(n,nf),expected(n,nf),scalar
 integer(ik)::status,nodes(2)
 integer::i,policy,dof
 z=[0._rk,.25_rk,.5_rk];sh=0
 do i=1,2;sh(:,i)=[2._rk,real(i,rk),real(i+1,rk),.05_rk,.01_rk,7810._rk,211.e9_rk,81.2e9_rk,0._rk,0._rk,0._rk];enddo
 disk(:,1)=[2._rk,2._rk,7._rk,.02_rk,.04_rk,0._rk]
 nodes=[1,3];coeff=0
 coeff(9,:,:)=1.1e6_rk;coeff(12,:,:)=1.7e6_rk;coeff(5,:,:)=170;coeff(8,:,:)=230
 freq=[0._rk,117._rk]
 do policy=0,1
 call general_frf(nn,z,2,sh,1,disk,2,nodes,nf,freq,policy,183._rk,coeff,hr,hi,hv,hvi,ha,hai,hres,status)
 if(status/=0)stop 1
 ! Unit response at every DOF, including pure moments, is a one-column H sentinel.
 do dof=1,n
 fr=0;fi=0;fr(dof,:)=137;fi(dof,:)=41
 call run(policy)
 do i=1,nf
 expected(:,i)=cmplx(hr(:,dof,i),hi(:,dof,i),rk)*cmplx(137._rk,41._rk,rk)
 enddo
 if(maxval(abs(cmplx(qr,qi,rk)-expected))>1.e-11_rk)stop 2
 enddo
 enddo
 ! Known single response coordinate: build F=D*q_known, recover exactly that coordinate.
 known=0;known(7)=cmplx(.003_rk,-.002_rk,rk)
 do i=1,nf
 call build_dynamic_stiffness(nn,z,2,sh,1,disk,2,nodes,coeff(:,:,i),183._rk,freq(i),M,C,G,K,Mb,Cb,Kb,D,status)
 if(status/=0)stop 17
 forcing=matmul(D,known);fr(:,i)=real(forcing);fi(:,i)=aimag(forcing)
 enddo
 call run(1)
 do i=1,nf
 if(maxval(abs(cmplx(qr(:,i),qi(:,i),rk)-known))>1.e-13_rk)stop 18
 enddo
 fr=0;fi=0;fr(5,:)=[137._rk,23._rk];fi(5,:)=[41._rk,-7._rk];call run(1);q1=cmplx(qr,qi,rk)
 fr=0;fi=0;fr(7,:)=[17._rk,31._rk];fi(10,:)=[-23._rk,89._rk];call run(1);q2=cmplx(qr,qi,rk)
 fr(5,:)=[137._rk,23._rk];fi(5,:)=[41._rk,-7._rk];call run(1)
 if(maxval(abs(cmplx(qr,qi,rk)-q1-q2))>1.e-11_rk)stop 3
 scalar=cmplx(-.7_rk,1.3_rk,rk);expected=cmplx(fr,fi,rk)*scalar
 fr=real(expected);fi=aimag(expected);call run(1)
 if(maxval(abs(cmplx(qr,qi,rk)-(q1+q2)*scalar))>1.e-11_rk)stop 4
 fr=0;fi=0;call run(1)
 if(any(qr/=0).or.any(qi/=0).or.any(vr/=0).or.any(vi/=0).or.any(ar/=0).or.any(ai/=0).or.any(res/=0))stop 5
 call forced_response(nn,z,2,sh,1,disk,2,nodes,nf,freq,1,183._rk,coeff,n-1,nf,fr(:n-1,:),fi(:n-1,:),qr,qi,vr,vi,ar,ai,res,cond,status)
 if(status/=10)stop 6
 fi(1,1)=ieee_value(0._rk,ieee_quiet_nan);call raw(1);if(status/=10)stop 7
 fi=0;freq(1)=-1;call raw(1);if(status/=10)stop 8
 freq(1)=ieee_value(0._rk,ieee_quiet_nan);call raw(1);if(status/=10)stop 9
 freq(1)=0;call raw(2);if(status/=10)stop 10
 coeff(:,2,:)=0;call raw(1);if(status/=30)stop 11
 coeff=0;call raw(1);if(status/=30)stop 12
 if(forced_size_valid(128,10000).or.forced_size_valid(3,0))stop 13
 print *,'PASS A3 direct solve, force/moment columns, synchronous/fixed, superposition, complex scaling, zero, residual, conditioning, invalid shape/nonfinite/frequency/policy, singular'
contains
 subroutine raw(p)
 integer,intent(in)::p
 call forced_response(nn,z,2,sh,1,disk,2,nodes,nf,freq,p,183._rk,coeff,n,nf,fr,fi,qr,qi,vr,vi,ar,ai,res,cond,status)
 end subroutine
 subroutine run(p)
 integer,intent(in)::p
 call raw(p)
 if(status/=0.or.maxval(res)>1.e-12_rk.or.any(cond<1))stop 14
 do i=1,nf
 if(maxval(abs(cmplx(vr(:,i),vi(:,i),rk)-cmplx(0._rk,freq(i),rk)*cmplx(qr(:,i),qi(:,i),rk)))>1.e-12_rk)stop 15
 if(maxval(abs(cmplx(ar(:,i),ai(:,i),rk)+freq(i)**2*cmplx(qr(:,i),qi(:,i),rk)))>1.e-12_rk)stop 16
 enddo
 end subroutine
end program
