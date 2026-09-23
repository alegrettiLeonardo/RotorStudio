program test_asymmetric
  use, intrinsic :: ieee_arithmetic, only: ieee_is_finite
  use rd_kinds,only:rk,ik
  use rd_status,only:RD_OK,RD_ERR_LEGACY_DEFECT
  use rd_shaft_asymmetric,only:shaft_asymmetric_matrices
  implicit none(type,external)
  real(rk)::M(8,8),C1(8,8),K(8,8),K2(8,8),tol
  integer(ik)::st
  integer::i,t
  tol=1e-10_rk
  do t=11,18
    call shaft_asymmetric_matrices(int(t,ik),0.25_rk,1.1e6_rk,0.9e6_rk,0.12_rk,0.12_rk,15._rk,0.003_rk, &
      0._rk,M,C1,K,K2,st)
    if(st/=RD_OK) error stop 1
    if(maxval(abs(M-transpose(M)))>tol*max(1._rk,maxval(abs(M)))) error stop 2
    if(maxval(abs(K-transpose(K)))>tol*max(1._rk,maxval(abs(K)))) error stop 3
    if(any([(M(i,i)<=0._rk,i=1,8)])) error stop 4
    if(.not.all(ieee_is_finite(C1)) .or. .not.all(ieee_is_finite(K2))) error stop 5
  end do
  call shaft_asymmetric_matrices(12_ik,0.25_rk,1.1e6_rk,0.9e6_rk,0.12_rk,0.12_rk,15._rk,0.003_rk, &
    100._rk,M,C1,K,K2,st)
  if(st/=RD_ERR_LEGACY_DEFECT) error stop 6
  print *, 'PASS shftasym types 11-18 + explicit V2 axial legacy-defect gate'
end program test_asymmetric
