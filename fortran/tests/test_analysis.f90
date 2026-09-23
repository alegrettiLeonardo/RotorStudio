program test_analysis
  use, intrinsic :: ieee_arithmetic, only: ieee_is_finite
  use rd_kinds,only:rk,ik
  use rd_status,only:RD_OK
  use rd_frequency_response,only:frequency_response_stationary
  use rd_critical_speed,only:critical_speeds_stationary
  implicit none(type,external)
  real(rk)::z(2),shaft(11,1),disc(6,0),bear(34,2),force(5,1),bend(3,0),speeds(2)
  complex(rk)::resp(8,2),modes1(8,2),modes2(8,2),modes3(8,2)
  real(rk)::crit1(2),crit2(2),crit3(2),initial(2)
  integer(ik)::it1(2),it2(2),it3(2),st
  logical::cv1(2),cv2(2),cv3(2)
  real(rk)::rel
  z=[0._rk,0.5_rk];shaft=0._rk;bear=0._rk;force=0._rk
  shaft(:,1)=[2._rk,1._rk,2._rk,0.05_rk,0._rk,7800._rk,2.0e11_rk,7.9e10_rk,0._rk,0._rk,0._rk]
  bear(1,1)=3;bear(2,1)=1;bear(3,1)=1e6;bear(4,1)=1e6
  bear(1,2)=3;bear(2,2)=2;bear(3,2)=1e6;bear(4,2)=1e6
  force(:,1)=[1._rk,1._rk,1e-4_rk,0.2_rk,0._rk]
  speeds=[100._rk,200._rk]
  call frequency_response_stationary(2_ik,z,1_ik,shaft,0_ik,disc,2_ik,bear,1_ik,force,0_ik,bend,2_ik,speeds,resp,st)
  if(st/=RD_OK) error stop 1
  if(maxval(abs(resp))<=0._rk) error stop 2
  initial=0._rk
  call critical_speeds_stationary(2_ik,z,1_ik,shaft,0_ik,disc,2_ik,bear,1_ik,1._rk,1_ik,2_ik, &
    40_ik,1e-9_rk,initial,crit1,it1,cv1,st,modes1)
  if(st/=RD_OK) error stop 3
  call critical_speeds_stationary(2_ik,z,1_ik,shaft,0_ik,disc,2_ik,bear,2_ik,1._rk,1_ik,2_ik, &
    80_ik,1e-10_rk,initial,crit2,it2,cv2,st,modes2)
  if(st/=RD_OK) error stop 4
  if(.not.all(cv2)) error stop 5
  rel=maxval(abs(crit1-crit2)/max(1._rk,abs(crit1)))
  if(rel>1e-6_rk) then
    print *, 'direct=',crit1,' iterative=',crit2,' rel=',rel
    error stop 6
  end if
  initial=crit1
  call critical_speeds_stationary(2_ik,z,1_ik,shaft,0_ik,disc,2_ik,bear,3_ik,1._rk,1_ik,2_ik, &
    80_ik,1e-10_rk,initial,crit3,it3,cv3,st,modes3)
  if(st/=RD_OK .or. .not.all(cv3)) error stop 7
  if(maxval(abs(crit3-crit1)/max(1._rk,abs(crit1)))>1e-6_rk) error stop 8
  if(.not.all(ieee_is_finite(real(modes1))) .or. maxval(abs(modes1))<=0._rk) error stop 9
  if(.not.all(ieee_is_finite(real(modes2))) .or. maxval(abs(modes2))<=0._rk) error stop 10
  print *, 'PASS freq_rsp smoke + crit_spd methods 1/2/3 consistency + mode shapes'
end program test_analysis
