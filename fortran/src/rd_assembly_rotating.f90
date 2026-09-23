module rd_assembly_rotating
  use rd_kinds, only: rk,ik
  use rd_status, only: RD_OK,RD_ERR_INPUT,RD_ERR_UNSUPPORTED
  use rd_shaft_asymmetric, only: shaft_asymmetric_matrices
  implicit none(type, external)
  private
  public :: assemble_rotor_rotating, assemble_bearings_rotating
contains
  subroutine assemble_rotor_rotating(nnode,z,nshaft,shaft,ndisc,disc,M0,C0,C1,K0,K1,K2,status)
    integer(ik),intent(in)::nnode,nshaft,ndisc
    real(rk),intent(in)::z(nnode),shaft(11,nshaft),disc(6,ndisc)
    real(rk),intent(out)::M0(4*nnode,4*nnode),C0(4*nnode,4*nnode),C1(4*nnode,4*nnode),K0(4*nnode,4*nnode),K1(4*nnode,4*nnode),K2(4*nnode,4*nnode)
    integer(ik),intent(out)::status
    integer::i,j,k,n1,n2,stype,dtype,dofs(8),dof4(4),dof2(2)
    real(rk)::L,EIx,EIy,Phix,Phiy,rhoA,rhoI,df,axial,do_,di,rho,E,G,Isec,A,nu,r,r2,r12,kappa,pi_,thick,mass,Idx,Idy,Ip
    real(rk)::Me(8,8),C1e(8,8),K0e(8,8),K2e(8,8),D4(4,4)
    integer(ik)::st
    M0=0;C0=0;C1=0;K0=0;K1=0;K2=0;status=RD_OK;pi_=acos(-1._rk)
    do i=1,nshaft
      stype=nint(shaft(1,i));n1=nint(shaft(2,i));n2=nint(shaft(3,i))
      if(n1<1.or.n1>nnode.or.n2<1.or.n2>nnode)then;status=RD_ERR_INPUT;return;endif
      L=z(n2)-z(n1);if(L<=0)then;status=RD_ERR_INPUT;return;endif
      if(stype>=11.and.stype<=18)then
        EIx=shaft(4,i);EIy=shaft(5,i);Phix=shaft(6,i);Phiy=shaft(7,i);rhoA=shaft(8,i);rhoI=shaft(9,i);df=shaft(10,i);axial=shaft(11,i)
      elseif(stype>=1.and.stype<=8)then
        do_=shaft(4,i);di=shaft(5,i);rho=shaft(6,i);E=shaft(7,i);G=shaft(8,i);df=shaft(9,i);axial=shaft(10,i)
        Isec=0.015625_rk*pi_*(do_**4-di**4);rhoI=rho*Isec;EIx=E*Isec;EIy=E*Isec;A=.25_rk*pi_*(do_**2-di**2);rhoA=rho*A
        if(G==0)then
          Phix=0;Phiy=0
        else
          nu=.5_rk*(E/G)-1;r=di/do_;r2=r*r;r12=(1+r2)**2;kappa=6*r12*(1+nu)/(r12*(7+6*nu)+r2*(20+12*nu))
          Phix=12*E*Isec/(G*kappa*A*L*L);Phiy=Phix
        endif
        stype=stype+10
      else;status=RD_ERR_UNSUPPORTED;return
      endif
      call shaft_asymmetric_matrices(int(stype,ik),L,EIx,EIy,Phix,Phiy,rhoA,rhoI,axial,Me,C1e,K0e,K2e,st)
      if(st/=RD_OK)then;status=st;return;endif
      dofs=[4*n1-3,4*n1-2,4*n1-1,4*n1,4*n2-3,4*n2-2,4*n2-1,4*n2]
      do j=1,8;do k=1,8
        M0(dofs(j),dofs(k))=M0(dofs(j),dofs(k))+Me(j,k)
        C0(dofs(j),dofs(k))=C0(dofs(j),dofs(k))+df*K0e(j,k)
        C1(dofs(j),dofs(k))=C1(dofs(j),dofs(k))+C1e(j,k)
        K0(dofs(j),dofs(k))=K0(dofs(j),dofs(k))+K0e(j,k)
        K2(dofs(j),dofs(k))=K2(dofs(j),dofs(k))+K2e(j,k)
      enddo;enddo
    enddo
    do i=1,ndisc
      dtype=nint(disc(1,i));n1=nint(disc(2,i));if(n1<1.or.n1>nnode)then;status=RD_ERR_INPUT;return;endif
      if(dtype==1.or.dtype==3)then
        rho=disc(3,i);thick=disc(4,i);do_=disc(5,i);di=disc(6,i)
        mass=.25_rk*rho*pi_*thick*(do_**2-di**2);Idx=.015625_rk*rho*pi_*thick*(do_**4-di**4)+mass*thick**2/12;Idy=Idx;Ip=.03125_rk*rho*pi_*thick*(do_**4-di**4)
      elseif(dtype==2.or.dtype==4)then
        mass=disc(3,i);Idx=disc(4,i);Idy=Idx;Ip=disc(5,i)
      elseif(dtype==5.or.dtype==6)then
        mass=disc(3,i);Idx=disc(4,i);Idy=disc(5,i);Ip=disc(6,i)
      else;status=RD_ERR_UNSUPPORTED;return
      endif
      dof4=[4*n1-3,4*n1-2,4*n1-1,4*n1];D4=0;D4(1,1)=mass;D4(2,2)=mass;D4(3,3)=Idx;D4(4,4)=Idy
      M0(dof4,dof4)=M0(dof4,dof4)+D4;K2(dof4,dof4)=K2(dof4,dof4)-D4
      C1(dof4(1),dof4(2))=C1(dof4(1),dof4(2))-2*mass;C1(dof4(2),dof4(1))=C1(dof4(2),dof4(1))+2*mass
      C1(dof4(3),dof4(4))=C1(dof4(3),dof4(4))-2*Idx;C1(dof4(4),dof4(3))=C1(dof4(4),dof4(3))+2*Idy
      if(dtype==1.or.dtype==2.or.dtype==5)then
        dof2=[4*n1-1,4*n1];C1(dof2(1),dof2(2))=C1(dof2(1),dof2(2))+Ip;C1(dof2(2),dof2(1))=C1(dof2(2),dof2(1))-Ip
        K2(dof2(1),dof2(1))=K2(dof2(1),dof2(1))+Ip;K2(dof2(2),dof2(2))=K2(dof2(2),dof2(2))+Ip
      endif
    enddo
  end subroutine

  subroutine assemble_bearings_rotating(nnode,nbear,bear,Cb,Kb,K1b,is_zero,status)
    integer(ik),intent(in)::nnode,nbear;real(rk),intent(in)::bear(34,nbear)
    real(rk),intent(out)::Cb(4*nnode,4*nnode),Kb(4*nnode,4*nnode),K1b(4*nnode,4*nnode)
    logical,intent(out)::is_zero(4*nnode);integer(ik),intent(out)::status
    integer::i,j,t,n,d(4);real(rk)::cl(4,4),kl(4,4),k1l(4,4)
    Cb=0;Kb=0;K1b=0;is_zero=.false.;status=RD_OK
    do i=1,nbear
      t=nint(bear(1,i));n=nint(bear(2,i));if(n<1.or.n>nnode)then;status=RD_ERR_INPUT;return;endif
      d=[4*n-3,4*n-2,4*n-1,4*n];cl=0;kl=0;k1l=0
      select case(t)
      case(1);is_zero(d(1:2))=.true.
      case(2);is_zero(d)=.true.
      case(3)
        kl(1,1)=bear(3,i);kl(2,2)=bear(4,i);cl(1,1)=bear(5,i);cl(2,2)=bear(6,i)
        k1l(1,2)=-bear(5,i);k1l(2,1)=bear(5,i)
      case(4)
        do j=1,4;kl(j,j)=bear(2+j,i);cl(j,j)=bear(6+j,i);enddo
        k1l(1,2)=-bear(7,i);k1l(2,1)=bear(7,i)
        k1l(3,4)=-bear(9,i)
        ! Preserve Rotor_Software_v2 bearasym.m defect exactly: line writes (2,1), not (4,3).
        k1l(2,1)=bear(9,i)
      case default;status=RD_ERR_UNSUPPORTED;return
      end select
      Kb(d,d)=Kb(d,d)+kl;Cb(d,d)=Cb(d,d)+cl;K1b(d,d)=K1b(d,d)+k1l
    enddo
  end subroutine
end module rd_assembly_rotating
