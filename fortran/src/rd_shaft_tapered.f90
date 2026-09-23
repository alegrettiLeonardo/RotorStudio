module rd_shaft_tapered
  use rd_kinds, only: rk, ik
  use rd_status, only: RD_OK, RD_ERR_INPUT
  implicit none(type, external)
  private
  public :: shaft_tapered_matrices
contains
  subroutine shaft_tapered_matrices(stype,L,doj,dok,dij,dik,E,G_in,rho,axial,M,Cg,K,K1,status)
    integer(ik),intent(in)::stype
    real(rk),intent(in)::L,doj,dok,dij,dik,E,G_in,rho,axial
    real(rk),intent(out)::M(8,8),Cg(8,8),K(8,8),K1(8,8)
    integer(ik),intent(out)::status
    integer::typ
    logical::shear,rotary,gyro
    real(rk)::G,pi_,nu,rok,rik,roj,rij,romean,rimean,mu2,Am,Im,kappa,chi,Dro,Dri,Aj,Itj,phi
    real(rk)::a1,b1,a2,b2,g2,d2
    real(rk)::q1,q2,q3,q4,q5,q6,q7,q8,q9,q10,q11,q12,q13
    real(rk)::m1,m2,m3,m4,m5,m6,m7,m8,m9,m10,m11,m12,m13,m14,m15,m16
    real(rk)::ka(8,8),kb(8,8),kg(8,8),mt(8,8),mr(8,8),ge(8,8)
    pi_=acos(-1._rk); M=0;Cg=0;K=0;K1=0;status=RD_OK
    typ=stype-20
    if(typ<1.or.typ>8.or.L<=0.or.doj<=dij.or.dok<=dik.or.dij<0.or.dik<0.or.E<=0.or.rho<=0)then
      status=RD_ERR_INPUT;return
    endif
    shear=.not.(typ==1.or.typ==5.or.typ==7.or.typ==8)
    G=G_in
    if(.not.shear .or. G==0)G=E/2.6_rk
    if(G<=0)then;status=RD_ERR_INPUT;return;endif
    rotary=.not.(typ==1.or.typ==4.or.typ==6.or.typ==8)
    gyro=.not.(typ==3.or.typ==6.or.typ==7.or.typ==8)
    nu=.5_rk*(E/G)-1; rok=dok/2;rik=dik/2;roj=doj/2;rij=dij/2
    romean=(rok+roj)/2;rimean=(rik+rij)/2;mu2=(rimean/romean)**2
    Am=pi_*(romean**2-rimean**2);Im=pi_*(romean**4-rimean**4)/4
    kappa=6*(1+nu)*(1+mu2)**2/((7+6*nu)*(1+mu2)**2+(20+12*nu)*mu2);chi=1/kappa
    Dro=rok-roj;Dri=rik-rij;Aj=pi_*(doj**2-dij**2)/4;Itj=pi_*(doj**4-dij**4)/64
    phi=12*E*Im*chi/(G*Am*L**2);if(.not.shear)phi=0
    a1=2*pi_*(roj*Dro-rij*Dri)/Aj;b1=pi_*(Dro**2-Dri**2)/Aj
    a2=pi_*(roj**3*Dro-rij**3*Dri)/Itj;b2=3*pi_*(roj**2*Dro**2-rij**2*Dri**2)/(2*Itj)
    g2=pi_*(roj*Dro**3-rij*Dri**3)/Itj;d2=pi_*(Dro**4-Dri**4)/(4*Itj)
    q1=1260+630*a2+504*b2+441*g2+396*d2
    q2=L*(630+210*a2+147*b2+126*g2+114*d2-phi*(105*a2+105*b2+94.5_rk*g2+84*d2))
    q3=L*(630+420*a2+357*b2+315*g2+282*d2+phi*(105*a2+105*b2+94.5_rk*g2+84*d2))
    q4=L**2*(420+210*phi+105*phi**2+a2*(105+52.5_rk*phi**2)+b2*(56-35*phi+35*phi**2)+g2*(42-42*phi+26.25_rk*phi**2)+d2*(36-42*phi+21*phi**2))
    q5=L**2*(210-210*phi-105*phi**2+a2*(105-105*phi-52.5_rk*phi**2)+b2*(91-70*phi-35*phi**2)+g2*(84-52.5_rk*phi-26.25_rk*phi**2)+d2*(78-42*phi-21*phi**2))
    q6=L**2*(420+210*phi+105*phi**2+a2*(315+210*phi+52.5_rk*phi**2)+b2*(266+175*phi+35*phi**2)+g2*(231+147*phi+26.25_rk*phi**2)+d2*(204+126*phi+21*phi**2))
    q7=12+6*a1+4*b1;q8=L*(6+3*a1+2*b1);q9=L**2*(3+1.5_rk*a1+b1)
    ka=reshape([q1,0._rk,0._rk,q2,-q1,0._rk,0._rk,q3, 0._rk,q1,-q2,0._rk,0._rk,-q1,-q3,0._rk, 0._rk,-q2,q4,0._rk,0._rk,q2,q5,0._rk, q2,0._rk,0._rk,q4,-q2,0._rk,0._rk,q5, -q1,0._rk,0._rk,-q2,q1,0._rk,0._rk,-q3, 0._rk,-q1,q2,0._rk,0._rk,q1,q3,0._rk, 0._rk,-q3,q5,0._rk,0._rk,q3,q6,0._rk, q3,0._rk,0._rk,q5,-q3,0._rk,0._rk,q6],[8,8],order=[2,1])
    kb=reshape([q7,0._rk,0._rk,q8,-q7,0._rk,0._rk,q8, 0._rk,q7,-q8,0._rk,0._rk,-q7,-q8,0._rk, 0._rk,-q8,q9,0._rk,0._rk,q8,q9,0._rk, q8,0._rk,0._rk,q9,-q8,0._rk,0._rk,q9, -q7,0._rk,0._rk,-q8,q7,0._rk,0._rk,-q8, 0._rk,-q7,q8,0._rk,0._rk,q7,q8,0._rk, 0._rk,-q8,q9,0._rk,0._rk,q8,q9,0._rk, q8,0._rk,0._rk,q9,-q8,0._rk,0._rk,q9],[8,8],order=[2,1])
    K=E*Itj*(ka+105*phi*kb)/(105*L**3*(1+phi)**2)
    if(axial/=0)then
      q10=36+60*phi+3*phi**2;q11=3*L;q12=L**2*(4+5*phi+2.5_rk*phi**2);q13=L**2*(1+5*phi+2.5_rk*phi**2)
      kg=reshape([q10,0._rk,0._rk,q11,-q10,0._rk,0._rk,q11,0._rk,q10,-q11,0._rk,0._rk,-q10,-q11,0._rk,0._rk,-q11,q12,0._rk,0._rk,q11,-q13,0._rk,q11,0._rk,0._rk,q12,-q11,0._rk,0._rk,-q13,-q10,0._rk,0._rk,-q11,q10,0._rk,0._rk,-q11,0._rk,-q10,q11,0._rk,0._rk,q10,q11,0._rk,0._rk,-q11,-q13,0._rk,0._rk,q11,q12,0._rk,q11,0._rk,0._rk,-q13,-q11,0._rk,0._rk,q12],[8,8],order=[2,1])
      K=K+axial*kg/(30*L*(1+phi)**2)
    endif
    m1=(468+882*phi+420*phi**2)+a1*(108+210*phi+105*phi**2)+b1*(38+78*phi+42*phi**2)
    m2=L*((66+115.5_rk*phi+52.5_rk*phi**2)+a1*(21+40.5_rk*phi+21*phi**2)+b1*(8.5_rk+18*phi+10.5_rk*phi**2))
    m3=(162+378*phi+210*phi**2)+a1*(81+189*phi+105*phi**2)+b1*(46+111*phi+63*phi**2)
    m4=L*((39+94.5_rk*phi+52.5_rk*phi**2)+a1*(18+40.5_rk*phi+21*phi**2)+b1*(9.5_rk+21*phi+10.5_rk*phi**2))
    m5=L**2*((12+21*phi+10.5_rk*phi**2)+a1*(4.5_rk+9*phi+5.25_rk*phi**2)+b1*(2+4.5_rk*phi+3*phi**2))
    m6=L*((39+94.5_rk*phi+52.5_rk*phi**2)+a1*(21+54*phi+31.5_rk*phi**2)+b1*(12.5_rk+34.5_rk*phi+21*phi**2))
    m7=L**2*((9+21*phi+10.5_rk*phi**2)+a1*(4.5_rk+10.5_rk*phi+5.25_rk*phi**2)+b1*(2.5_rk+6*phi+3*phi**2))
    m8=(468+882*phi+420*phi**2)+a1*(360+672*phi+315*phi**2)+b1*(290+540*phi+252*phi**2)
    m9=L*((66+115.5_rk*phi+52.5_rk*phi**2)+a1*(45+75*phi+31.5_rk*phi**2)+b1*(32.5_rk+52.5_rk*phi+21*phi**2))
    m10=L**2*((12+21*phi+10.5_rk*phi**2)+a1*(7.5_rk+12*phi+5.25_rk*phi**2)+b1*(5+7.5_rk*phi+3*phi**2))
    mt=reshape([m1,0._rk,0._rk,m2,m3,0._rk,0._rk,-m4,0._rk,m1,-m2,0._rk,0._rk,m3,m4,0._rk,0._rk,-m2,m5,0._rk,0._rk,-m6,-m7,0._rk,m2,0._rk,0._rk,m5,m6,0._rk,0._rk,-m7,m3,0._rk,0._rk,m6,m8,0._rk,0._rk,-m9,0._rk,m3,-m6,0._rk,0._rk,m8,m9,0._rk,0._rk,m4,-m7,0._rk,0._rk,m9,m10,0._rk,-m4,0._rk,0._rk,-m7,-m9,0._rk,0._rk,m10],[8,8],order=[2,1])
    M=rho*Aj*L*mt/(1260*(1+phi)**2)
    m11=252+126*a2+72*b2+45*g2+30*d2
    m12=L*(21-105*phi+a2*(21-42*phi)+b2*(15-21*phi)+g2*(10.5_rk-12*phi)+d2*(7.5_rk-7.5_rk*phi))
    m13=L*(21-105*phi+a2*(-63*phi)-b2*(6+42*phi)-g2*(7.5_rk+30*phi)-d2*(7.5_rk+22.5_rk*phi))
    m14=L**2*((28+35*phi+70*phi**2)+a2*(7-7*phi+17.5_rk*phi**2)+b2*(4-7*phi+7*phi**2)+g2*(2.75_rk-5*phi+3.5_rk*phi**2)+d2*(2-3.5_rk*phi+2*phi**2))
    m15=L**2*((7+35*phi-35*phi**2)+a2*(3.5_rk+17.5_rk*phi-17.5_rk*phi**2)+b2*(3+10.5_rk*phi-10.5_rk*phi**2)+g2*(2.75_rk+7*phi-7*phi**2)+d2*(2.5_rk+5*phi-5*phi**2))
    m16=L**2*((28+35*phi+70*phi**2)+a2*(21+42*phi+52.5_rk*phi**2)+b2*(18+42*phi+42*phi**2)+g2*(16.25_rk+40*phi+35*phi**2)+d2*(15+37.5_rk*phi+30*phi**2))
    if(rotary)then
      mr=reshape([m11,0._rk,0._rk,m12,-m11,0._rk,0._rk,m13,0._rk,m11,-m12,0._rk,0._rk,-m11,-m13,0._rk,0._rk,-m12,m14,0._rk,0._rk,m12,-m15,0._rk,m12,0._rk,0._rk,m14,-m12,0._rk,0._rk,-m15,-m11,0._rk,0._rk,-m12,m11,0._rk,0._rk,-m13,0._rk,-m11,m12,0._rk,0._rk,m11,m13,0._rk,0._rk,-m13,-m15,0._rk,0._rk,m13,m16,0._rk,m13,0._rk,0._rk,-m15,-m13,0._rk,0._rk,m16],[8,8],order=[2,1])
      M=M+rho*Itj*mr/(210*L*(1+phi)**2)
    endif
    if(gyro)then
      ge=reshape([0._rk,-m11,m12,0._rk,0._rk,m11,m13,0._rk,m11,0._rk,0._rk,m12,-m11,0._rk,0._rk,m13,-m12,0._rk,0._rk,-m14,m12,0._rk,0._rk,m15,0._rk,-m12,m14,0._rk,0._rk,m12,-m15,0._rk,0._rk,m11,-m12,0._rk,0._rk,-m11,-m13,0._rk,-m11,0._rk,0._rk,-m12,m11,0._rk,0._rk,-m13,-m13,0._rk,0._rk,m15,m13,0._rk,0._rk,-m16,0._rk,-m13,-m15,0._rk,0._rk,m13,m16,0._rk],[8,8],order=[2,1])
      Cg=-rho*Itj*ge/(105*L*(1+phi)**2)
    endif
  end subroutine
end module rd_shaft_tapered
