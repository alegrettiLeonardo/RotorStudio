program test_api541_torsional
  use rd_kinds, only: rk, ik
  use rd_status, only: RD_OK, RD_ERR_INPUT
  use rd_api541_torsional, only: api541_torsional_modes
  implicit none(type, external)
  real(rk)::j(2),kt(1),ct(1),m(2,2),c(2,2),k(2,2),freq(2),modes(2,2)
  real(rk)::ortho
  integer(ik)::status

  j=[2._rk,3._rk]
  kt=[120._rk]
  ct=[0._rk]

  call api541_torsional_modes(2_ik,j,kt,ct,m,c,k,freq,modes,status)
  if(status/=RD_OK)error stop 1
  if(abs(m(1,1)-2._rk)>1.e-14_rk .or. abs(m(2,2)-3._rk)>1.e-14_rk)error stop 2
  if(abs(k(1,1)-120._rk)>1.e-14_rk .or. abs(k(1,2)+120._rk)>1.e-14_rk)error stop 3
  if(abs(k(2,1)+120._rk)>1.e-14_rk .or. abs(k(2,2)-120._rk)>1.e-14_rk)error stop 4
  if(any(abs(c)>0._rk))error stop 5
  if(abs(freq(1))>1.e-7_rk)error stop 6
  ! sqrt(k*(1/J1+1/J2)) = sqrt(120*(1/2+1/3)) = 10 rad/s.
  if(abs(freq(2)-10._rk)>1.e-10_rk)error stop 7
  ortho=j(1)*modes(1,1)*modes(1,2)+j(2)*modes(2,1)*modes(2,2)
  if(abs(ortho)>1.e-10_rk)error stop 8

  j(1)=0._rk
  call api541_torsional_modes(2_ik,j,kt,ct,m,c,k,freq,modes,status)
  if(status/=RD_ERR_INPUT)error stop 9

  print *,"PASS: API541 torsional matrices and two-inertia modes"
end program
