! SPDX-License-Identifier: Apache-2.0
! ROSS-derived element formulas: Copyright 2022 Petroleo Brasileiro S.A.
! Native Fortran translation for RotorStudio B1, 2026.
! Authority: petrobras/ross@6320eab9f890f1b3cc1710d508b446fe063ca68d
! Mapping: shaft_element.py __init__, M, K, G, Kst. See validation/b1/NATIVE.md.
! This is an isolated element kernel; it does not call the legacy 4-DOF kernel.
module rd_shaft_6dof
  use iso_c_binding, only: c_double, c_int
  use, intrinsic :: ieee_arithmetic, only: ieee_is_finite
  use, intrinsic :: ieee_exceptions
  implicit none(type, external)
  private
  integer, parameter :: dp=c_double
  integer(c_int), parameter, public :: B1_OK=0, B1_INVALID_INPUT=10, B1_INVALID_ENUM=11
  integer(c_int), parameter, public :: B1_INVALID_DIMENSION=12, B1_INSUFFICIENT_CAPACITY=13, B1_NONFINITE_RESULT=14
  public :: shaft_6dof_matrices
contains
  subroutine shaft_6dof_matrices(L,idl,odl,idr,odr,rho,E,Gs,axial_force,torque,shear,rotary,gyro,method,Mo,Ko,Go,So,status)
    real(dp), intent(in) :: L,idl,odl,idr,odr,rho,E,Gs,axial_force,torque
    integer(c_int), intent(in) :: shear,rotary,gyro,method
    real(dp), intent(inout) :: Mo(12,12),Ko(12,12),Go(12,12),So(12,12)
    integer(c_int), intent(out) :: status
    real(dp) :: M(12,12),K(12,12),G(12,12),S(12,12)
    type(ieee_status_type) :: saved_ieee
    logical :: good
    status=B1_INVALID_INPUT
    if (.not.all(ieee_is_finite([L,idl,odl,idr,odr,rho,E,Gs,axial_force,torque]))) return
    if (L<=0 .or. rho<=0 .or. E<=0 .or. Gs<=0) return
    if (idl<0 .or. idr<0 .or. odl<=idl .or. odr<=idr) return
    status=B1_INVALID_ENUM
    if (shear<0 .or. shear>1 .or. rotary<0 .or. rotary>1 .or. gyro<0 .or. gyro>1) return
    if (method/=1 .and. method/=2) return
    ! Finite inputs can still overflow in geometry or constitutive arithmetic.
    ! Restore the caller's IEEE flags/modes after the isolated computation,
    ! including in Debug builds compiled with floating-point halting enabled.
    call ieee_get_status(saved_ieee)
    if (ieee_support_halting(ieee_invalid)) call ieee_set_halting_mode(ieee_invalid,.false.)
    if (ieee_support_halting(ieee_divide_by_zero)) call ieee_set_halting_mode(ieee_divide_by_zero,.false.)
    if (ieee_support_halting(ieee_overflow)) call ieee_set_halting_mode(ieee_overflow,.false.)
    call compute_shaft(L,idl,odl,idr,odr,rho,E,Gs,axial_force,torque,shear,rotary,gyro,method,M,K,G,S)
    good=all(ieee_is_finite(M)) .and. all(ieee_is_finite(K)) .and. all(ieee_is_finite(G)) .and. all(ieee_is_finite(S))
    call ieee_set_status(saved_ieee)
    status=B1_NONFINITE_RESULT
    if (.not.good) return
    Mo=M; Ko=K; Go=G; So=S
    status=B1_OK
  end subroutine

  pure subroutine add_planes(A,Q)
    real(dp), intent(inout) :: A(12,12)
    real(dp), intent(in) :: Q(4,4)
    integer, parameter :: ix(4)=[1,5,7,11], iy(4)=[2,4,8,10]
    real(dp), parameter :: s(4)=[1._dp,-1._dp,1._dp,-1._dp]
    integer :: i,j
    do j=1,4
      do i=1,4
        A(ix(i),ix(j))=A(ix(i),ix(j))+Q(i,j)
        A(iy(i),iy(j))=A(iy(i),iy(j))+s(i)*Q(i,j)*s(j)
      end do
    end do
  end subroutine

  pure subroutine compute_shaft(L,idl,odl,idr,odr,rho,E,Gs,F,T,shear,rotary,gyro,method,M,K,G,Kst)
    real(dp), intent(in) :: L,idl,odl,idr,odr,rho,E,Gs,F,T
    integer(c_int), intent(in) :: shear,rotary,gyro,method
    real(dp), intent(out) :: M(12,12),K(12,12),G(12,12),Kst(12,12)
    real(dp) :: pi,Al,Ar,Il,Ir,Amid,Imid,Ae,Je,roj,rij,rok,rik,dro,dri
    real(dp) :: a1,a2,b1,b2,gama,delta,nu,r,r2,r12,kappa,phi,p2
    real(dp) :: m1,m2,m3,m4,m5,m6,m7,m8,m9,m10,g1,g2,g3,g4,g5,g6
    real(dp) :: k1,k2,k3,k4,k5,k6,k7,k8,k9,k10,k11,k12,k13
    real(dp) :: Q(4,4),Qr(4,4),Q1(4,4),Q2(4,4),Qt(12,12),v
    integer, parameter :: ix(4)=[1,5,7,11], iy(4)=[2,4,8,10]
    real(dp), parameter :: signs(4)=[1._dp,-1._dp,1._dp,-1._dp]
    integer :: i,j
    M=0; K=0; G=0; Kst=0
    pi=acos(-1._dp)
    Al=pi*(odl**2-idl**2)/4; Ar=pi*(odr**2-idr**2)/4
    Il=pi*(odl**4-idl**4)/64; Ir=pi*(odr**4-idr**4)/64
    roj=odl/2; rij=idl/2; rok=odr/2; rik=idr/2
    dro=rok-roj; dri=rik-rij
    a1=2*pi*(roj*dro-rij*dri)/Al
    a2=pi*(roj**3*dro-rij**3*dri)/Il
    b1=pi*(dro**2-dri**2)/Al
    b2=3*pi*(roj**2*dro**2-rij**2*dri**2)/(2*Il)
    gama=pi*(roj*dro**3-rij*dri**3)/Il
    delta=pi*(dro**4-dri**4)/(4*Il)
    Amid=Al*(1+a1*0.5_dp+b1*0.5_dp**2)
    Imid=Il*(1+a2*0.5_dp+b2*0.5_dp**2+gama*0.5_dp**3+delta*0.5_dp**4)
    phi=0
    if (shear==1) then
      nu=E/(2*Gs)-1
      r=((idl+idr)/2)/((odl+odr)/2); r2=r*r; r12=(1+r2)**2
      if (method==1) then
        kappa=6*r12*((1+nu)/(r12*(7+6*nu)+r2*(20+12*nu)))
      else
        kappa=6*r12*((1+nu)/(r12*(7+12*nu+4*nu**2)+4*r2*(5+6*nu+2*nu**2)))
      end if
      phi=12*E*Imid/(Gs*kappa*Amid*L**2)
    end if
    p2=phi**2
    ! Consistent lateral mass, source M coefficients m1..m10.
    m1=(468+882*phi+420*p2)+a1*(108+210*phi+105*p2)+b1*(38+78*phi+42*p2)
    m2=((66+115.5_dp*phi+52.5_dp*p2)+a1*(21+40.5_dp*phi+21*p2)+b1*(8.5_dp+18*phi+10.5_dp*p2))*L
    m3=(162+378*phi+210*p2)+a1*(81+189*phi+105*p2)+b1*(46+111*phi+63*p2)
    m4=((39+94.5_dp*phi+52.5_dp*p2)+a1*(18+40.5_dp*phi+21*p2)+b1*(9.5_dp+21*phi+10.5_dp*p2))*L
    m5=((12+21*phi+10.5_dp*p2)+a1*(4.5_dp+9*phi+5.25_dp*p2)+b1*(2+4.5_dp*phi+3*p2))*L**2
    m6=((39+94.5_dp*phi+52.5_dp*p2)+a1*(21+54*phi+31.5_dp*p2)+b1*(12.5_dp+34.5_dp*phi+21*p2))*L
    m7=((9+21*phi+10.5_dp*p2)+a1*(4.5_dp+10.5_dp*phi+5.25_dp*p2)+b1*(2.5_dp+6*phi+3*p2))*L**2
    m8=(468+882*phi+420*p2)+a1*(360+672*phi+315*p2)+b1*(290+540*phi+252*p2)
    m9=((66+115.5_dp*phi+52.5_dp*p2)+a1*(45+75*phi+31.5_dp*p2)+b1*(32.5_dp+52.5_dp*phi+21*p2))*L
    m10=((12+21*phi+10.5_dp*p2)+a1*(7.5_dp+12*phi+5.25_dp*p2)+b1*(5+7.5_dp*phi+3*p2))*L**2
    Q(1,:)=[m1,m2,m3,-m4]; Q(2,:)=[m2,m5,m6,-m7]
    Q(3,:)=[m3,m6,m8,-m9]; Q(4,:)=[-m4,-m7,-m9,m10]
    Q=Q*rho*Al*L/(1260*(1+phi)**2)
    call add_planes(M,Q)
    ! These scalar polynomials occur in both rotary M and G in the source.
    ! G is computed independently of the rotary-inertia flag and of M output.
    g1=252+126*a2+72*b2+45*gama+30*delta
    g2=(21-105*phi+a2*(21-42*phi)+b2*(15-21*phi)+gama*(10.5_dp-12*phi)+delta*(7.5_dp-7.5_dp*phi))*L
    g3=(21-105*phi-63*a2*phi-b2*(6+42*phi)-gama*(7.5_dp+30*phi)-delta*(7.5_dp+22.5_dp*phi))*L
    g4=(28+35*phi+70*p2+a2*(7-7*phi+17.5_dp*p2)+b2*(4-7*phi+7*p2)+gama*(2.75_dp-5*phi+3.5_dp*p2)+delta*(2-3.5_dp*phi+2*p2))*L**2
    g5=(7+35*phi-35*p2+a2*(3.5_dp+17.5_dp*phi-17.5_dp*p2)+b2*(3+10.5_dp*phi-10.5_dp*p2)+gama*(2.75_dp+7*phi-7*p2)+delta*(2.5_dp+5*phi-5*p2))*L**2
    g6=(28+35*phi+70*p2+a2*(21+42*phi+52.5_dp*p2)+b2*(18+42*phi+42*p2)+gama*(16.25_dp+40*phi+35*p2)+delta*(15+37.5_dp*phi+30*p2))*L**2
    Qr(1,:)=[g1,g2,-g1,g3]; Qr(2,:)=[g2,g4,-g2,-g5]
    Qr(3,:)=[-g1,-g2,g1,-g3]; Qr(4,:)=[g3,-g5,-g3,g6]
    if (rotary==1) then
      Q=Qr*rho*Il/(210*L*(1+phi)**2)
      call add_planes(M,Q)
    end if
    if (gyro==1) then
      Q=Qr*rho*Il*2/(210*L*(1+phi)**2)
      do j=1,4
        do i=1,4
          G(ix(i),iy(j))=Q(i,j)*signs(j)
          G(iy(j),ix(i))=-G(ix(i),iy(j))
        end do
      end do
    end if
    ! Endpoint means, not exact-frustum integration, including tapered cases.
    Ae=(Al+Ar)/2; Je=Il+Ir
    v=rho*Ae*L/6
    M(3,3)=2*v; M(3,9)=v; M(9,3)=v; M(9,9)=2*v
    v=rho*Je*L/6
    M(6,6)=2*v; M(6,12)=v; M(12,6)=v; M(12,12)=2*v
    ! Elastic stiffness: retain the source's separate taper/shear contributions.
    k1=1260+630*a2+504*b2+441*gama+396*delta
    k2=(630+210*a2+147*b2+126*gama+114*delta-phi*(105*a2+105*b2+94.5_dp*gama+84*delta))*L
    k3=(630+420*a2+357*b2+315*gama+282*delta+phi*(105*a2+105*b2+94.5_dp*gama+84*delta))*L
    k4=(420+210*phi+105*p2+a2*(105+52.5_dp*p2)+b2*(56-35*phi+35*p2)+gama*(42-42*phi+26.25_dp*p2)+delta*(36-42*phi+21*p2))*L**2
    k5=(210-210*phi-105*p2+a2*(105-105*phi-52.5_dp*p2)+b2*(91-70*phi-35*p2)+gama*(84-52.5_dp*phi-26.25_dp*p2)+delta*(78-42*phi-21*p2))*L**2
    k6=(420+210*phi+105*p2+a2*(315+210*phi+52.5_dp*p2)+b2*(266+175*phi+35*p2)+gama*(231+147*phi+26.25_dp*p2)+delta*(204+126*phi+21*p2))*L**2
    k7=12+6*a1+4*b1; k8=(6+3*a1+2*b1)*L; k9=(3+1.5_dp*a1+b1)*L**2
    Q1(1,:)=[k1,k2,-k1,k3]; Q1(2,:)=[k2,k4,-k2,k5]
    Q1(3,:)=[-k1,-k2,k1,-k3]; Q1(4,:)=[k3,k5,-k3,k6]
    Q1=Q1*Il/105
    Q2(1,:)=[k7,k8,-k7,k8]; Q2(2,:)=[k8,k9,-k8,k9]
    Q2(3,:)=[-k7,-k8,k7,-k8]; Q2(4,:)=[k8,k9,-k8,k9]
    Q2=Q2*Imid*phi*Al/Amid
    Q=E*L**(-3)*(1+phi)**(-2)*(Q1+Q2)
    call add_planes(K,Q)
    k10=36+60*phi+30*p2; k11=3*L
    k12=(4+5*phi+2.5_dp*p2)*L**2; k13=(1+5*phi+2.5_dp*p2)*L**2
    Q(1,:)=[k10,k11,-k10,k11]; Q(2,:)=[k11,k12,-k11,-k13]
    Q(3,:)=[-k10,-k11,k10,-k11]; Q(4,:)=[k11,-k13,-k11,k12]
    Q=Q*F/(30*L*(1+phi)**2)
    call add_planes(K,Q)
    ! Nonconservative torque terms: deliberately not symmetrized.
    Qt=0
    Qt(1,4)=1; Qt(1,10)=-1; Qt(2,5)=1; Qt(2,11)=-1
    Qt(4,1)=1; Qt(4,5)=-L/2; Qt(4,7)=-1; Qt(4,11)=L/2
    Qt(5,2)=1; Qt(5,4)=L/2; Qt(5,8)=-1; Qt(5,10)=-L/2
    Qt(7,4)=-1; Qt(7,10)=1; Qt(8,5)=-1; Qt(8,11)=1
    Qt(10,1)=-1; Qt(10,5)=-L/2; Qt(10,7)=1; Qt(10,11)=L/2
    Qt(11,2)=-1; Qt(11,4)=L/2; Qt(11,8)=1; Qt(11,10)=-L/2
    K=K+Qt*T/L
    v=E*Ae/L; K(3,3)=v; K(3,9)=-v; K(9,3)=-v; K(9,9)=v
    v=Gs*Je/L; K(6,6)=v; K(6,12)=-v; K(12,6)=-v; K(12,12)=v
    ! Independent acceleration coefficient Kst, source Kst(), NOT legacy K1.
    Q(1,:)=[-36._dp,3*L,36._dp,3*L]
    Q(2,:)=[-3*L,4*L**2,3*L,-L**2]
    Q(3,:)=[36._dp,-3*L,-36._dp,-3*L]
    Q(4,:)=[-3*L,-L**2,3*L,4*L**2]
    Q=Q*rho*((Il+Ir)/2)/(15*L)
    do j=1,4
      do i=1,4
        Kst(ix(i),iy(j))=Q(i,j)
      end do
    end do
  end subroutine
end module rd_shaft_6dof
