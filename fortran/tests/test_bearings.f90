program test_bearings
 use rd_kinds,only:rk,ik
 use rd_status,only:RD_OK
 use rd_assembly_stationary,only:assemble_bearings
 implicit none(type,external)
 real(rk)::b(34,1),M(4,4),C(4,4),K(4,4),ecc(1)
 logical::iz(4);integer(ik)::st
 b=0;b(1,1)=3;b(2,1)=1;b(3,1)=11;b(4,1)=22;b(5,1)=3;b(6,1)=4
 call assemble_bearings(1_ik,1_ik,b,100._rk,M,C,K,iz,st,ecc)
 if(st/=RD_OK)error stop 1
 if(K(1,1)/=11._rk.or.K(2,2)/=22._rk.or.C(1,1)/=3._rk.or.C(2,2)/=4._rk)error stop 2
 b=0;b(1,1)=7;b(2,1)=1;b(3,1)=1200;b(4,1)=.06_rk;b(5,1)=.025_rk;b(6,1)=60e-6_rk;b(7,1)=.018_rk
 call assemble_bearings(1_ik,1_ik,b,320._rk,M,C,K,iz,st,ecc)
 if(st/=RD_OK)error stop 3
 if(.not.(ecc(1)>0._rk.and.ecc(1)<1._rk))error stop 4
 if(any(.not.(K==K)).or.any(.not.(C==C)))error stop 5
 b=0;b(1,1)=20;b(2,1)=1;b(3,1)=1
 call assemble_bearings(1_ik,1_ik,b,100._rk,M,C,K,iz,st,ecc)
 if(st/=RD_OK)error stop 6
 if(maxval(abs(M))+maxval(abs(C))+maxval(abs(K))/=0._rk)error stop 7
 print *,'PASS bearing source-formula smoke'
end program
