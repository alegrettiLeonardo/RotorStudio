program test_shaft
 use rd_kinds,only:rk,ik
 use rd_status,only:RD_OK
 use rd_shaft_circular,only:shaft_circular_matrices
 implicit none(type,external)
 real(rk)::M(8,8),Gm(8,8),K(8,8),K1(8,8),tol
 integer(ik)::st
 integer::i
 tol=1e-10_rk
 call shaft_circular_matrices(2_ik,0.2_rk,0.08_rk,0.03_rk,2e11_rk,7.874015748031496e10_rk,7800._rk,0._rk,0._rk,M,Gm,K,K1,st)
 if(st/=RD_OK) error stop 1
 if(maxval(abs(M-transpose(M)))>tol*max(1._rk,maxval(abs(M)))) error stop 2
 if(maxval(abs(K-transpose(K)))>tol*max(1._rk,maxval(abs(K)))) error stop 3
 if(maxval(abs(Gm+transpose(Gm)))>tol*max(1._rk,maxval(abs(Gm)))) error stop 4
 if(maxval(abs(K1+transpose(K1)))>tol*max(1._rk,maxval(abs(K1)))) error stop 5
 if(any([(M(i,i)<=0._rk,i=1,8)])) error stop 6
 print *, 'PASS test_shaft invariants'
end program
