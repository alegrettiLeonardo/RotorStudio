program test_fault_misalignment
 use rd_kinds,only:rk,ik
 use rd_fault_misalignment,only:flex_force_at,rigid_force_at,C1_OK
 implicit none
 integer(ik)::st
 real(rk)::F1(18),F2(18),F3(18),Fr(18),q(18),phi,pi
 pi=acos(-1._rk);q=0._rk
 call flex_force_at(3_ik,1_ik,0.37_rk,1_ik,0.02_rk,2e-4_rk,1.5e-4_rk,5*pi/180,4e4_rk,3.8e4_rk,0._rk,0._rk,F1,st)
 if(st/=C1_OK)error stop 1
 if(abs(F1(1)+F1(7))>1e-11_rk.or.abs(F1(2)+F1(8))>1e-11_rk)error stop 2
 call flex_force_at(3_ik,1_ik,0.37_rk,2_ik,0.02_rk,2e-4_rk,1.5e-4_rk,5*pi/180,4e4_rk,3.8e4_rk,0._rk,0._rk,F2,st)
 if(st/=C1_OK)error stop 3
 call flex_force_at(3_ik,1_ik,0.37_rk,3_ik,0.02_rk,2e-4_rk,1.5e-4_rk,5*pi/180,4e4_rk,3.8e4_rk,0._rk,0._rk,F3,st)
 if(st/=C1_OK)error stop 4
 if(maxval(abs(F3-(F1+F2)))>1e-12_rk)error stop 5
 call flex_force_at(3_ik,1_ik,0.37_rk,2_ik,0.02_rk,2e-4_rk,1.5e-4_rk,0._rk,4e4_rk,3.8e4_rk,0._rk,0._rk,F2,st)
 if(st/=C1_OK.or.maxval(abs(F2))>1e-12_rk)error stop 6
 phi=-pi/180
 call rigid_force_at(3_ik,1_ik,0.4_rk,0._rk,12._rk,5._rk,1e6_rk,1.2e6_rk,4e4_rk,5e4_rk,q,phi,Fr,st)
 if(st/=C1_OK)error stop 7
 if(abs(Fr(6)-7._rk)>1e-12_rk.or.abs(Fr(12)+7._rk)>1e-12_rk)error stop 8
 if(maxval(abs(Fr([1,2,7,8])))>1e-12_rk)error stop 9
 print *,'C1_MISALIGNMENT_NATIVE_CONTRACT_PASS'
end program
