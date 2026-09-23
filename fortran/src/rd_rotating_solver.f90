module rd_rotating_solver
  use rd_kinds,only:rk,ik
  use rd_status,only:RD_OK,RD_ERR_INPUT
  use rd_assembly_rotating,only:assemble_rotor_rotating,assemble_bearings_rotating
  use rd_eigensystem,only:second_order_eigs
  use rd_lapack,only:solve_real
  implicit none(type,external);private
  public::asymmetric_eigs,asymmetric_frequency_response
contains
  subroutine asymmetric_eigs(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,speed,include_vectors_semantics,w,Vfull,status)
    integer(ik),intent(in)::nnode,nshaft,ndisc,nbear;real(rk),intent(in)::z(nnode),shaft(11,nshaft),disc(6,ndisc),bear(34,nbear),speed
    logical,intent(in)::include_vectors_semantics;complex(rk),intent(out)::w(:),Vfull(:,:);integer(ik),intent(out)::status
    real(rk),allocatable::M(:,:),C0(:,:),C1(:,:),K0(:,:),K1(:,:),K2(:,:),Cb(:,:),Kb(:,:),K1b(:,:),C(:,:),K(:,:)
    logical,allocatable::iz(:);integer,allocatable::keep(:);complex(rk),allocatable::Vr(:,:);integer::ndof,nc,i,j,idx
    ndof=4*nnode;allocate(M(ndof,ndof),C0(ndof,ndof),C1(ndof,ndof),K0(ndof,ndof),K1(ndof,ndof),K2(ndof,ndof),Cb(ndof,ndof),Kb(ndof,ndof),K1b(ndof,ndof),iz(ndof))
    call assemble_rotor_rotating(nnode,z,nshaft,shaft,ndisc,disc,M,C0,C1,K0,K1,K2,status);if(status/=RD_OK)return
    call assemble_bearings_rotating(nnode,nbear,bear,Cb,Kb,K1b,iz,status);if(status/=RD_OK)return
    nc=count(.not.iz);if(size(w)<2*nc.or.size(Vfull,1)<ndof.or.size(Vfull,2)<2*nc)then;status=RD_ERR_INPUT;return;endif
    allocate(keep(nc));idx=0;do i=1,ndof;if(.not.iz(i))then;idx=idx+1;keep(idx)=i;endif;enddo
    allocate(C(nc,nc),K(nc,nc),Vr(nc,2*nc))
    do j=1,nc;do i=1,nc
      C(i,j)=C0(keep(i),keep(j))+Cb(keep(i),keep(j))+speed*C1(keep(i),keep(j))
      if(include_vectors_semantics)then
        ! Preserve chr_asym.m nargout==2 path: K1b is omitted in V2.
        K(i,j)=K0(keep(i),keep(j))+Kb(keep(i),keep(j))+speed*K1(keep(i),keep(j))+speed**2*K2(keep(i),keep(j))
      else
        K(i,j)=K0(keep(i),keep(j))+Kb(keep(i),keep(j))+speed*(K1(keep(i),keep(j))+K1b(keep(i),keep(j)))+speed**2*K2(keep(i),keep(j))
      endif
    enddo;enddo
    call second_order_eigs(M(keep,keep),C,K,w(1:2*nc),Vr,status);if(status/=RD_OK)return
    Vfull=(0._rk,0._rk);do i=1,nc;Vfull(keep(i),1:2*nc)=Vr(i,:);enddo
  end subroutine

  subroutine asymmetric_frequency_response(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,nforce,force,nspeed,speeds,response,status)
    integer(ik),intent(in)::nnode,nshaft,ndisc,nbear,nforce,nspeed;real(rk),intent(in)::z(nnode),shaft(11,nshaft),disc(6,ndisc),bear(34,nbear),force(5,nforce),speeds(nspeed)
    real(rk),intent(out)::response(4*nnode,nspeed);integer(ik),intent(out)::status
    real(rk),allocatable::M(:,:),C0(:,:),C1(:,:),K0(:,:),K1(:,:),K2(:,:),Cb(:,:),Kb(:,:),K1b(:,:),K(:,:),rhs(:,:),ub(:)
    logical,allocatable::iz(:);integer,allocatable::keep(:);integer::ndof,nc,i,j,ispeed,node,idx
    ndof=4*nnode;response=0;allocate(M(ndof,ndof),C0(ndof,ndof),C1(ndof,ndof),K0(ndof,ndof),K1(ndof,ndof),K2(ndof,ndof),Cb(ndof,ndof),Kb(ndof,ndof),K1b(ndof,ndof),iz(ndof),ub(ndof));ub=0
    call assemble_rotor_rotating(nnode,z,nshaft,shaft,ndisc,disc,M,C0,C1,K0,K1,K2,status);if(status/=RD_OK)return
    call assemble_bearings_rotating(nnode,nbear,bear,Cb,Kb,K1b,iz,status);if(status/=RD_OK)return
    do i=1,nforce
      node=nint(force(2,i));if(node<1.or.node>nnode)then;status=RD_ERR_INPUT;return;endif
      if(nint(force(1,i))==1)then
        ub(4*node-3)=ub(4*node-3)+force(3,i)*cos(force(4,i));ub(4*node-2)=ub(4*node-2)+force(3,i)*sin(force(4,i))
      elseif(nint(force(1,i))==2)then
        ub(4*node-1)=ub(4*node-1)-force(3,i)*sin(force(4,i));ub(4*node)=ub(4*node)+force(3,i)*cos(force(4,i))
      endif
    enddo
    nc=count(.not.iz);allocate(keep(nc));idx=0;do i=1,ndof;if(.not.iz(i))then;idx=idx+1;keep(idx)=i;endif;enddo
    allocate(K(nc,nc),rhs(nc,1))
    do ispeed=1,nspeed
      do j=1,nc;do i=1,nc
        K(i,j)=K0(keep(i),keep(j))+Kb(keep(i),keep(j))+speeds(ispeed)*(K1(keep(i),keep(j))+K1b(keep(i),keep(j)))+speeds(ispeed)**2*K2(keep(i),keep(j))
      enddo;enddo
      do i=1,nc;rhs(i,1)=ub(keep(i));enddo
      call solve_real(K,rhs,status);if(status/=RD_OK)return
      do i=1,nc;response(keep(i),ispeed)=speeds(ispeed)**2*rhs(i,1);enddo
    enddo
  end subroutine
end module rd_rotating_solver
