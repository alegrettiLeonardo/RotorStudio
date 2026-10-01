program test_irdin_support_global
 use rd_kinds,only:rk,ik
 use rd_irdin_support_global,only:irdin_support_global_matrices,I8_OK,I8_INVALID_INPUT
 implicit none(type,external)
 integer(ik)::st,nodes(1)
 real(rk)::mass(1),kb(2,2,1),cb(2,2,1),ks(2,2,1),cs(2,2,1)
 real(rk)::mr(8,8),cr(8,8),gr(8,8),kr(8,8),m(10,10),c(10,10),g(10,10),k(10,10)
 mr=0;cr=0;gr=0;kr=0;mr(1,1)=7;gr(3,4)=2
 nodes=[2_ik];mass=[5._rk]
 kb(:,:,1)=reshape([10._rk,30._rk,20._rk,40._rk],[2,2])
 cb(:,:,1)=reshape([1._rk,3._rk,2._rk,4._rk],[2,2])
 ks(:,:,1)=reshape([100._rk,0._rk,0._rk,200._rk],[2,2]);cs(:,:,1)=0
 call irdin_support_global_matrices(2_ik,1_ik,nodes,mass,kb,cb,ks,cs,mr,cr,gr,kr,m,c,g,k,st)
 if(st/=I8_OK)error stop 1
 if(m(1,1)/=7._rk.or.m(9,9)/=5._rk.or.m(10,10)/=5._rk)error stop 2
 if(k(5,5)/=10._rk.or.k(5,9)/=-10._rk.or.k(9,5)/=-10._rk.or.k(9,9)/=110._rk)error stop 3
 if(k(5,6)/=20._rk.or.k(6,5)/=30._rk)error stop 4
 if(c(5,9)/=-1._rk.or.c(6,9)/=-3._rk)error stop 5
 if(g(3,4)/=2._rk.or.any(g(9:10,:)/=0._rk).or.any(g(:,9:10)/=0._rk))error stop 6
 nodes=[3_ik]
 call irdin_support_global_matrices(2_ik,1_ik,nodes,mass,kb,cb,ks,cs,mr,cr,gr,kr,m,c,g,k,st)
 if(st/=I8_INVALID_INPUT)error stop 7
 print *,"PASS: iRdin global support matrix composition"
end program
