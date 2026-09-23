module rd_bearings
  use rd_kinds, only: rk, ik
  use rd_status, only: RD_OK, RD_ERR_INPUT, RD_ERR_UNSUPPORTED
  use rd_lapack, only: eig_real
  implicit none(type, external)
  private
  public :: assemble_bearings
contains
  subroutine assemble_bearings(nnode,nbear,bear,speed,Mb,Cb,Kb,is_zero,eccentricity,status)
    integer(ik),intent(in) :: nnode,nbear
    real(rk),intent(in) :: bear(34,nbear),speed
    real(rk),intent(out) :: Mb(4*nnode,4*nnode),Cb(4*nnode,4*nnode),Kb(4*nnode,4*nnode)
    logical,intent(out) :: is_zero(4*nnode)
    real(rk),intent(out) :: eccentricity(nbear)
    integer(ik),intent(out) :: status
    integer :: ib,j,k,t,n,d(4)
    real(rk) :: kl(4,4),cl(4,4),ml(4,4),ecc
    integer(ik) :: st

    Mb=0._rk; Cb=0._rk; Kb=0._rk; is_zero=.false.; eccentricity=0._rk; status=RD_OK
    do ib=1,nbear
      t=nint(bear(1,ib)); n=nint(bear(2,ib))
      if (n<1 .or. n>nnode) then
        status=RD_ERR_INPUT; return
      end if
      d=[4*n-3,4*n-2,4*n-1,4*n]
      kl=0._rk; cl=0._rk; ml=0._rk; ecc=0._rk
      select case(t)
      case(1)
        is_zero(d(1:2))=.true.
      case(2)
        is_zero(d)=.true.
      case(3)
        kl(1,1)=bear(3,ib); kl(2,2)=bear(4,ib)
        cl(1,1)=bear(5,ib); cl(2,2)=bear(6,ib)
      case(4)
        do j=1,4
          kl(j,j)=bear(2+j,ib)
          cl(j,j)=bear(6+j,ib)
        end do
      case(5)
        kl(1,1)=bear(3,ib); kl(1,2)=bear(4,ib)
        kl(2,1)=bear(5,ib); kl(2,2)=bear(6,ib)
        cl(1,1)=bear(7,ib); cl(1,2)=bear(8,ib)
        cl(2,1)=bear(9,ib); cl(2,2)=bear(10,ib)
      case(6)
        do j=1,4
          do k=1,4
            kl(j,k)=bear(2+(j-1)*4+k,ib)
            cl(j,k)=bear(18+(j-1)*4+k,ib)
          end do
        end do
      case(7)
        call short_bearing_coefficients(bear(:,ib),speed,kl,cl,ecc,st)
        if (st/=RD_OK) then
          status=st; return
        end if
      case(8)
        call seal_coefficients(bear(:,ib),speed,ml,cl,kl,st)
        if (st/=RD_OK) then
          status=st; return
        end if
      case(20)
        ! Rotor_Software_v2/bearmtx.m accepts type 20 in the range check but
        ! contributes nothing in the single-rotor stationary assembly.
      case default
        status=RD_ERR_UNSUPPORTED; return
      end select
      eccentricity(ib)=ecc
      do j=1,4
        do k=1,4
          Kb(d(j),d(k))=Kb(d(j),d(k))+kl(j,k)
          Cb(d(j),d(k))=Cb(d(j),d(k))+cl(j,k)
          Mb(d(j),d(k))=Mb(d(j),d(k))+ml(j,k)
        end do
      end do
    end do
  end subroutine assemble_bearings

  subroutine short_bearing_coefficients(row,speed,Kb1,Cb1,ecc,status)
    real(rk),intent(in) :: row(34),speed
    real(rk),intent(out) :: Kb1(4,4),Cb1(4,4),ecc
    integer(ik),intent(out) :: status
    real(rk) :: F,D,L,c,eta,H,pi_,p2,n2,n,q1,q2,q3,de
    real(rk) :: a(2,2),b(2,2),coef(5),comp(4,4),wr(4),wi(4),vr(4,4),roots(4)
    integer :: i,nroot
    integer(ik) :: st

    Kb1=0._rk; Cb1=0._rk; ecc=0._rk; status=RD_OK
    F=row(3); D=row(4); L=row(5); c=row(6); eta=row(7); pi_=acos(-1._rk)
    if (F<=0._rk .or. D<=0._rk .or. L<=0._rk .or. c<=0._rk .or. eta<=0._rk) then
      status=RD_ERR_INPUT; return
    end if
    if (speed==0._rk) then
      ! The V2 source emits an error message and then continues into divisions
      ! by zero. At the C ABI we make that undefined case explicit.
      status=RD_ERR_INPUT; return
    end if
    H=(8._rk*c*c*F/(D*speed*eta*L**3))**2
    if (H<=0._rk) then
      status=RD_ERR_INPUT; return
    end if
    coef=[1._rk,-4._rk,6._rk-(16._rk-pi_**2)/H,-(4._rk+pi_**2/H),1._rk]
    comp=0._rk
    comp(2,1)=1._rk; comp(3,2)=1._rk; comp(4,3)=1._rk
    comp(1,4)=-coef(5); comp(2,4)=-coef(4); comp(3,4)=-coef(3); comp(4,4)=-coef(2)
    call eig_real(comp,wr,wi,vr,st)
    if (st/=RD_OK) then
      status=st; return
    end if
    nroot=0; roots=0._rk
    do i=1,4
      if (wi(i)==0._rk .and. wr(i)>0._rk .and. wr(i)<1._rk) then
        nroot=nroot+1; roots(nroot)=wr(i)
      end if
    end do
    if (nroot==0) then
      n2=0.5_rk
    else
      n2=minval(roots(1:nroot))
    end if

    n=sqrt(n2); ecc=n
    q1=1._rk-n2; q2=1._rk+n2; q3=1._rk+2._rk*n2; p2=pi_**2
    de=(p2*q1+16._rk*n2)**1.5_rk
    a=0._rk; b=0._rk
    a(1,1)=4._rk*(p2*(2._rk-n2)+16._rk*n2)/de
    a(2,2)=4._rk*(p2*q1*q3+32._rk*n2*q2)/(q1*de)
    a(1,2)=pi_*(p2*q1**2-16._rk*n**4)/(n*sqrt(q1)*de)
    a(2,1)=-pi_*(p2*q1*q3+32._rk*n2*q2)/(n*sqrt(q1)*de)
    b(1,1)=2._rk*pi_*sqrt(q1)*(p2*q3-16._rk*n2)/(n*de)
    b(2,2)=2._rk*pi_*(p2*q1**2+48._rk*n2)/(n*sqrt(q1)*de)
    b(1,2)=-8._rk*(p2*q3-16._rk*n2)/de
    b(2,1)=b(1,2)
    Kb1(1:2,1:2)=(F/c)*a
    Cb1(1:2,1:2)=(F/(c*speed))*b
    if (row(8)/=0._rk) then
      Kb1=0._rk; Cb1=0._rk
    end if
  end subroutine short_bearing_coefficients

  subroutine seal_coefficients(row,speed,Mb1,Cb1,Kb1,status)
    real(rk),intent(in) :: row(34),speed
    real(rk),intent(out) :: Mb1(4,4),Cb1(4,4),Kb1(4,4)
    integer(ik),intent(out) :: status
    real(rk) :: P,R,L,c,V,fric,T,sigma,epsilon,mu0,mu1,mu2,pi_
    real(rk) :: eye2(2,2),skew2(2,2)
    P=row(3); R=row(4); L=row(5); c=row(6); V=row(7); fric=row(8)
    Mb1=0._rk; Cb1=0._rk; Kb1=0._rk; status=RD_OK
    if (R<=0._rk .or. L<=0._rk .or. c<=0._rk .or. V==0._rk .or. fric==0._rk) then
      status=RD_ERR_INPUT; return
    end if
    pi_=acos(-1._rk); T=L/V; sigma=fric*L/c
    if (1.5_rk+2._rk*sigma==0._rk) then
      status=RD_ERR_INPUT; return
    end if
    epsilon=pi_*sigma*R*P/(6._rk*fric*(1.5_rk+2._rk*sigma))
    mu0=9._rk*sigma/(1.5_rk+2._rk*sigma)
    mu1=((3._rk+2._rk*sigma)**2*(1.5_rk+2._rk*sigma)-9._rk*sigma)/(1.5_rk+2._rk*sigma)**2
    mu2=(19._rk*sigma+18._rk*sigma**2+8._rk*sigma**3)/(1.5_rk+2._rk*sigma)**3
    eye2=0._rk; eye2(1,1)=1._rk; eye2(2,2)=1._rk
    skew2=reshape([0._rk,-1._rk,1._rk,0._rk],[2,2],order=[2,1])
    Kb1(1:2,1:2)=epsilon*(mu0-mu2*T*T*speed*speed/4._rk)*eye2 &
                  +epsilon*(mu1*T*speed/2._rk)*skew2
    Cb1(1:2,1:2)=epsilon*mu1*T*eye2+epsilon*(mu2*T*T*speed)*skew2
    Mb1(1:2,1:2)=epsilon*mu2*T*T*eye2
  end subroutine seal_coefficients
end module rd_bearings
