program test_static
 use, intrinsic::ieee_arithmetic,only:ieee_value,ieee_quiet_nan
 use rd_kinds,only:rk,ik
 use rd_status,only:RD_OK,RD_ERR_INPUT,RD_ERR_LAPACK,RD_ERR_UNSUPPORTED
 use rd_static,only:static_solve
 implicit none(type,external)
 integer(ik)::st
 integer::i
 real(rk)::z(7),sh(11,6),di(6,2),be(34,3),q(28),rx(7),sw(6),dw(2),v(12),bm(12),x(12),dg(3),qbase(28),EI,w,expected
 do i=1,7;z(i)=real(i-1,rk)*.25_rk;enddo
 sh=0
 do i=1,6;sh(:,i)=[1._rk,real(i,rk),real(i+1,rk),.05_rk,0._rk,7810._rk,211.e9_rk,81.2e9_rk,0._rk,0._rk,0._rk];enddo
 di=0;di(:,1)=[2._rk,3._rk,12.3_rk,.04_rk,.08_rk,0._rk];di(:,2)=[2._rk,5._rk,9.7_rk,.04_rk,.08_rk,0._rk]
 be=0;be(1,1:2)=1;be(2,1)=1;be(2,2)=7
 call run(6,2,2);call check(st==RD_OK,'uniform/multiple disks');call balances()
 qbase=q
 be(1,3)=8;be(2,3)=4
 call run(6,2,3);call check(st==RD_OK,'seals accepted/excluded');call check(maxval(abs(q-qbase))<1e-20_rk,'seal changes displacement')
 call run(6,0,2);call check(st==RD_OK,'no disk');call balances()
 EI=211.e9_rk*acos(-1._rk)*.05_rk**4/64
 w=7810._rk*acos(-1._rk)*.05_rk**2/4*9.8065_rk
 expected=-5*w*1.5_rk**4/(384*EI)
 call check(abs(q(14)-expected)<1e-12_rk,'analytical uniform midspan deformation')
 call check(abs(rx(1)-w*1.5_rk/2)<1e-9_rk,'analytical reaction')
 be(1,3)=1;be(2,3)=4
 call run(6,2,3);call check(st==RD_OK,'three supports');call balances()
 do i=1,6;sh(4,i)=.04_rk+.003_rk*i;enddo
 be(2,1)=2;be(2,2)=5
 call run(6,2,2);call check(st==RD_OK,'stepped/overhung');call balances()
 call run(6,2,0);call check(st==RD_ERR_INPUT,'no bearing rejected')
 call run(6,2,1);call check(st==RD_ERR_LAPACK,'singular single support rejected')
 be(1,:)=8
 call run(6,2,3);call check(st==RD_ERR_INPUT,'seals-only rejected')
 be(1,:)=1;sh(4,1)=-1
 call run(6,2,2);call check(st==RD_ERR_INPUT,'invalid diameter rejected')
 sh(4,1)=ieee_value(0._rk,ieee_quiet_nan)
 call run(6,2,2);call check(st==RD_ERR_INPUT,'NaN rejected')
 sh(4,1)=.05;sh(1,1)=21
 call run(6,2,2);call check(st==RD_ERR_UNSUPPORTED,'tapered not silently admitted')
 print *, 'PASS static native: analytical, support/seal, overhung, equilibrium, residual, invalid/singular'
contains
 subroutine run(ns,nd,nb)
 integer,intent(in)::ns,nd,nb
 call static_solve(7_ik,z,int(ns,ik),sh(:,1:ns),int(nd,ik),di(:,1:nd),int(nb,ik),be(:,1:nb), &
 q,rx,sw,dw(1:nd),v,bm,x,dg,st)
 end subroutine
 subroutine check(ok,message)
 logical,intent(in)::ok
 character(*),intent(in)::message
 if(.not.ok)then;print *, 'FAIL ',message;error stop 1;endif
 end subroutine
 subroutine balances()
 call check(abs(dg(1))<1e-8_rk,'force balance')
 call check(abs(dg(2))<1e-8_rk,'moment balance')
 call check(dg(3)<1e-14_rk,'scaled residual')
 end subroutine
end program
