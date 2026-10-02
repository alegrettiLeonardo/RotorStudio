program test_api541_torsional_response
  use rd_kinds, only: rk, ik
  use rd_status, only: RD_OK, RD_ERR_INPUT
  use rd_api541_torsional_response, only: api541_torsional_harmonic_response
  implicit none(type, external)
  real(rk)::jv(2),kt(1),ct(1),omega(1),fr(2,1),fi(2,1)
  real(rk)::qr(2,1),qi(2,1),tr(1,1),ti(1,1)
  integer(ik)::status

  jv=[2._rk,3._rk]
  kt=[120._rk]
  ct=[0._rk]
  omega=[5._rk]
  fr(:,1)=[1._rk,-1._rk]
  fi=0._rk

  call api541_torsional_harmonic_response(2_ik,jv,kt,ct,1_ik,omega,fr,fi,qr,qi,tr,ti,status)
  if(status/=RD_OK)error stop 1
  if(abs(qr(1,1)-1._rk/150._rk)>1.e-12_rk)error stop 2
  if(abs(qr(2,1)+1._rk/225._rk)>1.e-12_rk)error stop 3
  if(any(abs(qi)>1.e-13_rk))error stop 4
  if(abs(tr(1,1)-4._rk/3._rk)>1.e-12_rk)error stop 5
  if(abs(ti(1,1))>1.e-13_rk)error stop 6

  omega=[0._rk]
  call api541_torsional_harmonic_response(2_ik,jv,kt,ct,1_ik,omega,fr,fi,qr,qi,tr,ti,status)
  if(status/=RD_ERR_INPUT)error stop 7

  print *,"PASS: API541 harmonic torsional response"
end program
