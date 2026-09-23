module rd_shaft_circular
  use rd_kinds, only: rk, ik
  use rd_status, only: RD_OK, RD_ERR_INPUT, RD_ERR_UNSUPPORTED
  implicit none(type, external)
  private
  public :: shaft_circular_matrices
contains
  subroutine shaft_circular_matrices(stype,L,do_,di,E,G,rho,axial,torque,M,Cg,K,K1,status)
    integer(ik), intent(in) :: stype
    real(rk), intent(in) :: L,do_,di,E,G,rho,axial,torque
    real(rk), intent(out) :: M(8,8),Cg(8,8),K(8,8),K1(8,8)
    integer(ik), intent(out) :: status
    logical :: shear, rotary, gyro
    real(rk) :: pi_,I,A,nu,r,r2,r12,kappa,phi
    real(rk) :: m1,m2,m3,m4,m5,m6,m7,m8,m9,m10,g1,g2,g3,g4,k1a,k2,k3,k4
    real(rk) :: Ms(8,8), KF(8,8), KT(8,8)
    pi_=acos(-1.0_rk); M=0; Cg=0; K=0; K1=0; status=RD_OK
    if (stype<1 .or. stype>8 .or. L<=0 .or. do_<=di .or. di<0 .or. E<=0 .or. rho<=0) then
      status=RD_ERR_INPUT; return
    end if
    shear = .not.(stype==1 .or. stype==5 .or. stype==7 .or. stype==8)
    if (G==0) shear=.false.
    if (shear .and. G<0) then; status=RD_ERR_INPUT; return; end if
    rotary = .not.(stype==1 .or. stype==4 .or. stype==6 .or. stype==8)
    gyro = .not.(stype==3 .or. stype==6 .or. stype==7 .or. stype==8)
    I=0.015625_rk*pi_*(do_**4-di**4); A=0.25_rk*pi_*(do_**2-di**2)
    if (shear) then
      nu=0.5_rk*(E/G)-1.0_rk; r=di/do_; r2=r*r; r12=(1+r2)**2
      kappa=6*r12*(1+nu)/(r12*(7+6*nu)+r2*(20+12*nu))
      phi=12*E*I/(G*kappa*A*L*L)
    else
      phi=0
    end if
    K = reshape([ &
      12._rk,0._rk,0._rk,6*L,-12._rk,0._rk,0._rk,6*L, &
      0._rk,12._rk,-6*L,0._rk,0._rk,-12._rk,-6*L,0._rk, &
      0._rk,-6*L,(4+phi)*L*L,0._rk,0._rk,6*L,(2-phi)*L*L,0._rk, &
      6*L,0._rk,0._rk,(4+phi)*L*L,-6*L,0._rk,0._rk,(2-phi)*L*L, &
      -12._rk,0._rk,0._rk,-6*L,12._rk,0._rk,0._rk,-6*L, &
      0._rk,-12._rk,6*L,0._rk,0._rk,12._rk,6*L,0._rk, &
      0._rk,-6*L,(2-phi)*L*L,0._rk,0._rk,6*L,(4+phi)*L*L,0._rk, &
      6*L,0._rk,0._rk,(2-phi)*L*L,-6*L,0._rk,0._rk,(4+phi)*L*L ],[8,8],order=[2,1])
    K=E*I*K/((1+phi)*L**3)
    m1=312+588*phi+280*phi**2; m2=(44+77*phi+35*phi**2)*L
    m3=108+252*phi+140*phi**2; m4=-(26+63*phi+35*phi**2)*L
    m5=(8+14*phi+7*phi**2)*L**2; m6=-(6+14*phi+7*phi**2)*L**2
    M = reshape([ &
      m1,0._rk,0._rk,m2,m3,0._rk,0._rk,m4, &
      0._rk,m1,-m2,0._rk,0._rk,m3,-m4,0._rk, &
      0._rk,-m2,m5,0._rk,0._rk,m4,m6,0._rk, &
      m2,0._rk,0._rk,m5,-m4,0._rk,0._rk,m6, &
      m3,0._rk,0._rk,-m4,m1,0._rk,0._rk,-m2, &
      0._rk,m3,m4,0._rk,0._rk,m1,m2,0._rk, &
      0._rk,-m4,m6,0._rk,0._rk,m2,m5,0._rk, &
      m4,0._rk,0._rk,m6,-m2,0._rk,0._rk,m5 ],[8,8],order=[2,1])
    M=rho*A*L*M/(840*(1+phi)**2)
    if (rotary) then
      m7=36; m8=(3-15*phi)*L; m9=(4+5*phi+10*phi**2)*L**2; m10=(-1-5*phi+5*phi**2)*L**2
      Ms=reshape([ &
        m7,0._rk,0._rk,m8,-m7,0._rk,0._rk,m8, &
        0._rk,m7,-m8,0._rk,0._rk,-m7,-m8,0._rk, &
        0._rk,-m8,m9,0._rk,0._rk,m8,m10,0._rk, &
        m8,0._rk,0._rk,m9,-m8,0._rk,0._rk,m10, &
        -m7,0._rk,0._rk,-m8,m7,0._rk,0._rk,-m8, &
        0._rk,-m7,m8,0._rk,0._rk,m7,m8,0._rk, &
        0._rk,-m8,m10,0._rk,0._rk,m8,m9,0._rk, &
        m8,0._rk,0._rk,m10,-m8,0._rk,0._rk,m9 ],[8,8],order=[2,1])
      M=M+rho*I*Ms/(30*L*(1+phi)**2)
    end if
    if (gyro) then
      g1=36; g2=(3-15*phi)*L; g3=(4+5*phi+10*phi**2)*L**2; g4=(-1-5*phi+5*phi**2)*L**2
      Cg=reshape([ &
        0._rk,-g1,g2,0._rk,0._rk,g1,g2,0._rk, &
        g1,0._rk,0._rk,g2,-g1,0._rk,0._rk,g2, &
        -g2,0._rk,0._rk,-g3,g2,0._rk,0._rk,-g4, &
        0._rk,-g2,g3,0._rk,0._rk,g2,g4,0._rk, &
        0._rk,g1,-g2,0._rk,0._rk,-g1,-g2,0._rk, &
        -g1,0._rk,0._rk,-g2,g1,0._rk,0._rk,-g2, &
        -g2,0._rk,0._rk,-g4,g2,0._rk,0._rk,-g3, &
        0._rk,-g2,g4,0._rk,0._rk,g2,g3,0._rk ],[8,8],order=[2,1])
      Cg=-rho*I*Cg/(15*L*(1+phi)**2)
    end if
    if (axial/=0) then
      k1a=72+120*phi+60*phi**2; k2=6*L; k3=(8+10*phi+5*phi**2)*L**2; k4=(-2-10*phi-5*phi**2)*L**2
      KF=reshape([ &
        k1a,0._rk,0._rk,k2,-k1a,0._rk,0._rk,k2, &
        0._rk,k1a,-k2,0._rk,0._rk,-k1a,-k2,0._rk, &
        0._rk,-k2,k3,0._rk,0._rk,k2,k4,0._rk, &
        k2,0._rk,0._rk,k3,-k2,0._rk,0._rk,k4, &
        -k1a,0._rk,0._rk,-k2,k1a,0._rk,0._rk,-k2, &
        0._rk,-k1a,k2,0._rk,0._rk,k1a,k2,0._rk, &
        0._rk,-k2,k4,0._rk,0._rk,k2,k3,0._rk, &
        k2,0._rk,0._rk,k4,-k2,0._rk,0._rk,k3 ],[8,8],order=[2,1])
      K=K+axial*KF/(60*L*(1+phi)**2)
    end if
    if (torque/=0) then
      KT=reshape([ &
       0._rk,0._rk,1._rk,0._rk,0._rk,0._rk,-1._rk,0._rk, &
       0._rk,0._rk,0._rk,1._rk,0._rk,0._rk,0._rk,-1._rk, &
       1._rk,0._rk,0._rk,-L/2,-1._rk,0._rk,0._rk,L/2, &
       0._rk,1._rk,L/2,0._rk,0._rk,-1._rk,-L/2,0._rk, &
       0._rk,0._rk,-1._rk,0._rk,0._rk,0._rk,1._rk,0._rk, &
       0._rk,0._rk,0._rk,-1._rk,0._rk,0._rk,0._rk,1._rk, &
       -1._rk,0._rk,0._rk,-L/2,1._rk,0._rk,0._rk,L/2, &
       0._rk,-1._rk,L/2,0._rk,0._rk,1._rk,-L/2,0._rk ],[8,8],order=[2,1])
      K=K+torque*KT/L
    end if
    K1=reshape([ &
      0._rk,12._rk,-6*L,0._rk,0._rk,-12._rk,-6*L,0._rk, &
      -12._rk,0._rk,0._rk,-6*L,12._rk,0._rk,0._rk,-6*L, &
      6*L,0._rk,0._rk,(4+phi)*L*L,-6*L,0._rk,0._rk,(2-phi)*L*L, &
      0._rk,6*L,-(4+phi)*L*L,0._rk,0._rk,-6*L,-(2-phi)*L*L,0._rk, &
      0._rk,-12._rk,6*L,0._rk,0._rk,12._rk,6*L,0._rk, &
      12._rk,0._rk,0._rk,6*L,-12._rk,0._rk,0._rk,6*L, &
      6*L,0._rk,0._rk,(2-phi)*L*L,-6*L,0._rk,0._rk,(4+phi)*L*L, &
      0._rk,6*L,-(2-phi)*L*L,0._rk,0._rk,-6*L,-(4+phi)*L*L,0._rk ],[8,8],order=[2,1])
    K1=E*I*K1/((1+phi)*L**3)
  end subroutine
end module rd_shaft_circular
