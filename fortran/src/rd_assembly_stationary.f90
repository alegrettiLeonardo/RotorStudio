module rd_assembly_stationary
  use rd_kinds, only: rk, ik
  use rd_status, only: RD_OK, RD_ERR_INPUT, RD_ERR_UNSUPPORTED
  use rd_shaft_circular, only: shaft_circular_matrices
  use rd_shaft_tapered, only: shaft_tapered_matrices
  implicit none(type, external)
  private
  public :: assemble_rotor
contains
  subroutine assemble_rotor(nnode,z,nshaft,shaft,ndisc,disc,M,C0,C1,K0,K1,status)
    integer(ik),intent(in) :: nnode,nshaft,ndisc
    real(rk),intent(in) :: z(nnode),shaft(11,nshaft),disc(6,ndisc)
    real(rk),intent(out) :: M(4*nnode,4*nnode),C0(4*nnode,4*nnode),C1(4*nnode,4*nnode)
    real(rk),intent(out) :: K0(4*nnode,4*nnode),K1(4*nnode,4*nnode)
    integer(ik),intent(out) :: status
    integer :: i,j,k,n1,n2,dofs(8),dof4(4),stype,dtype
    real(rk) :: Me(8,8),Ge(8,8),Ke(8,8),K1e(8,8),Le
    real(rk) :: do_,di,rho,E,G,df,axial,torque,pi_,thick,mass_d,Id,Ip
    real(rk) :: do1,do2,di1,di2
    integer(ik) :: st

    M=0._rk; C0=0._rk; C1=0._rk; K0=0._rk; K1=0._rk
    status=RD_OK; pi_=acos(-1._rk)
    if (nnode<=0 .or. nshaft<0 .or. ndisc<0) then
      status=RD_ERR_INPUT; return
    end if

    do i=1,nshaft
      stype=nint(shaft(1,i)); n1=nint(shaft(2,i)); n2=nint(shaft(3,i))
      if (n1<1 .or. n1>nnode .or. n2<1 .or. n2>nnode) then
        status=RD_ERR_INPUT; return
      end if
      Le=z(n2)-z(n1)
      if (stype>=1 .and. stype<=8) then
        do_=shaft(4,i); di=shaft(5,i); rho=shaft(6,i); E=shaft(7,i); G=shaft(8,i)
        df=shaft(9,i); axial=shaft(10,i); torque=shaft(11,i)
        call shaft_circular_matrices(stype,Le,do_,di,E,G,rho,axial,torque,Me,Ge,Ke,K1e,st)
      else if (stype>=21 .and. stype<=28) then
        do1=shaft(4,i); do2=shaft(5,i); di1=shaft(6,i); di2=shaft(7,i)
        rho=shaft(8,i); E=shaft(9,i); G=shaft(10,i); axial=shaft(11,i)
        df=0._rk; torque=0._rk
        call shaft_tapered_matrices(stype,Le,do1,do2,di1,di2,E,G,rho,axial,Me,Ge,Ke,K1e,st)
      else
        status=RD_ERR_UNSUPPORTED; return
      end if
      if (st/=RD_OK) then
        status=st; return
      end if
      dofs=[4*n1-3,4*n1-2,4*n1-1,4*n1,4*n2-3,4*n2-2,4*n2-1,4*n2]
      do j=1,8
        do k=1,8
          M(dofs(j),dofs(k))=M(dofs(j),dofs(k))+Me(j,k)
          C0(dofs(j),dofs(k))=C0(dofs(j),dofs(k))+df*Ke(j,k)
          C1(dofs(j),dofs(k))=C1(dofs(j),dofs(k))+Ge(j,k)
          K0(dofs(j),dofs(k))=K0(dofs(j),dofs(k))+Ke(j,k)
          K1(dofs(j),dofs(k))=K1(dofs(j),dofs(k))+df*K1e(j,k)
        end do
      end do
    end do

    do i=1,ndisc
      dtype=nint(disc(1,i)); n1=nint(disc(2,i))
      if (n1<1 .or. n1>nnode) then
        status=RD_ERR_INPUT; return
      end if
      if (dtype==1 .or. dtype==3) then
        rho=disc(3,i); thick=disc(4,i); do_=disc(5,i); di=disc(6,i)
        if (rho<=0._rk .or. thick<=0._rk .or. do_<=di .or. di<0._rk) then
          status=RD_ERR_INPUT; return
        end if
        mass_d=0.25_rk*rho*pi_*thick*(do_**2-di**2)
        Id=0.015625_rk*rho*pi_*thick*(do_**4-di**4)+mass_d*thick**2/12._rk
        Ip=0.03125_rk*rho*pi_*thick*(do_**4-di**4)
      else if (dtype==2 .or. dtype==4) then
        mass_d=disc(3,i); Id=disc(4,i); Ip=disc(5,i)
        if (mass_d<=0._rk .or. Id<0._rk) then
          status=RD_ERR_INPUT; return
        end if
      else
        status=RD_ERR_UNSUPPORTED; return
      end if
      dof4=[4*n1-3,4*n1-2,4*n1-1,4*n1]
      M(dof4(1),dof4(1))=M(dof4(1),dof4(1))+mass_d
      M(dof4(2),dof4(2))=M(dof4(2),dof4(2))+mass_d
      M(dof4(3),dof4(3))=M(dof4(3),dof4(3))+Id
      M(dof4(4),dof4(4))=M(dof4(4),dof4(4))+Id
      if (dtype==1 .or. dtype==2) then
        C1(dof4(3),dof4(4))=C1(dof4(3),dof4(4))+Ip
        C1(dof4(4),dof4(3))=C1(dof4(4),dof4(3))-Ip
      end if
    end do
  end subroutine assemble_rotor
end module rd_assembly_stationary
