program test_frf_general
 use, intrinsic::ieee_arithmetic,only:ieee_value,ieee_quiet_nan
 use rd_kinds,only:rk,ik
 use rd_dynamic_stiffness
 use rd_frf_general
 implicit none
 integer,parameter::nn=3,n=12,nf=2
 real(rk)::z(nn),sh(11,2),disk(6,1),coeff(12,2,nf),freq(nf),M(n,n),C(n,n),G(n,n),K(n,n),Mb(n,n),Cb(n,n),Kb(n,n)
 real(rk)::hr(n,n,nf),hi(n,n,nf),vr(n,n,nf),vi(n,n,nf),ar(n,n,nf),ai(n,n,nf),res(nf),old(n,n)
 complex(rk)::D(n,n),H(n,n),Id(n,n)
 integer(ik)::status,nodes(2)
 integer::i
 z=[0._rk,.25_rk,.5_rk];sh=0
 do i=1,2;sh(:,i)=[2._rk,real(i,rk),real(i+1,rk),.05_rk,.01_rk,7810._rk,211.e9_rk,81.2e9_rk,0._rk,0._rk,0._rk];enddo
 disk(:,1)=[2._rk,2._rk,7._rk,.02_rk,.04_rk,0._rk]
 nodes=[1,3];coeff=0
 do i=1,nf
 coeff(9,:,i)=1.1e6_rk;coeff(12,:,i)=1.7e6_rk
 coeff(10,:,i)=-2.e4_rk;coeff(11,:,i)=3.e4_rk
 coeff(5,:,i)=170;coeff(8,:,i)=230;coeff(6,:,i)=-7;coeff(7,:,i)=13
 enddo
 freq=[0._rk,117._rk];Id=0;do i=1,n;Id(i,i)=1;enddo
 call general_frf(nn,z,2,sh,1,disk,2,nodes,nf,freq,1,183._rk,coeff,hr,hi,vr,vi,ar,ai,res,status)
 if(status/=0.or.maxval(res)>1.e-12_rk)stop 1
 do i=1,nf
 call build_dynamic_stiffness(nn,z,2,sh,1,disk,2,nodes,coeff(:,:,i),183._rk,freq(i),M,C,G,K,Mb,Cb,Kb,D,status)
 if(status/=0)stop 2
 if(maxval(abs(real(D)-(K-freq(i)**2*M)))>1.e-8_rk)stop 3
 if(maxval(abs(aimag(D)-freq(i)*(C+183*G)))>1.e-8_rk)stop 4
 H=cmplx(hr(:,:,i),hi(:,:,i),rk)
 if(maxval(abs(matmul(D,H)-Id))>1.e-9_rk)stop 5
 if(maxval(abs(cmplx(vr(:,:,i),vi(:,:,i),rk)-cmplx(0._rk,freq(i),rk)*H))>1.e-12_rk)stop 6
 if(maxval(abs(cmplx(ar(:,:,i),ai(:,:,i),rk)+freq(i)**2*H))>1.e-12_rk)stop 7
 enddo
 old=aimag(D)
 call build_dynamic_stiffness(nn,z,2,sh,1,disk,2,nodes,coeff(:,:,2),-183._rk,freq(2),M,C,G,K,Mb,Cb,Kb,D,status)
 if(maxval(abs(old-aimag(D)-2*freq(2)*183*G))>1.e-8_rk)stop 8
 call general_frf(nn,z,2,sh,1,disk,2,nodes,nf,freq,2,183._rk,coeff,hr,hi,vr,vi,ar,ai,res,status)
 old=hr(:,:,2)
 call general_frf(nn,z,2,sh,1,disk,2,nodes,nf,freq,1,0._rk,coeff,hr,hi,vr,vi,ar,ai,res,status)
 if(status/=0.or.any(old/=hr(:,:,2)))stop 9
 call general_frf(nn,z,2,sh,1,disk,2,nodes,nf,freq,0,0._rk,coeff,hr,hi,vr,vi,ar,ai,res,status)
 if(status/=0.or.maxval(abs(old-hr(:,:,2)))<1.e-12_rk)stop 10
 coeff=0
 call general_frf(nn,z,2,sh,1,disk,2,nodes,nf,freq,0,0._rk,coeff,hr,hi,vr,vi,ar,ai,res,status)
 if(status/=30)stop 11
 freq(1)=ieee_value(0._rk,ieee_quiet_nan)
 call general_frf(nn,z,2,sh,1,disk,2,nodes,nf,freq,0,0._rk,coeff,hr,hi,vr,vi,ar,ai,res,status)
 if(status/=10)stop 12
 if(frf_size_valid(128,10000).or.frf_size_valid(3,0))stop 13
 print *,'PASS general FRF matrices/complex solve/identities/policies/invalid/singular'
end program
