module rd_frequency_response
  use rd_kinds, only: rk, ik
  use rd_status, only: RD_OK, RD_ERR_INPUT
  use rd_assembly_stationary, only: assemble_rotor
  use rd_bearings, only: assemble_bearings
  use rd_lapack, only: solve_complex
  implicit none(type, external)
  private
  public :: frequency_response_stationary
contains
  subroutine frequency_response_stationary(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear, &
      nforce,force,nbend,bend,nspeed,speeds,response,status)
    integer(ik),intent(in) :: nnode,nshaft,ndisc,nbear,nforce,nbend,nspeed
    real(rk),intent(in) :: z(nnode),shaft(11,nshaft),disc(6,ndisc),bear(34,nbear)
    real(rk),intent(in) :: force(5,nforce),bend(3,nbend),speeds(nspeed)
    complex(rk),intent(out) :: response(4*nnode,nspeed)
    integer(ik),intent(out) :: status
    integer :: ndof,nc,i,j,ispeed,iforce,node,node1,node2,idx,nmaster,nslave
    integer,allocatable :: keep(:),master(:),slave(:)
    logical,allocatable :: is_zero(:),is_master(:)
    logical :: has_bend
    real(rk),allocatable :: M0(:,:),C0(:,:),C1(:,:),K0(:,:),K1(:,:),Mb(:,:),Cb(:,:),Kb(:,:),ecc(:)
    complex(rk),allocatable :: ub(:),pzt(:),bend_force(:),force_c(:),xbend(:),xmaster(:)
    complex(rk),allocatable :: A(:,:),B(:,:),Kss(:,:),Ksm(:,:)
    real(rk) :: mag,phase,omega
    complex(rk) :: ph,jot
    integer(ik) :: st

    status=RD_OK; response=(0._rk,0._rk); jot=cmplx(0._rk,1._rk,rk)
    if (nnode<=0 .or. nspeed<=0 .or. nforce<0 .or. nbend<0) then
      status=RD_ERR_INPUT; return
    end if
    ndof=4*nnode
    allocate(M0(ndof,ndof),C0(ndof,ndof),C1(ndof,ndof),K0(ndof,ndof),K1(ndof,ndof))
    allocate(Mb(ndof,ndof),Cb(ndof,ndof),Kb(ndof,ndof),is_zero(ndof),ecc(nbear))
    call assemble_rotor(nnode,z,nshaft,shaft,ndisc,disc,M0,C0,C1,K0,K1,st)
    if (st/=RD_OK) then; status=st; return; end if
    call assemble_bearings(nnode,nbear,bear,speeds(1),Mb,Cb,Kb,is_zero,ecc,st)
    if (st/=RD_OK) then; status=st; return; end if
    nc=count(.not.is_zero)
    if (nc<=0) then; status=RD_ERR_INPUT; return; end if
    allocate(keep(nc)); idx=0
    do i=1,ndof
      if (.not.is_zero(i)) then; idx=idx+1; keep(idx)=i; end if
    end do

    allocate(ub(ndof),pzt(ndof),bend_force(ndof),xbend(ndof))
    ub=(0._rk,0._rk); pzt=(0._rk,0._rk); bend_force=(0._rk,0._rk); xbend=(0._rk,0._rk)
    has_bend=.false.
    do iforce=1,nforce
      select case(nint(force(1,iforce)))
      case(1)
        node=nint(force(2,iforce)); mag=force(3,iforce); phase=force(4,iforce)
        if (node<1 .or. node>nnode) then; status=RD_ERR_INPUT; return; end if
        ph=exp(jot*phase)
        ub(4*node-3)=ub(4*node-3)+mag*ph
        ub(4*node-2)=ub(4*node-2)-jot*mag*ph
      case(2)
        node=nint(force(2,iforce)); mag=force(3,iforce); phase=force(4,iforce)
        if (node<1 .or. node>nnode) then; status=RD_ERR_INPUT; return; end if
        ph=exp(jot*phase)
        ub(4*node-1)=ub(4*node-1)+jot*mag*ph
        ub(4*node)=ub(4*node)+mag*ph
      case(3)
        has_bend=.true.
      case(8)
        node1=nint(force(2,iforce)); node2=nint(force(3,iforce)); mag=force(4,iforce); phase=force(5,iforce)
        if (node1<1 .or. node1>nnode .or. node2<1 .or. node2>nnode) then
          status=RD_ERR_INPUT; return
        end if
        ph=exp(jot*phase)
        pzt(4*node1-1)=pzt(4*node1-1)+jot*mag*ph
        pzt(4*node1)=pzt(4*node1)+mag*ph
        pzt(4*node2-1)=pzt(4*node2-1)-jot*mag*ph
        pzt(4*node2)=pzt(4*node2)-mag*ph
      case default
        ! V2 freq_rsp ignores force definitions not handled here.
      end select
    end do

    if (has_bend) then
      if (nbend<=0) then; status=RD_ERR_INPUT; return; end if
      nmaster=2*nbend
      allocate(master(nmaster),xmaster(nmaster),is_master(ndof)); is_master=.false.
      do i=1,nbend
        node=nint(bend(1,i))
        if (node<1 .or. node>nnode) then; status=RD_ERR_INPUT; return; end if
        master(2*i-1)=4*node-3; master(2*i)=4*node-2
        if (is_master(master(2*i-1)) .or. is_master(master(2*i))) then
          status=RD_ERR_INPUT; return
        end if
        is_master(master(2*i-1))=.true.; is_master(master(2*i))=.true.
        xmaster(2*i-1)=cmplx(bend(2,i),bend(3,i),rk)
        xmaster(2*i)=cmplx(bend(3,i),-bend(2,i),rk)
      end do
      nslave=ndof-nmaster
      if (nslave>0) then
        allocate(slave(nslave)); idx=0
        do i=1,ndof
          if (.not.is_master(i)) then; idx=idx+1; slave(idx)=i; end if
        end do
        allocate(Kss(nslave,nslave),Ksm(nslave,nmaster),B(nslave,1))
        do j=1,nslave
          do i=1,nslave
            Kss(i,j)=cmplx(K0(slave(i),slave(j)),0._rk,rk)
          end do
        end do
        do j=1,nmaster
          do i=1,nslave
            Ksm(i,j)=cmplx(K0(slave(i),master(j)),0._rk,rk)
          end do
        end do
        B(:,1)=-matmul(Ksm,xmaster)
        call solve_complex(Kss,B,st)
        if (st/=RD_OK) then; status=st; return; end if
        do i=1,nslave; xbend(slave(i))=B(i,1); end do
      end if
      do i=1,nmaster; xbend(master(i))=xmaster(i); end do
      bend_force=matmul(cmplx(K0,0._rk,rk),xbend)
    end if

    allocate(force_c(nc),A(nc,nc),B(nc,1))
    do ispeed=1,nspeed
      omega=speeds(ispeed)
      call assemble_bearings(nnode,nbear,bear,omega,Mb,Cb,Kb,is_zero,ecc,st)
      if (st/=RD_OK) then; status=st; return; end if
      force_c=(0._rk,0._rk)
      do i=1,nc
        force_c(i)=bend_force(keep(i))+pzt(keep(i))+ub(keep(i))*omega**2
      end do
      do j=1,nc
        do i=1,nc
          A(i,j)=cmplx(K0(keep(i),keep(j))+Kb(keep(i),keep(j))+omega*K1(keep(i),keep(j)) &
                  -omega**2*(M0(keep(i),keep(j))+Mb(keep(i),keep(j))), &
                  omega*(C0(keep(i),keep(j))+Cb(keep(i),keep(j))+omega*C1(keep(i),keep(j))),rk)
        end do
      end do
      B(:,1)=force_c
      call solve_complex(A,B,st)
      if (st/=RD_OK) then; status=st; return; end if
      do i=1,nc; response(keep(i),ispeed)=B(i,1); end do
    end do
  end subroutine frequency_response_stationary
end module rd_frequency_response
