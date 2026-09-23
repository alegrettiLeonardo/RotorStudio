module rd_coaxial_solver
  use rd_kinds,only:rk,ik
  use rd_status,only:RD_OK,RD_ERR_INPUT
  use rd_assembly_stationary,only:assemble_rotor,assemble_bearings
  use rd_eigensystem,only:second_order_eigs
  use rd_lapack,only:solve_complex
  implicit none(type,external);private
  public::coaxial_eigs,coaxial_frequency_response
contains
  subroutine coaxial_eigs(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,nrotor,rotors,speed,w,Vfull,status)
    integer(ik),intent(in)::nnode,nshaft,ndisc,nbear,nrotor
    real(rk),intent(in)::z(nnode),shaft(11,nshaft),disc(6,ndisc),bear(34,nbear),rotors(3,nrotor),speed
    complex(rk),intent(out)::w(:),Vfull(:,:);integer(ik),intent(out)::status
    real(rk),allocatable::M0(:,:),C0(:,:),C1(:,:),K0(:,:),K1(:,:),Mb(:,:),Cb(:,:),Kb(:,:),M(:,:),C(:,:),K(:,:),rel(:)
    logical,allocatable::iz(:);integer,allocatable::keep(:);complex(rk),allocatable::Vr(:,:)
    integer::ndof,nc,i,j,idx
    ndof=4*nnode;status=RD_OK
    allocate(M0(ndof,ndof),C0(ndof,ndof),C1(ndof,ndof),K0(ndof,ndof),K1(ndof,ndof),Mb(ndof,ndof),Cb(ndof,ndof),Kb(ndof,ndof),iz(ndof),rel(ndof))
    call assemble_rotor(nnode,z,nshaft,shaft,ndisc,disc,M0,C0,C1,K0,K1,status);if(status/=RD_OK)return
    call assemble_bearings(nnode,nbear,bear,speed,Mb,Cb,Kb,iz,status);if(status/=RD_OK)return
    call add_coaxial_links(nnode,nbear,bear,K0,C0,status);if(status/=RD_OK)return
    call relative_speed_vector(nnode,nrotor,rotors,rel,status);if(status/=RD_OK)return
    nc=count(.not.iz);if(size(w)<2*nc.or.size(Vfull,1)<ndof.or.size(Vfull,2)<2*nc)then;status=RD_ERR_INPUT;return;endif
    allocate(keep(nc));idx=0;do i=1,ndof;if(.not.iz(i))then;idx=idx+1;keep(idx)=i;endif;enddo
    allocate(M(nc,nc),C(nc,nc),K(nc,nc),Vr(nc,2*nc))
    do j=1,nc;do i=1,nc
      M(i,j)=M0(keep(i),keep(j))+Mb(keep(i),keep(j))
      C(i,j)=C0(keep(i),keep(j))+Cb(keep(i),keep(j))+speed*rel(keep(i))*C1(keep(i),keep(j))
      K(i,j)=K0(keep(i),keep(j))+Kb(keep(i),keep(j))+speed*rel(keep(i))*K1(keep(i),keep(j))
    enddo;enddo
    call second_order_eigs(M,C,K,w(1:2*nc),Vr,status);if(status/=RD_OK)return
    Vfull=(0._rk,0._rk);do i=1,nc;Vfull(keep(i),1:2*nc)=Vr(i,:);enddo
  end subroutine

  subroutine coaxial_frequency_response(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,nrotor,rotors,nforce,force,nspeed,speeds,response,status)
    integer(ik),intent(in)::nnode,nshaft,ndisc,nbear,nrotor,nforce,nspeed
    real(rk),intent(in)::z(nnode),shaft(11,nshaft),disc(6,ndisc),bear(34,nbear),rotors(3,nrotor),force(5,nforce),speeds(nspeed)
    complex(rk),intent(out)::response(4*nnode,nspeed);integer(ik),intent(out)::status
    real(rk),allocatable::M0(:,:),C0(:,:),C1(:,:),K0(:,:),K1(:,:),Mb(:,:),Cb(:,:),Kb(:,:),rel(:)
    logical,allocatable::iz(:);integer,allocatable::keep(:)
    complex(rk),allocatable::ub(:,:),A(:,:),rhs(:,:);complex(rk)::phase,jot
    integer::ndof,nc,i,j,k,node,irotor,irotor_ub,idx;real(rk)::excspd
    ndof=4*nnode;response=(0._rk,0._rk);status=RD_OK;jot=(0._rk,1._rk)
    allocate(M0(ndof,ndof),C0(ndof,ndof),C1(ndof,ndof),K0(ndof,ndof),K1(ndof,ndof),Mb(ndof,ndof),Cb(ndof,ndof),Kb(ndof,ndof),iz(ndof),rel(ndof))
    call assemble_rotor(nnode,z,nshaft,shaft,ndisc,disc,M0,C0,C1,K0,K1,status);if(status/=RD_OK)return
    call add_coaxial_links(nnode,nbear,bear,K0,C0,status);if(status/=RD_OK)return
    call relative_speed_vector(nnode,nrotor,rotors,rel,status);if(status/=RD_OK)return
    allocate(ub(ndof,nrotor));ub=(0._rk,0._rk);irotor_ub=0
    do i=1,nforce
      if(nint(force(1,i))==1)then
        node=nint(force(2,i));if(node<1.or.node>nnode)then;status=RD_ERR_INPUT;return;endif
        do irotor=1,nrotor
          if(node>=nint(rotors(1,irotor)).and.node<=nint(rotors(2,irotor)))irotor_ub=irotor
        enddo
        if(irotor_ub==0)then;status=RD_ERR_INPUT;return;endif
        phase=force(3,i)*cmplx(cos(force(4,i)),sin(force(4,i)),rk)
        ub(4*node-3,irotor_ub)=ub(4*node-3,irotor_ub)+phase
        ub(4*node-2,irotor_ub)=ub(4*node-2,irotor_ub)-jot*phase
      endif
    enddo
    if(irotor_ub==0)then;status=RD_ERR_INPUT;return;endif
    do k=1,nspeed
      call assemble_bearings(nnode,nbear,bear,speeds(k),Mb,Cb,Kb,iz,status);if(status/=RD_OK)return
      nc=count(.not.iz);allocate(keep(nc));idx=0;do i=1,ndof;if(.not.iz(i))then;idx=idx+1;keep(idx)=i;endif;enddo
      allocate(A(nc,nc),rhs(nc,1));excspd=rotors(3,irotor_ub)*speeds(k)
      do j=1,nc;do i=1,nc
        A(i,j)=cmplx(K0(keep(i),keep(j))+Kb(keep(i),keep(j))+speeds(k)*rel(keep(i))*K1(keep(i),keep(j)) - &
          excspd**2*(M0(keep(i),keep(j))+Mb(keep(i),keep(j))), &
          excspd*(C0(keep(i),keep(j))+Cb(keep(i),keep(j))+speeds(k)*rel(keep(i))*C1(keep(i),keep(j))),rk)
      enddo;enddo
      do i=1,nc;rhs(i,1)=ub(keep(i),irotor_ub)*excspd**2;enddo
      call solve_complex(A,rhs,status);if(status/=RD_OK)return
      do i=1,nc;response(keep(i),k)=rhs(i,1);enddo
      deallocate(keep,A,rhs)
    enddo
  end subroutine

  subroutine relative_speed_vector(nnode,nrotor,rotors,rel,status)
    integer(ik),intent(in)::nnode,nrotor;real(rk),intent(in)::rotors(3,nrotor);real(rk),intent(out)::rel(4*nnode);integer(ik),intent(out)::status
    integer::r,n1,n2;rel=0;status=RD_OK
    do r=1,nrotor;n1=nint(rotors(1,r));n2=nint(rotors(2,r));if(n1<1.or.n2>nnode.or.n2<n1)then;status=RD_ERR_INPUT;return;endif
      rel(4*n1-3:4*n2)=rotors(3,r)
    enddo
  end subroutine

  subroutine add_coaxial_links(nnode,nbear,bear,K0,C0,status)
    integer(ik),intent(in)::nnode,nbear;real(rk),intent(in)::bear(34,nbear);real(rk),intent(inout)::K0(4*nnode,4*nnode),C0(4*nnode,4*nnode);integer(ik),intent(out)::status
    integer::i,n1,n2,d1,d2;status=RD_OK
    do i=1,nbear
      if(nint(bear(1,i))==20)then
        n1=nint(bear(2,i));n2=nint(bear(3,i));if(n1<1.or.n1>nnode.or.n2<1.or.n2>nnode)then;status=RD_ERR_INPUT;return;endif
        d1=4*n1-3;d2=4*n2-3;call add_pair(K0,d1,d2,bear(4,i));call add_pair(C0,d1,d2,bear(6,i))
        d1=4*n1-2;d2=4*n2-2;call add_pair(K0,d1,d2,bear(5,i));call add_pair(C0,d1,d2,bear(7,i))
      endif
    enddo
  contains
    subroutine add_pair(A,i1,i2,v)
      real(rk),intent(inout)::A(:,:);integer,intent(in)::i1,i2;real(rk),intent(in)::v
      A(i1,i1)=A(i1,i1)+v;A(i2,i2)=A(i2,i2)+v;A(i1,i2)=A(i1,i2)-v;A(i2,i1)=A(i2,i1)-v
    end subroutine
  end subroutine
end module rd_coaxial_solver
