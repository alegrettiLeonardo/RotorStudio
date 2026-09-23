program test_transient
  use rd_kinds, only: rk,ik
  use rd_status, only: RD_OK
  use rd_dp45, only: dp45_time_fdn_grid
  use rd_reduction, only: modal_truncation
  implicit none(type,external)
  real(rk)::XK(1,1),XC(1,1),B2(1),B1(1),B0(1),y0(2),te(2),yo(2,2)
  integer(ik)::na,nrj,st,nru
  real(rk)::M(2,2),K(2,2),mf
  real(rk),allocatable::Tr(:,:),ev(:)
  XK=1._rk;XC=0._rk;B2=0._rk;B1=0._rk;B0=0._rk;y0=[1._rk,0._rk];te=[0._rk,acos(-1._rk)/2]
  call dp45_time_fdn_grid(XK,XC,B2,B1,B0,1._rk,y0,te,1e-10_rk,1e-12_rk,0._rk,0._rk,yo,na,nrj,st)
  if(st/=RD_OK)error stop 1
  if(abs(yo(1,2))>2e-9_rk)error stop 2
  if(abs(yo(2,2)+1._rk)>2e-9_rk)error stop 3
  M=0;K=0;M(1,1)=2;M(2,2)=1;K(1,1)=8;K(2,2)=9
  call modal_truncation(M,K,1_ik,Tr,ev,nru,mf,st)
  if(st/=RD_OK.or.nru/=1)error stop 4
  if(abs(ev(1)-4._rk)>1e-12_rk.or.abs(ev(2)-9._rk)>1e-12_rk)error stop 5
  if(abs(mf-1._rk/acos(-1._rk))>1e-12_rk)error stop 6
  print *,'PASS DP45 and V2 modal truncation primitives'
end program
