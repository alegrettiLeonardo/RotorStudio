program test_irdin_support
  use rd_kinds, only: rk, ik
  use rd_irdin_support, only: irdin_support_matrices, I4_OK, I4_INVALID_INPUT
  implicit none(type, external)
  real(rk) :: kb(2,2),cb(2,2),ks(2,2),cs(2,2),m(4,4),c(4,4),k(4,4)
  integer(ik) :: status
  kb=reshape([10.0_rk,30.0_rk,20.0_rk,40.0_rk],[2,2])
  cb=reshape([1.0_rk,3.0_rk,2.0_rk,4.0_rk],[2,2])
  ks=reshape([100.0_rk,300.0_rk,200.0_rk,400.0_rk],[2,2])
  cs=reshape([11.0_rk,13.0_rk,12.0_rk,14.0_rk],[2,2])
  call irdin_support_matrices(kb,cb,ks,cs,5.0_rk,m,c,k,status)
  if(status/=I4_OK) error stop 1
  if(m(3,3)/=5.0_rk .or. m(4,4)/=5.0_rk) error stop 2
  if(maxval(abs(k(1:2,1:2)-kb))>0.0_rk) error stop 3
  if(maxval(abs(k(1:2,3:4)+kb))>0.0_rk) error stop 4
  if(maxval(abs(k(3:4,1:2)+kb))>0.0_rk) error stop 5
  if(maxval(abs(k(3:4,3:4)-(kb+ks)))>0.0_rk) error stop 6
  if(maxval(abs(c(1:2,1:2)-cb))>0.0_rk) error stop 7
  if(maxval(abs(c(3:4,3:4)-(cb+cs)))>0.0_rk) error stop 8
  if(k(1,2)/=20.0_rk .or. k(2,1)/=30.0_rk) error stop 9
  call irdin_support_matrices(kb,cb,ks,cs,0.0_rk,m,c,k,status)
  if(status/=I4_INVALID_INPUT) error stop 10
  print *,"IRDIN_I4_SUPPORT_NATIVE_PASS"
end program test_irdin_support
