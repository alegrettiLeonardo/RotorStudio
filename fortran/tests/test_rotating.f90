program test_rotating
 use rd_kinds,only:rk,ik
 use rd_status,only:RD_OK
 use rd_assembly_rotating,only:assemble_bearings_rotating
 implicit none(type,external)
 real(rk)::b(34,1),C(4,4),K(4,4),K1(4,4);logical::iz(4);integer(ik)::st
 b=0;b(1,1)=4;b(2,1)=1;b(3,1)=1e6_rk;b(4,1)=1e6_rk;b(5,1)=2e4_rk;b(6,1)=2e4_rk;b(7,1)=100;b(8,1)=100;b(9,1)=5;b(10,1)=5
 call assemble_bearings_rotating(1_ik,1_ik,b,C,K,K1,iz,st)
 if(st/=RD_OK)error stop 1
 if(K1(1,2)/=-100._rk)error stop 2
 if(K1(2,1)/=5._rk)error stop 3
 if(K1(3,4)/=-5._rk)error stop 4
 if(K1(4,3)/=0._rk)error stop 5
 print *,'PASS rotating bearing V2-compatibility smoke'
end program
