program test_assembly
  use rd_kinds,only:rk,ik
  use rd_status,only:RD_OK
  use rd_assembly_stationary,only:assemble_rotor
  use rd_bearings,only:assemble_bearings
  implicit none(type,external)
  real(rk)::z(3),shaft(11,2),disc(6,1),bear(34,2)
  real(rk)::M(12,12),C0(12,12),C1(12,12),K0(12,12),K1(12,12),Mb(12,12),Cb(12,12),Kb(12,12),ecc(2)
  logical::iz(12)
  integer(ik)::st
  integer::i
  real(rk)::tol
  z=[0._rk,0.4_rk,0.8_rk];shaft=0._rk;disc=0._rk;bear=0._rk;tol=1e-10_rk
  shaft(:,1)=[2._rk,1._rk,2._rk,.05_rk,0._rk,7800._rk,2.1e11_rk,8.1e10_rk,2e-5_rk,0._rk,0._rk]
  shaft(:,2)=[22._rk,2._rk,3._rk,.05_rk,.04_rk,0._rk,0._rk,7800._rk,2.1e11_rk,8.1e10_rk,500._rk]
  disc(:,1)=[1._rk,2._rk,7800._rk,.05_rk,.25_rk,.05_rk]
  bear(1,1)=3;bear(2,1)=1;bear(3,1)=1e6;bear(4,1)=1.2e6;bear(5,1)=100;bear(6,1)=120
  bear(1,2)=3;bear(2,2)=3;bear(3,2)=1.1e6;bear(4,2)=1.3e6;bear(5,2)=110;bear(6,2)=130
  call assemble_rotor(3_ik,z,2_ik,shaft,1_ik,disc,M,C0,C1,K0,K1,st)
  if(st/=RD_OK) error stop 1
  call assemble_bearings(3_ik,2_ik,bear,100._rk,Mb,Cb,Kb,iz,ecc,st)
  if(st/=RD_OK) error stop 2
  if(maxval(abs(M-transpose(M)))>tol*max(1._rk,maxval(abs(M)))) error stop 3
  if(maxval(abs(C0-transpose(C0)))>tol*max(1._rk,maxval(abs(C0)))) error stop 4
  if(maxval(abs(K0-transpose(K0)))>tol*max(1._rk,maxval(abs(K0)))) error stop 5
  if(maxval(abs(C1+transpose(C1)))>tol*max(1._rk,maxval(abs(C1)))) error stop 6
  if(maxval(abs(K1+transpose(K1)))>tol*max(1._rk,maxval(abs(K1)))) error stop 7
  if(any([(M(i,i)<=0._rk,i=1,12)])) error stop 8
  if(maxval(abs(Kb-transpose(Kb)))>tol*max(1._rk,maxval(abs(Kb)))) error stop 9
  if(maxval(abs(Cb-transpose(Cb)))>tol*max(1._rk,maxval(abs(Cb)))) error stop 10
  print *, 'PASS stationary M/C0/C1/K0/K1 assembly invariants for mixed circular+tapered rotor'
end program test_assembly
