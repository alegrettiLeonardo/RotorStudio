module rd_shaft_asymmetric
  use rd_kinds, only: rk, ik
  use rd_status, only: RD_OK, RD_ERR_INPUT, RD_ERR_LEGACY_DEFECT
  implicit none(type, external)
  private
  public :: shaft_asymmetric_matrices
contains
  subroutine shaft_asymmetric_matrices(stype,L,EIx,EIy,Phix_in,Phiy_in,rhoA,rhoI,axial,M,C1,K0,K2,status)
    integer(ik),intent(in) :: stype
    real(rk),intent(in) :: L,EIx,EIy,Phix_in,Phiy_in,rhoA,rhoI,axial
    real(rk),intent(out) :: M(8,8),C1(8,8),K0(8,8),K2(8,8)
    integer(ik),intent(out) :: status
    logical :: shear,rotary,gyro
    real(rk) :: Phix,Phiy
    real(rk) :: Kx(4,4),Ky(4,4),Mx(8,8),Ms(8,8),Cs(8,8),Ge(8,8),G1e(8,8)
    real(rk) :: m1,m2,m3,m4,m5,m6,m7,m8,m9,m10,sk1,sk2,sk3,sk4
    integer :: ix(4),iy(4),i,j

    M=0._rk; C1=0._rk; K0=0._rk; K2=0._rk; status=RD_OK
    if (stype<11 .or. stype>18 .or. L<=0._rk .or. EIx<=0._rk .or. EIy<=0._rk .or. rhoA<=0._rk .or. rhoI<0._rk) then
      status=RD_ERR_INPUT; return
    end if

    ! Rotor_Software_v2/shftasym.m writes the axial-load contribution to
    ! undefined Kre. Until an executable MATLAB/Octave baseline is available,
    ! preserve that branch as an explicit legacy-defect status rather than
    ! silently changing the numerical authority.
    if (axial/=0._rk) then
      status=RD_ERR_LEGACY_DEFECT; return
    end if

    shear=.not.(stype==11 .or. stype==15 .or. stype==17 .or. stype==18)
    rotary=.not.(stype==11 .or. stype==14 .or. stype==16 .or. stype==18)
    gyro=.not.(stype==13 .or. stype==16 .or. stype==17 .or. stype==18)
    Phix=Phix_in; Phiy=Phiy_in
    if (.not.shear) then
      Phix=0._rk; Phiy=0._rk
    end if
    if (Phix<0._rk .or. Phiy<0._rk) then
      status=RD_ERR_INPUT; return
    end if

    Kx=reshape([ &
      12._rk,6._rk*L,-12._rk,6._rk*L, &
      6._rk*L,(4._rk+Phix)*L*L,-6._rk*L,(2._rk-Phix)*L*L, &
      -12._rk,-6._rk*L,12._rk,-6._rk*L, &
      6._rk*L,(2._rk-Phix)*L*L,-6._rk*L,(4._rk+Phix)*L*L ],[4,4],order=[2,1])
    Kx=EIx*Kx/((1._rk+Phix)*L**3)
    Ky=reshape([ &
      12._rk,-6._rk*L,-12._rk,-6._rk*L, &
      -6._rk*L,(4._rk+Phiy)*L*L,6._rk*L,(2._rk-Phiy)*L*L, &
      -12._rk,6._rk*L,12._rk,6._rk*L, &
      -6._rk*L,(2._rk-Phiy)*L*L,6._rk*L,(4._rk+Phiy)*L*L ],[4,4],order=[2,1])
    Ky=EIy*Ky/((1._rk+Phiy)*L**3)
    ix=[1,4,5,8]; iy=[2,3,6,7]
    do i=1,4
      do j=1,4
        K0(ix(i),ix(j))=Kx(i,j)
        K0(iy(i),iy(j))=Ky(i,j)
      end do
    end do

    m1=156._rk; m2=22._rk*L; m3=54._rk; m4=-13._rk*L
    m5=4._rk*L**2; m6=-3._rk*L**2
    Mx=reshape([ &
      m1,0._rk,0._rk,m2,m3,0._rk,0._rk,m4, &
      0._rk,m1,-m2,0._rk,0._rk,m3,-m4,0._rk, &
      0._rk,-m2,m5,0._rk,0._rk,m4,m6,0._rk, &
      m2,0._rk,0._rk,m5,-m4,0._rk,0._rk,m6, &
      m3,0._rk,0._rk,-m4,m1,0._rk,0._rk,-m2, &
      0._rk,m3,m4,0._rk,0._rk,m1,m2,0._rk, &
      0._rk,-m4,m6,0._rk,0._rk,m2,m5,0._rk, &
      m4,0._rk,0._rk,m6,-m2,0._rk,0._rk,m5 ],[8,8],order=[2,1])
    M=rhoA*L*Mx/420._rk
    K2=-M
    C1=reshape([ &
      0._rk,-m1,m2,0._rk,0._rk,-m3,m4,0._rk, &
      m1,0._rk,0._rk,m2,m3,0._rk,0._rk,m4, &
      -m2,0._rk,0._rk,-m5,m4,0._rk,0._rk,-m6, &
      0._rk,-m2,m5,0._rk,0._rk,m4,m6,0._rk, &
      0._rk,-m3,-m4,0._rk,0._rk,-m1,-m2,0._rk, &
      m3,0._rk,0._rk,-m4,m1,0._rk,0._rk,-m2, &
      -m4,0._rk,0._rk,-m6,m2,0._rk,0._rk,-m5, &
      0._rk,-m4,m6,0._rk,0._rk,m2,m5,0._rk ],[8,8],order=[2,1])
    C1=rhoA*L*C1/210._rk

    if (rotary) then
      m7=36._rk; m8=3._rk*L; m9=4._rk*L**2; m10=-L**2
      Ms=reshape([ &
        m7,0._rk,0._rk,m8,-m7,0._rk,0._rk,m8, &
        0._rk,m7,-m8,0._rk,0._rk,-m7,-m8,0._rk, &
        0._rk,-m8,m9,0._rk,0._rk,m8,m10,0._rk, &
        m8,0._rk,0._rk,m9,-m8,0._rk,0._rk,m10, &
        -m7,0._rk,0._rk,-m8,m7,0._rk,0._rk,-m8, &
        0._rk,-m7,m8,0._rk,0._rk,m7,m8,0._rk, &
        0._rk,-m8,m10,0._rk,0._rk,m8,m9,0._rk, &
        m8,0._rk,0._rk,m10,-m8,0._rk,0._rk,m9 ],[8,8],order=[2,1])
      Ms=rhoI*Ms/(30._rk*L)
      M=M+Ms

      ! Preserve V2 exactly: shftasym.m constructs a skew Cs and then
      ! immediately overwrites it with rhoI*Ms/(15*L). This is intentionally
      ! not "corrected" without MATLAB execution evidence.
      Cs=rhoI*Ms/(15._rk*L)
      C1=C1+Cs
    end if

    if (gyro) then
      sk1=36._rk; sk2=3._rk*L; sk3=4._rk*L**2; sk4=-L**2
      Ge=reshape([ &
        0._rk,-sk1,sk2,0._rk,0._rk,sk1,sk2,0._rk, &
        sk1,0._rk,0._rk,sk2,-sk1,0._rk,0._rk,sk2, &
        -sk2,0._rk,0._rk,-sk3,sk2,0._rk,0._rk,-sk4, &
        0._rk,-sk2,sk3,0._rk,0._rk,sk2,sk4,0._rk, &
        0._rk,sk1,-sk2,0._rk,0._rk,-sk1,-sk2,0._rk, &
        -sk1,0._rk,0._rk,-sk2,sk1,0._rk,0._rk,-sk2, &
        -sk2,0._rk,0._rk,-sk4,sk2,0._rk,0._rk,-sk3, &
        0._rk,-sk2,sk4,0._rk,0._rk,sk2,sk3,0._rk ],[8,8],order=[2,1])
      C1=C1-rhoI*Ge/(15._rk*L)
      G1e=reshape([ &
        sk1,0._rk,0._rk,sk2,-sk1,0._rk,0._rk,sk2, &
        0._rk,sk1,-sk2,0._rk,0._rk,-sk1,-sk2,0._rk, &
        0._rk,-sk2,sk3,0._rk,0._rk,sk4,sk4,0._rk, &
        sk2,0._rk,0._rk,sk3,-sk4,0._rk,0._rk,sk4, &
        -sk1,0._rk,0._rk,-sk2,sk1,0._rk,0._rk,-sk2, &
        0._rk,-sk1,sk2,0._rk,0._rk,sk1,sk2,0._rk, &
        0._rk,-sk2,sk4,0._rk,0._rk,sk2,sk3,0._rk, &
        sk2,0._rk,0._rk,sk4,-sk2,0._rk,0._rk,sk3 ],[8,8],order=[2,1])
      K2=K2+2._rk*rhoI*G1e/(15._rk*L)
    end if
  end subroutine shaft_asymmetric_matrices
end module rd_shaft_asymmetric
