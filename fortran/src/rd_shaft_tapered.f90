module rd_shaft_tapered
  use rd_kinds, only: rk, ik
  use rd_status, only: RD_OK, RD_ERR_INPUT
  implicit none(type, external)
  private
  public :: shaft_tapered_matrices
contains
  subroutine shaft_tapered_matrices(stype,L,doj,dok,dij,dik,E,G_in,rho,axial,M,Cg,K,K1,status)
    integer(ik), intent(in) :: stype
    real(rk), intent(in) :: L,doj,dok,dij,dik,E,G_in,rho,axial
    real(rk), intent(out) :: M(8,8),Cg(8,8),K(8,8),K1(8,8)
    integer(ik), intent(out) :: status
    integer(ik) :: btype
    logical :: shear,rotary,gyro
    real(rk) :: G,pi_,nu,rok,rik,roj,rij,romean,rimean,mu2,Am,Im,kappa,chi
    real(rk) :: Dro,Dri,Aj,Itj,phi,a1,b1,a2,b2,g2,d2
    real(rk) :: sk1,sk2,sk3,sk4,sk5,sk6,sk7,sk8,sk9,sk10,sk11,sk12,sk13
    real(rk) :: m1,m2,m3,m4,m5,m6,m7,m8,m9,m10,m11,m12,m13,m14,m15,m16
    real(rk) :: ka(8,8),kb(8,8),kg(8,8),mt(8,8),mr(8,8),ge(8,8)

    M=0._rk; Cg=0._rk; K=0._rk; K1=0._rk; status=RD_OK
    btype=stype-20_ik
    if (btype<1 .or. btype>8 .or. L<=0._rk .or. E<=0._rk .or. rho<=0._rk) then
      status=RD_ERR_INPUT; return
    end if
    if (doj<=dij .or. dok<=dik .or. dij<0._rk .or. dik<0._rk .or. doj<=0._rk .or. dok<=0._rk) then
      status=RD_ERR_INPUT; return
    end if

    shear = .not.(btype==1 .or. btype==5 .or. btype==7 .or. btype==8)
    G=G_in
    if (.not.shear .or. G==0._rk) then
      shear=.false.
      G=E/2.6_rk
    else if (G<0._rk) then
      status=RD_ERR_INPUT; return
    end if
    rotary=.not.(btype==1 .or. btype==4 .or. btype==6 .or. btype==8)
    gyro=.not.(btype==3 .or. btype==6 .or. btype==7 .or. btype==8)

    pi_=acos(-1._rk)
    nu=0.5_rk*(E/G)-1._rk
    rok=dok/2._rk; rik=dik/2._rk; roj=doj/2._rk; rij=dij/2._rk
    romean=(rok+roj)/2._rk; rimean=(rik+rij)/2._rk
    mu2=(rimean/romean)**2
    Am=pi_*(romean**2-rimean**2)
    Im=pi_*(romean**4-rimean**4)/4._rk
    kappa=6._rk*(1._rk+nu)*(1._rk+mu2)**2 / &
      ((7._rk+6._rk*nu)*(1._rk+mu2)**2+(20._rk+12._rk*nu)*mu2)
    chi=1._rk/kappa
    Dro=rok-roj; Dri=rik-rij
    Aj=pi_*(doj**2-dij**2)/4._rk
    Itj=pi_*(doj**4-dij**4)/64._rk
    if (Aj<=0._rk .or. Itj<=0._rk .or. Am<=0._rk) then
      status=RD_ERR_INPUT; return
    end if
    phi=12._rk*E*Im*chi/(G*Am*L**2)
    if (.not.shear) phi=0._rk

    a1=2._rk*pi_*(roj*Dro-rij*Dri)/Aj
    b1=pi_*(Dro**2-Dri**2)/Aj
    a2=pi_*(roj**3*Dro-rij**3*Dri)/Itj
    b2=3._rk*pi_*(roj**2*Dro**2-rij**2*Dri**2)/(2._rk*Itj)
    g2=pi_*(roj*Dro**3-rij*Dri**3)/Itj
    d2=pi_*(Dro**4-Dri**4)/(4._rk*Itj)

    sk1=1260._rk+630._rk*a2+504._rk*b2+441._rk*g2+396._rk*d2
    sk2=L*(630._rk+210._rk*a2+147._rk*b2+126._rk*g2+114._rk*d2 &
       -phi*(105._rk*a2+105._rk*b2+94.5_rk*g2+84._rk*d2))
    sk3=L*(630._rk+420._rk*a2+357._rk*b2+315._rk*g2+282._rk*d2 &
       +phi*(105._rk*a2+105._rk*b2+94.5_rk*g2+84._rk*d2))
    sk4=L**2*(420._rk+210._rk*phi+105._rk*phi**2+a2*(105._rk+52.5_rk*phi**2) &
       +b2*(56._rk-35._rk*phi+35._rk*phi**2)+g2*(42._rk-42._rk*phi+26.25_rk*phi**2) &
       +d2*(36._rk-42._rk*phi+21._rk*phi**2))
    sk5=L**2*(210._rk-210._rk*phi-105._rk*phi**2+a2*(105._rk-105._rk*phi-52.5_rk*phi**2) &
       +b2*(91._rk-70._rk*phi-35._rk*phi**2)+g2*(84._rk-52.5_rk*phi-26.25_rk*phi**2) &
       +d2*(78._rk-42._rk*phi-21._rk*phi**2))
    sk6=L**2*(420._rk+210._rk*phi+105._rk*phi**2+a2*(315._rk+210._rk*phi+52.5_rk*phi**2) &
       +b2*(266._rk+175._rk*phi+35._rk*phi**2)+g2*(231._rk+147._rk*phi+26.25_rk*phi**2) &
       +d2*(204._rk+126._rk*phi+21._rk*phi**2))
    sk7=12._rk+6._rk*a1+4._rk*b1
    sk8=L*(6._rk+3._rk*a1+2._rk*b1)
    sk9=L**2*(3._rk+1.5_rk*a1+b1)

    ka=reshape([ &
      sk1,0._rk,0._rk,sk2,-sk1,0._rk,0._rk,sk3, &
      0._rk,sk1,-sk2,0._rk,0._rk,-sk1,-sk3,0._rk, &
      0._rk,-sk2,sk4,0._rk,0._rk,sk2,sk5,0._rk, &
      sk2,0._rk,0._rk,sk4,-sk2,0._rk,0._rk,sk5, &
      -sk1,0._rk,0._rk,-sk2,sk1,0._rk,0._rk,-sk3, &
      0._rk,-sk1,sk2,0._rk,0._rk,sk1,sk3,0._rk, &
      0._rk,-sk3,sk5,0._rk,0._rk,sk3,sk6,0._rk, &
      sk3,0._rk,0._rk,sk5,-sk3,0._rk,0._rk,sk6 ],[8,8],order=[2,1])
    kb=reshape([ &
      sk7,0._rk,0._rk,sk8,-sk7,0._rk,0._rk,sk8, &
      0._rk,sk7,-sk8,0._rk,0._rk,-sk7,-sk8,0._rk, &
      0._rk,-sk8,sk9,0._rk,0._rk,sk8,sk9,0._rk, &
      sk8,0._rk,0._rk,sk9,-sk8,0._rk,0._rk,sk9, &
      -sk7,0._rk,0._rk,-sk8,sk7,0._rk,0._rk,-sk8, &
      0._rk,-sk7,sk8,0._rk,0._rk,sk7,sk8,0._rk, &
      0._rk,-sk8,sk9,0._rk,0._rk,sk8,sk9,0._rk, &
      sk8,0._rk,0._rk,sk9,-sk8,0._rk,0._rk,sk9 ],[8,8],order=[2,1])
    K=E*Itj*(ka+105._rk*phi*kb)/(105._rk*L**3*(1._rk+phi)**2)

    if (axial/=0._rk) then
      sk10=36._rk+60._rk*phi+3._rk*phi**2
      sk11=3._rk*L
      sk12=L**2*(4._rk+5._rk*phi+2.5_rk*phi**2)
      sk13=L**2*(1._rk+5._rk*phi+2.5_rk*phi**2)
      kg=reshape([ &
        sk10,0._rk,0._rk,sk11,-sk10,0._rk,0._rk,sk11, &
        0._rk,sk10,-sk11,0._rk,0._rk,-sk10,-sk11,0._rk, &
        0._rk,-sk11,sk12,0._rk,0._rk,sk11,-sk13,0._rk, &
        sk11,0._rk,0._rk,sk12,-sk11,0._rk,0._rk,-sk13, &
        -sk10,0._rk,0._rk,-sk11,sk10,0._rk,0._rk,-sk11, &
        0._rk,-sk10,sk11,0._rk,0._rk,sk10,sk11,0._rk, &
        0._rk,-sk11,-sk13,0._rk,0._rk,sk11,sk12,0._rk, &
        sk11,0._rk,0._rk,-sk13,-sk11,0._rk,0._rk,sk12 ],[8,8],order=[2,1])
      K=K+axial*kg/(30._rk*L*(1._rk+phi)**2)
    end if

    m1=(468._rk+882._rk*phi+420._rk*phi**2)+a1*(108._rk+210._rk*phi+105._rk*phi**2) &
       +b1*(38._rk+78._rk*phi+42._rk*phi**2)
    m2=L*((66._rk+115.5_rk*phi+52.5_rk*phi**2)+a1*(21._rk+40.5_rk*phi+21._rk*phi**2) &
       +b1*(8.5_rk+18._rk*phi+10.5_rk*phi**2))
    m3=(162._rk+378._rk*phi+210._rk*phi**2)+a1*(81._rk+189._rk*phi+105._rk*phi**2) &
       +b1*(46._rk+111._rk*phi+63._rk*phi**2)
    m4=L*((39._rk+94.5_rk*phi+52.5_rk*phi**2)+a1*(18._rk+40.5_rk*phi+21._rk*phi**2) &
       +b1*(9.5_rk+21._rk*phi+10.5_rk*phi**2))
    m5=L**2*((12._rk+21._rk*phi+10.5_rk*phi**2)+a1*(4.5_rk+9._rk*phi+5.25_rk*phi**2) &
       +b1*(2._rk+4.5_rk*phi+3._rk*phi**2))
    m6=L*((39._rk+94.5_rk*phi+52.5_rk*phi**2)+a1*(21._rk+54._rk*phi+31.5_rk*phi**2) &
       +b1*(12.5_rk+34.5_rk*phi+21._rk*phi**2))
    m7=L**2*((9._rk+21._rk*phi+10.5_rk*phi**2)+a1*(4.5_rk+10.5_rk*phi+5.25_rk*phi**2) &
       +b1*(2.5_rk+6._rk*phi+3._rk*phi**2))
    m8=(468._rk+882._rk*phi+420._rk*phi**2)+a1*(360._rk+672._rk*phi+315._rk*phi**2) &
       +b1*(290._rk+540._rk*phi+252._rk*phi**2)
    m9=L*((66._rk+115.5_rk*phi+52.5_rk*phi**2)+a1*(45._rk+75._rk*phi+31.5_rk*phi**2) &
       +b1*(32.5_rk+52.5_rk*phi+21._rk*phi**2))
    m10=L**2*((12._rk+21._rk*phi+10.5_rk*phi**2)+a1*(7.5_rk+12._rk*phi+5.25_rk*phi**2) &
       +b1*(5._rk+7.5_rk*phi+3._rk*phi**2))

    mt=reshape([ &
      m1,0._rk,0._rk,m2,m3,0._rk,0._rk,-m4, &
      0._rk,m1,-m2,0._rk,0._rk,m3,m4,0._rk, &
      0._rk,-m2,m5,0._rk,0._rk,-m6,-m7,0._rk, &
      m2,0._rk,0._rk,m5,m6,0._rk,0._rk,-m7, &
      m3,0._rk,0._rk,m6,m8,0._rk,0._rk,-m9, &
      0._rk,m3,-m6,0._rk,0._rk,m8,m9,0._rk, &
      0._rk,m4,-m7,0._rk,0._rk,m9,m10,0._rk, &
      -m4,0._rk,0._rk,-m7,-m9,0._rk,0._rk,m10 ],[8,8],order=[2,1])
    mt=rho*Aj*L*mt/(1260._rk*(1._rk+phi)**2)
    M=mt

    m11=252._rk+126._rk*a2+72._rk*b2+45._rk*g2+30._rk*d2
    m12=L*(21._rk-105._rk*phi+a2*(21._rk-42._rk*phi)+b2*(15._rk-21._rk*phi) &
       +g2*(10.5_rk-12._rk*phi)+d2*(7.5_rk-7.5_rk*phi))
    m13=L*(21._rk-105._rk*phi+a2*(-63._rk*phi)-b2*(6._rk+42._rk*phi) &
       -g2*(7.5_rk+30._rk*phi)-d2*(7.5_rk+22.5_rk*phi))
    m14=L**2*((28._rk+35._rk*phi+70._rk*phi**2)+a2*(7._rk-7._rk*phi+17.5_rk*phi**2) &
       +b2*(4._rk-7._rk*phi+7._rk*phi**2)+g2*(2.75_rk-5._rk*phi+3.5_rk*phi**2) &
       +d2*(2._rk-3.5_rk*phi+2._rk*phi**2))
    m15=L**2*((7._rk+35._rk*phi-35._rk*phi**2)+a2*(3.5_rk+17.5_rk*phi-17.5_rk*phi**2) &
       +b2*(3._rk+10.5_rk*phi-10.5_rk*phi**2)+g2*(2.75_rk+7._rk*phi-7._rk*phi**2) &
       +d2*(2.5_rk+5._rk*phi-5._rk*phi**2))
    m16=L**2*((28._rk+35._rk*phi+70._rk*phi**2)+a2*(21._rk+42._rk*phi+52.5_rk*phi**2) &
       +b2*(18._rk+42._rk*phi+42._rk*phi**2)+g2*(16.25_rk+40._rk*phi+35._rk*phi**2) &
       +d2*(15._rk+37.5_rk*phi+30._rk*phi**2))

    if (rotary) then
      mr=reshape([ &
        m11,0._rk,0._rk,m12,-m11,0._rk,0._rk,m13, &
        0._rk,m11,-m12,0._rk,0._rk,-m11,-m13,0._rk, &
        0._rk,-m12,m14,0._rk,0._rk,m12,-m15,0._rk, &
        m12,0._rk,0._rk,m14,-m12,0._rk,0._rk,-m15, &
        -m11,0._rk,0._rk,-m12,m11,0._rk,0._rk,-m13, &
        0._rk,-m11,m12,0._rk,0._rk,m11,m13,0._rk, &
        0._rk,-m13,-m15,0._rk,0._rk,m13,m16,0._rk, &
        m13,0._rk,0._rk,-m15,-m13,0._rk,0._rk,m16 ],[8,8],order=[2,1])
      mr=rho*Itj*mr/(210._rk*L*(1._rk+phi)**2)
      M=mt+mr
    end if

    if (gyro) then
      ge=reshape([ &
        0._rk,-m11,m12,0._rk,0._rk,m11,m13,0._rk, &
        m11,0._rk,0._rk,m12,-m11,0._rk,0._rk,m13, &
        -m12,0._rk,0._rk,-m14,m12,0._rk,0._rk,m15, &
        0._rk,-m12,m14,0._rk,0._rk,m12,-m15,0._rk, &
        0._rk,m11,-m12,0._rk,0._rk,-m11,-m13,0._rk, &
        -m11,0._rk,0._rk,-m12,m11,0._rk,0._rk,-m13, &
        -m13,0._rk,0._rk,m15,m13,0._rk,0._rk,-m16, &
        0._rk,-m13,-m15,0._rk,0._rk,m13,m16,0._rk ],[8,8],order=[2,1])
      Cg=-rho*Itj*ge/(105._rk*L*(1._rk+phi)**2)
    end if
  end subroutine shaft_tapered_matrices
end module rd_shaft_tapered
