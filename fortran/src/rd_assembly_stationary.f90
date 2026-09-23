module rd_assembly_stationary
  use rd_kinds, only: rk, ik
  use rd_status, only: RD_OK, RD_ERR_INPUT, RD_ERR_UNSUPPORTED
  use rd_shaft_circular, only: shaft_circular_matrices
  use rd_shaft_tapered, only: shaft_tapered_matrices
  use rd_lapack, only: eig_real
  implicit none(type, external)
  private
  public :: assemble_rotor, assemble_bearings
contains
  subroutine assemble_rotor(nnode,z,nshaft,shaft,ndisc,disc,M,C0,C1,K0,K1,status)
    integer(ik),intent(in)::nnode,nshaft,ndisc
    real(rk),intent(in)::z(nnode),shaft(11,nshaft),disc(6,ndisc)
    real(rk),intent(out)::M(4*nnode,4*nnode),C0(4*nnode,4*nnode),C1(4*nnode,4*nnode),K0(4*nnode,4*nnode),K1(4*nnode,4*nnode)
    integer(ik),intent(out)::status
    integer :: i,j,k,n1,n2,dofs(8),dof4(4),stype,dtype
    real(rk)::Me(8,8),Ge(8,8),Ke(8,8),K1e(8,8),L,do_,di,rho,E,G,df,axial,torque,pi_,thick,mod_,Id,Ip
    integer(ik)::st
    M=0;C0=0;C1=0;K0=0;K1=0; status=RD_OK; pi_=acos(-1._rk)
    do i=1,nshaft
      stype=nint(shaft(1,i)); n1=nint(shaft(2,i)); n2=nint(shaft(3,i))
      if(n1<1.or.n1>nnode.or.n2<1.or.n2>nnode) then; status=RD_ERR_INPUT;return;endif
      L=z(n2)-z(n1)
      if(stype>=1.and.stype<=8)then
        do_=shaft(4,i);di=shaft(5,i);rho=shaft(6,i);E=shaft(7,i);G=shaft(8,i);df=shaft(9,i);axial=shaft(10,i);torque=shaft(11,i)
        call shaft_circular_matrices(stype,L,do_,di,E,G,rho,axial,torque,Me,Ge,Ke,K1e,st)
      elseif(stype>=21.and.stype<=28)then
        df=0;torque=0
        call shaft_tapered_matrices(stype,L,shaft(4,i),shaft(5,i),shaft(6,i),shaft(7,i),shaft(9,i),shaft(10,i),shaft(8,i),shaft(11,i),Me,Ge,Ke,K1e,st)
      else
        status=RD_ERR_UNSUPPORTED;return
      endif
      if(st/=RD_OK) then;status=st;return;endif
      dofs=[4*n1-3,4*n1-2,4*n1-1,4*n1,4*n2-3,4*n2-2,4*n2-1,4*n2]
      do j=1,8;do k=1,8
        M(dofs(j),dofs(k))=M(dofs(j),dofs(k))+Me(j,k)
        C0(dofs(j),dofs(k))=C0(dofs(j),dofs(k))+df*Ke(j,k)
        C1(dofs(j),dofs(k))=C1(dofs(j),dofs(k))+Ge(j,k)
        K0(dofs(j),dofs(k))=K0(dofs(j),dofs(k))+Ke(j,k)
        K1(dofs(j),dofs(k))=K1(dofs(j),dofs(k))+df*K1e(j,k)
      enddo;enddo
    enddo
    do i=1,ndisc
      dtype=nint(disc(1,i)); n1=nint(disc(2,i)); if(n1<1.or.n1>nnode) then;status=RD_ERR_INPUT;return;endif
      if(dtype==1.or.dtype==3) then
        rho=disc(3,i);thick=disc(4,i);do_=disc(5,i);di=disc(6,i)
        mod_=0.25_rk*rho*pi_*thick*(do_**2-di**2)
        Id=0.015625_rk*rho*pi_*thick*(do_**4-di**4)+mod_*thick**2/12
        Ip=0.03125_rk*rho*pi_*thick*(do_**4-di**4)
      elseif(dtype==2.or.dtype==4) then
        mod_=disc(3,i);Id=disc(4,i);Ip=disc(5,i)
      else; status=RD_ERR_UNSUPPORTED;return
      endif
      dof4=[4*n1-3,4*n1-2,4*n1-1,4*n1]
      M(dof4(1),dof4(1))=M(dof4(1),dof4(1))+mod_; M(dof4(2),dof4(2))=M(dof4(2),dof4(2))+mod_
      M(dof4(3),dof4(3))=M(dof4(3),dof4(3))+Id; M(dof4(4),dof4(4))=M(dof4(4),dof4(4))+Id
      if(dtype==1.or.dtype==2) then
        C1(dof4(3),dof4(4))=C1(dof4(3),dof4(4))+Ip; C1(dof4(4),dof4(3))=C1(dof4(4),dof4(3))-Ip
      endif
    enddo
  end subroutine

  subroutine assemble_bearings(nnode,nbear,bear,speed,Mb,Cb,Kb,is_zero,status,eccentricity)
    integer(ik),intent(in)::nnode,nbear
    real(rk),intent(in)::bear(34,nbear),speed
    real(rk),intent(out)::Mb(4*nnode,4*nnode),Cb(4*nnode,4*nnode),Kb(4*nnode,4*nnode)
    logical,intent(out)::is_zero(4*nnode)
    integer(ik),intent(out)::status
    real(rk),intent(out),optional::eccentricity(nbear)
    integer::i,j,k,t,n,d(4); real(rk)::kl(4,4),cl(4,4),ml(4,4),ecc
    Mb=0;Cb=0;Kb=0;is_zero=.false.;status=RD_OK
    if(present(eccentricity)) eccentricity=0
    do i=1,nbear
      t=nint(bear(1,i));n=nint(bear(2,i));if(n<1.or.n>nnode)then;status=RD_ERR_INPUT;return;endif
      d=[4*n-3,4*n-2,4*n-1,4*n];kl=0;cl=0;ml=0;ecc=0
      select case(t)
      case(1);is_zero(d(1:2))=.true.
      case(2);is_zero(d)=.true.
      case(3);kl(1,1)=bear(3,i);kl(2,2)=bear(4,i);cl(1,1)=bear(5,i);cl(2,2)=bear(6,i)
      case(4)
        do j=1,4;kl(j,j)=bear(2+j,i);cl(j,j)=bear(6+j,i);enddo
      case(5)
        kl(1,1)=bear(3,i);kl(1,2)=bear(4,i);kl(2,1)=bear(5,i);kl(2,2)=bear(6,i)
        cl(1,1)=bear(7,i);cl(1,2)=bear(8,i);cl(2,1)=bear(9,i);cl(2,2)=bear(10,i)
      case(6)
        do j=1,4;do k=1,4;kl(j,k)=bear(2+(j-1)*4+k,i);cl(j,k)=bear(18+(j-1)*4+k,i);enddo;enddo
      case(7)
        call short_bearing_coefficients(bear(:,i),speed,kl,cl,ecc,status);if(status/=RD_OK)return
      case(8)
        call seal_coefficients(bear(:,i),speed,ml,cl,kl,status);if(status/=RD_OK)return
      case(20)
        ! bearmtx.m accepts type 20 but contributes zero; coaxial coupling is assembled separately.
      case default; status=RD_ERR_UNSUPPORTED;return
      end select
      if(present(eccentricity)) eccentricity(i)=ecc
      do j=1,4;do k=1,4
        Kb(d(j),d(k))=Kb(d(j),d(k))+kl(j,k);Cb(d(j),d(k))=Cb(d(j),d(k))+cl(j,k);Mb(d(j),d(k))=Mb(d(j),d(k))+ml(j,k)
      enddo;enddo
    enddo
  end subroutine

  subroutine short_bearing_coefficients(row,speed,K,C,ecc,status)
    real(rk),intent(in)::row(34),speed;real(rk),intent(out)::K(4,4),C(4,4),ecc;integer(ik),intent(out)::status
    real(rk)::F,D,L,cclr,eta,H,pcoef(5),Acomp(4,4),wr(4),wi(4),vr(4,4),n2,n,q1,q2,q3,p2,de,a(2,2),b(2,2)
    integer::i,nroot;integer(ik)::st
    K=0;C=0;ecc=0;status=RD_OK
    if(speed==0)then;status=RD_ERR_INPUT;return;endif
    F=row(3);D=row(4);L=row(5);cclr=row(6);eta=row(7)
    if(F<=0.or.D<=0.or.L<=0.or.cclr<=0.or.eta<=0)then;status=RD_ERR_INPUT;return;endif
    H=(8*cclr*cclr*F/(D*speed*eta*L**3))**2
    ! MATLAB: roots([1 -4 (6-(16-pi^2)/H) -(4+pi^2/H) 1])
    pcoef=[1._rk,-4._rk,6._rk-(16._rk-acos(-1._rk)**2)/H,-(4._rk+acos(-1._rk)**2/H),1._rk]
    Acomp=0
    Acomp(2,1)=1;Acomp(3,2)=1;Acomp(4,3)=1
    Acomp(1,4)=-pcoef(5)/pcoef(1)
    Acomp(2,4)=-pcoef(4)/pcoef(1)
    Acomp(3,4)=-pcoef(3)/pcoef(1)
    Acomp(4,4)=-pcoef(2)/pcoef(1)
    call eig_real(Acomp,wr,wi,vr,st);if(st/=RD_OK)then;status=st;return;endif
    nroot=0;n2=huge(1._rk)
    do i=1,4
      if(abs(wi(i))<=1e-10_rk*max(1._rk,abs(wr(i))).and.wr(i)>0.and.wr(i)<1)then
        nroot=nroot+1;n2=min(n2,wr(i))
      endif
    enddo
    if(nroot==0)n2=.5_rk
    n=sqrt(n2);ecc=n;p2=acos(-1._rk)**2;q1=1-n2;q2=1+n2;q3=1+2*n2;de=(p2*q1+16*n2)**1.5_rk
    a(1,1)=4*(p2*(2-n2)+16*n2)/de;a(2,2)=4*(p2*q1*q3+32*n2*q2)/(q1*de)
    a(1,2)=acos(-1._rk)*(p2*q1**2-16*n**4)/(n*sqrt(q1)*de);a(2,1)=-acos(-1._rk)*(p2*q1*q3+32*n2*q2)/(n*sqrt(q1)*de)
    b(1,1)=2*acos(-1._rk)*sqrt(q1)*(p2*q3-16*n2)/(n*de);b(2,2)=2*acos(-1._rk)*(p2*q1**2+48*n2)/(n*sqrt(q1)*de)
    b(1,2)=-8*(p2*q3-16*n2)/de;b(2,1)=b(1,2)
    K(1:2,1:2)=(F/cclr)*a;C(1:2,1:2)=(F/(cclr*speed))*b
    if(row(8)/=0)then;K=0;C=0;endif
  end subroutine

  subroutine seal_coefficients(row,speed,M,C,K,status)
    real(rk),intent(in)::row(34),speed;real(rk),intent(out)::M(4,4),C(4,4),K(4,4);integer(ik),intent(out)::status
    real(rk)::P,R,L,cclr,V,fric,T,sigma,eps,mu0,mu1,mu2,J(2,2),I2(2,2)
    M=0;C=0;K=0;status=RD_OK;P=row(3);R=row(4);L=row(5);cclr=row(6);V=row(7);fric=row(8)
    if(R<=0.or.L<=0.or.cclr<=0.or.V==0.or.fric==0)then;status=RD_ERR_INPUT;return;endif
    T=L/V;sigma=fric*L/cclr;eps=acos(-1._rk)*sigma*R*P/(6*fric*(1.5_rk+2*sigma))
    mu0=9*sigma/(1.5_rk+2*sigma);mu1=((3+2*sigma)**2*(1.5_rk+2*sigma)-9*sigma)/(1.5_rk+2*sigma)**2
    mu2=(19*sigma+18*sigma**2+8*sigma**3)/(1.5_rk+2*sigma)**3
    I2=0;I2(1,1)=1;I2(2,2)=1;J=0;J(1,2)=-1;J(2,1)=1
    K(1:2,1:2)=eps*(mu0-mu2*T*T*speed*speed/4)*I2+eps*(mu1*T*speed/2)*J
    C(1:2,1:2)=eps*mu1*T*I2+eps*(mu2*T*T*speed)*J
    M(1:2,1:2)=eps*mu2*T*T*I2
  end subroutine
end module rd_assembly_stationary
