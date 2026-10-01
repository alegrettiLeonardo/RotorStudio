program test_irdin_support_analysis
 use rd_kinds,only:rk,ik
 use rd_status,only:RD_OK
 use rd_irdin_support_analysis,only:irdin_expanded_modal,irdin_expanded_synchronous
 implicit none(type,external)
 real(rk)::m(4,4),c(4,4),k(4,4),res,mag(1),phase(1),tol
 complex(rk)::w(8),v(4,8),q(4)
 integer(ik)::st,nodes(1)
 real(rk)::freq(8)
 integer::i
 tol=1.e-11_rk
 m=0._rk;c=0._rk;k=0._rk
 do i=1,4;m(i,i)=1._rk;enddo
 k(1,1)=4._rk;k(2,2)=9._rk;k(3,3)=16._rk;k(4,4)=25._rk
 call irdin_expanded_modal(m,c,k,w,v,st)
 if(st/=RD_OK)error stop 1
 do i=1,8;freq(i)=abs(w(i));enddo
 if(abs(freq(1)-2._rk)>tol.or.abs(freq(2)-2._rk)>tol)error stop 2
 if(abs(freq(3)-3._rk)>tol.or.abs(freq(4)-3._rk)>tol)error stop 3

 k=0._rk;k(1,1)=100._rk;k(2,2)=120._rk;k(3,3)=140._rk;k(4,4)=160._rk
 nodes=[1_ik];mag=[0.1_rk];phase=[0._rk]
 call irdin_expanded_synchronous(1_ik,m,c,k,2._rk,1_ik,nodes,mag,phase,q,res,st)
 if(st/=RD_OK)error stop 4
 if(abs(real(q(1),rk))>tol.or.abs(aimag(q(1))+0.4_rk/96._rk)>tol)error stop 5
 if(abs(real(q(2),rk)-0.4_rk/116._rk)>tol.or.abs(aimag(q(2)))>tol)error stop 6
 if(res>1.e-13_rk)error stop 7
 print *,"PASS: iRdin expanded modal and synchronous native solvers"
end program
