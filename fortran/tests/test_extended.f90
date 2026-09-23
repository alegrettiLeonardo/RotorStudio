program test_extended
 use rd_kinds,only:rk,ik
 use rd_status,only:RD_OK,RD_ERR_UNSUPPORTED
 use rd_shaft_circular,only:shaft_circular_matrices
 use rd_shaft_tapered,only:shaft_tapered_matrices
 use rd_shaft_asymmetric,only:shaft_asymmetric_matrices
 implicit none(type,external)
 real(rk)::M1(8,8),G1(8,8),K1(8,8),D1(8,8),M2(8,8),G2(8,8),K2(8,8),D2(8,8),scale,err
 integer(ik)::st1,st2
 integer::t
 do t=1,8
  call shaft_circular_matrices(int(t,ik),.3_rk,.08_rk,.02_rk,2.1e11_rk,8.1e10_rk,7800._rk,0._rk,0._rk,M1,G1,K1,D1,st1)
  call shaft_tapered_matrices(int(20+t,ik),.3_rk,.08_rk,.08_rk,.02_rk,.02_rk,2.1e11_rk,8.1e10_rk,7800._rk,0._rk,M2,G2,K2,D2,st2)
  if(st1/=RD_OK.or.st2/=RD_OK)error stop 1
  scale=max(1._rk,maxval(abs(M1)));err=maxval(abs(M1-M2))/scale;if(err>2e-12_rk)error stop 2
  scale=max(1._rk,maxval(abs(K1)));err=maxval(abs(K1-K2))/scale;if(err>2e-12_rk)error stop 3
  scale=max(1._rk,maxval(abs(G1)));err=maxval(abs(G1-G2))/scale;if(err>2e-12_rk)error stop 4
 enddo
 call shaft_asymmetric_matrices(12_ik,.2_rk,1e5_rk,1.2e5_rk,.1_rk,.1_rk,12._rk,.01_rk,0._rk,M1,G1,K1,D1,st1)
 if(st1/=RD_OK)error stop 5
 if(maxval(abs(M1-transpose(M1)))>1e-10_rk*max(1._rk,maxval(abs(M1))))error stop 6
 call shaft_asymmetric_matrices(12_ik,.2_rk,1e5_rk,1.2e5_rk,.1_rk,.1_rk,12._rk,.01_rk,1._rk,M1,G1,K1,D1,st1)
 if(st1/=RD_ERR_UNSUPPORTED)error stop 7
 print *,'PASS extended shaft tests'
end program
