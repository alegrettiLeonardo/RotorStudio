program test_taper
  use rd_kinds,only:rk,ik
  use rd_status,only:RD_OK
  use rd_shaft_circular,only:shaft_circular_matrices
  use rd_shaft_tapered,only:shaft_tapered_matrices
  implicit none(type,external)
  real(rk)::Mc(8,8),Gc(8,8),Kc(8,8),K1c(8,8),Mt(8,8),Gt(8,8),Kt(8,8),K1t(8,8)
  real(rk)::tol,scale,axial
  integer(ik)::s1,s2
  integer::t
  tol=3e-12_rk
  axial=0._rk
  do t=1,8
    call shaft_circular_matrices(int(t,ik),0.31_rk,0.08_rk,0.025_rk,2.05e11_rk,7.9e10_rk,7800._rk, &
      axial,0._rk,Mc,Gc,Kc,K1c,s1)
    call shaft_tapered_matrices(int(t+20,ik),0.31_rk,0.08_rk,0.08_rk,0.025_rk,0.025_rk,2.05e11_rk, &
      7.9e10_rk,7800._rk,axial,Mt,Gt,Kt,K1t,s2)
    if(s1/=RD_OK.or.s2/=RD_OK) error stop 1
    scale=max(1._rk,maxval(abs(Mc)));if(maxval(abs(Mt-Mc))>tol*scale) error stop 2
    scale=max(1._rk,maxval(abs(Gc)));if(maxval(abs(Gt-Gc))>tol*scale) error stop 3
    scale=max(1._rk,maxval(abs(Kc)));if(maxval(abs(Kt-Kc))>tol*scale) error stop 4
    if(maxval(abs(K1t))>tol) error stop 5
  end do
  call shaft_tapered_matrices(22_ik,0.31_rk,0.09_rk,0.055_rk,0.02_rk,0.005_rk,2.05e11_rk,7.9e10_rk, &
    7800._rk,1500._rk,Mt,Gt,Kt,K1t,s2)
  if(s2/=RD_OK) error stop 6
  if(maxval(abs(Mt-transpose(Mt)))>1e-11_rk*max(1._rk,maxval(abs(Mt)))) error stop 7
  if(maxval(abs(Kt-transpose(Kt)))>1e-11_rk*max(1._rk,maxval(abs(Kt)))) error stop 8
  if(maxval(abs(Gt+transpose(Gt)))>1e-11_rk*max(1._rk,maxval(abs(Gt)))) error stop 9
  print *, 'PASS taper: constant-section equivalence (zero axial) + axial/nonuniform + nonuniform invariants'
end program test_taper
