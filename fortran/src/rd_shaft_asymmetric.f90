module rd_shaft_asymmetric
 use rd_kinds,only:rk,ik
 use rd_status,only:RD_OK,RD_ERR_INPUT,RD_ERR_UNSUPPORTED
 implicit none(type,external);private;public::shaft_asymmetric_matrices
contains
 subroutine shaft_asymmetric_matrices(stype,L,EIx,EIy,Phix_in,Phiy_in,rhoA,rhoI,axial,M,C1,K0,K2,status)
  integer(ik),intent(in)::stype;real(rk),intent(in)::L,EIx,EIy,Phix_in,Phiy_in,rhoA,rhoI,axial
  real(rk),intent(out)::M(8,8),C1(8,8),K0(8,8),K2(8,8);integer(ik),intent(out)::status
  logical::shear,rotary,gyro;real(rk)::px,py,m1,m2,m3,m4,m5,m6,m7,m8,m9,m10
  real(rk)::Kx(4,4),Ky(4,4),Ms(8,8),Cs(8,8),Ge(8,8),G1(8,8);integer::ix(4),iy(4)
  M=0;C1=0;K0=0;K2=0;status=RD_OK
  if(stype<11.or.stype>18.or.L<=0.or.EIx<=0.or.EIy<=0.or.rhoA<=0.or.rhoI<0)then;status=RD_ERR_INPUT;return;endif
  if(axial/=0)then;status=RD_ERR_UNSUPPORTED;return;endif
  shear=.not.(stype==11.or.stype==15.or.stype==17.or.stype==18);rotary=.not.(stype==11.or.stype==14.or.stype==16.or.stype==18);gyro=.not.(stype==13.or.stype==16.or.stype==17.or.stype==18)
  px=merge(Phix_in,0._rk,shear);py=merge(Phiy_in,0._rk,shear);ix=[1,4,5,8];iy=[2,3,6,7]
  Kx=reshape([12._rk,6*L,-12._rk,6*L,6*L,(4+px)*L*L,-6*L,(2-px)*L*L,-12._rk,-6*L,12._rk,-6*L,6*L,(2-px)*L*L,-6*L,(4+px)*L*L],[4,4],order=[2,1])*EIx/((1+px)*L**3)
  Ky=reshape([12._rk,-6*L,-12._rk,-6*L,-6*L,(4+py)*L*L,6*L,(2-py)*L*L,-12._rk,6*L,12._rk,6*L,-6*L,(2-py)*L*L,6*L,(4+py)*L*L],[4,4],order=[2,1])*EIy/((1+py)*L**3)
  K0(ix,ix)=Kx;K0(iy,iy)=Ky
  m1=156;m2=22*L;m3=54;m4=-13*L;m5=4*L**2;m6=-3*L**2
  M=reshape([m1,0._rk,0._rk,m2,m3,0._rk,0._rk,m4,0._rk,m1,-m2,0._rk,0._rk,m3,-m4,0._rk,0._rk,-m2,m5,0._rk,0._rk,m4,m6,0._rk,m2,0._rk,0._rk,m5,-m4,0._rk,0._rk,m6,m3,0._rk,0._rk,-m4,m1,0._rk,0._rk,-m2,0._rk,m3,m4,0._rk,0._rk,m1,m2,0._rk,0._rk,-m4,m6,0._rk,0._rk,m2,m5,0._rk,m4,0._rk,0._rk,m6,-m2,0._rk,0._rk,m5],[8,8],order=[2,1])*rhoA*L/420
  K2=-M
  C1=reshape([0._rk,-m1,m2,0._rk,0._rk,-m3,m4,0._rk,m1,0._rk,0._rk,m2,m3,0._rk,0._rk,m4,-m2,0._rk,0._rk,-m5,m4,0._rk,0._rk,-m6,0._rk,-m2,m5,0._rk,0._rk,m4,m6,0._rk,0._rk,-m3,-m4,0._rk,0._rk,-m1,-m2,0._rk,m3,0._rk,0._rk,-m4,m1,0._rk,0._rk,-m2,-m4,0._rk,0._rk,-m6,m2,0._rk,0._rk,-m5,0._rk,-m4,m6,0._rk,0._rk,m2,m5,0._rk],[8,8],order=[2,1])*rhoA*L/210
  if(rotary)then
    m7=36;m8=3*L;m9=4*L**2;m10=-L**2
    Ms=reshape([m7,0._rk,0._rk,m8,-m7,0._rk,0._rk,m8,0._rk,m7,-m8,0._rk,0._rk,-m7,-m8,0._rk,0._rk,-m8,m9,0._rk,0._rk,m8,m10,0._rk,m8,0._rk,0._rk,m9,-m8,0._rk,0._rk,m10,-m7,0._rk,0._rk,-m8,m7,0._rk,0._rk,-m8,0._rk,-m7,m8,0._rk,0._rk,m7,m8,0._rk,0._rk,-m8,m10,0._rk,0._rk,m8,m9,0._rk,m8,0._rk,0._rk,m10,-m8,0._rk,0._rk,m9],[8,8],order=[2,1])
    Ms=rhoI*Ms/(30*L);M=M+Ms
    Cs=reshape([0._rk,-m7,m8,0._rk,0._rk,m7,m8,0._rk,m7,0._rk,0._rk,m8,-m7,0._rk,0._rk,m8,-m8,0._rk,0._rk,-m9,m8,0._rk,0._rk,-m10,0._rk,-m8,m9,0._rk,0._rk,m8,m10,0._rk,0._rk,m7,-m8,0._rk,0._rk,-m7,-m8,0._rk,-m7,0._rk,0._rk,-m8,m7,0._rk,0._rk,-m8,-m8,0._rk,0._rk,-m10,m8,0._rk,0._rk,-m9,0._rk,-m8,m10,0._rk,0._rk,m8,m9,0._rk],[8,8],order=[2,1])
    Cs=rhoI*Ms/(15*L);C1=C1+Cs
  endif
  if(gyro)then
    m7=36;m8=3*L;m9=4*L**2;m10=-L**2
    Ge=reshape([0._rk,-m7,m8,0._rk,0._rk,m7,m8,0._rk,m7,0._rk,0._rk,m8,-m7,0._rk,0._rk,m8,-m8,0._rk,0._rk,-m9,m8,0._rk,0._rk,-m10,0._rk,-m8,m9,0._rk,0._rk,m8,m10,0._rk,0._rk,m7,-m8,0._rk,0._rk,-m7,-m8,0._rk,-m7,0._rk,0._rk,-m8,m7,0._rk,0._rk,-m8,-m8,0._rk,0._rk,-m10,m8,0._rk,0._rk,-m9,0._rk,-m8,m10,0._rk,0._rk,m8,m9,0._rk],[8,8],order=[2,1])
    C1=C1-rhoI*Ge/(15*L)
    G1=reshape([m7,0._rk,0._rk,m8,-m7,0._rk,0._rk,m8,0._rk,m7,-m8,0._rk,0._rk,-m7,-m8,0._rk,0._rk,-m8,m9,0._rk,0._rk,m10,m10,0._rk,m8,0._rk,0._rk,m9,-m10,0._rk,0._rk,m10,-m7,0._rk,0._rk,-m8,m7,0._rk,0._rk,-m8,0._rk,-m7,m8,0._rk,0._rk,m7,m8,0._rk,0._rk,-m8,m10,0._rk,0._rk,m8,m9,0._rk,m8,0._rk,0._rk,m10,-m8,0._rk,0._rk,m9],[8,8],order=[2,1])
    K2=K2+2*rhoI*G1/(15*L)
  endif
 end subroutine
end module rd_shaft_asymmetric
