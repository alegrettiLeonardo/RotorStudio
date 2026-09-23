program test_bearings
  use, intrinsic :: ieee_arithmetic, only: ieee_is_finite
  use rd_kinds,only:rk,ik
  use rd_status,only:RD_OK,RD_ERR_INPUT
  use rd_bearings,only:assemble_bearings
  implicit none(type,external)
  real(rk)::bear(34,9),Mb(36,36),Cb(36,36),Kb(36,36),ecc(9),b7(34,1),M2(4,4),C2(4,4),K2(4,4),e2(1)
  logical::iz(36),iz2(4)
  integer(ik)::st
  integer::j,k,c
  bear=0._rk
  bear(1,1)=1;bear(2,1)=1
  bear(1,2)=2;bear(2,2)=2
  bear(1,3)=3;bear(2,3)=3;bear(3:6,3)=[11._rk,12._rk,13._rk,14._rk]
  bear(1,4)=4;bear(2,4)=4;bear(3:10,4)=[21._rk,22._rk,23._rk,24._rk,25._rk,26._rk,27._rk,28._rk]
  bear(1,5)=5;bear(2,5)=5;bear(3:10,5)=[31._rk,32._rk,33._rk,34._rk,35._rk,36._rk,37._rk,38._rk]
  bear(1,6)=6;bear(2,6)=6;c=0
  do j=1,4;do k=1,4;c=c+1;bear(2+(j-1)*4+k,6)=100._rk+c;bear(18+(j-1)*4+k,6)=200._rk+c;enddo;enddo
  bear(1,7)=7;bear(2,7)=7;bear(3,7)=1000;bear(4,7)=0.08;bear(5,7)=0.04;bear(6,7)=8e-5;bear(7,7)=0.02
  bear(1,8)=8;bear(2,8)=8;bear(3,8)=1e6;bear(4,8)=0.04;bear(5,8)=0.02;bear(6,8)=2e-4;bear(7,8)=10;bear(8,8)=0.02
  bear(1,9)=20;bear(2,9)=9
  call assemble_bearings(9_ik,9_ik,bear,200._rk,Mb,Cb,Kb,iz,ecc,st)
  if(st/=RD_OK) error stop 1
  if(.not.all(iz(1:2)) .or. any(iz(3:4))) error stop 2
  if(.not.all(iz(5:8))) error stop 3
  if(Kb(9,9)/=11._rk .or. Kb(10,10)/=12._rk .or. Cb(9,9)/=13._rk .or. Cb(10,10)/=14._rk) error stop 4
  if(Kb(13,13)/=21._rk .or. Kb(16,16)/=24._rk .or. Cb(13,13)/=25._rk .or. Cb(16,16)/=28._rk) error stop 5
  if(Kb(17,18)/=32._rk .or. Kb(18,17)/=33._rk .or. Cb(17,18)/=36._rk .or. Cb(18,17)/=37._rk) error stop 6
  if(Kb(21,22)/=102._rk .or. Kb(22,21)/=105._rk .or. Cb(21,22)/=202._rk .or. Cb(22,21)/=205._rk) error stop 7
  if(.not.(ecc(7)>0._rk.and.ecc(7)<1._rk) .or. ecc(8)/=0._rk) error stop 8
  if(.not.all(ieee_is_finite(Mb)) .or. .not.all(ieee_is_finite(Cb)) .or. .not.all(ieee_is_finite(Kb))) error stop 9
  if(maxval(abs(Mb(29:32,29:32)))<=0._rk) error stop 10
  if(maxval(abs(Kb(33:36,33:36)))>0._rk .or. maxval(abs(Cb(33:36,33:36)))>0._rk) error stop 11

  b7=0._rk;b7(1,1)=7;b7(2,1)=1;b7(3,1)=1000;b7(4,1)=0.08;b7(5,1)=0.04;b7(6,1)=8e-5;b7(7,1)=0.02;b7(8,1)=1
  call assemble_bearings(1_ik,1_ik,b7,200._rk,M2,C2,K2,iz2,e2,st)
  if(st/=RD_OK .or. maxval(abs(C2))>0._rk .or. maxval(abs(K2))>0._rk) error stop 12
  call assemble_bearings(1_ik,1_ik,b7,0._rk,M2,C2,K2,iz2,e2,st)
  if(st/=RD_ERR_INPUT) error stop 13
  print *, 'PASS bearmtx legacy types 1-8/20 + nonlinear type-7 suppression + zero-speed gate'
end program test_bearings
