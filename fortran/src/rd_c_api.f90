module rd_c_api
  use, intrinsic :: iso_c_binding, only: c_int, c_double
  use rd_kinds, only: rk, ik
  use rd_status, only: RD_OK, RD_ERR_INPUT, RD_ERR_UNSUPPORTED
  use rd_shaft_circular, only: shaft_circular_matrices
  use rd_shaft_tapered, only: shaft_tapered_matrices
  use rd_shaft_asymmetric, only: shaft_asymmetric_matrices
  use rd_assembly_stationary, only: assemble_rotor
  use rd_bearings, only: assemble_bearings
  use rd_eigensystem, only: stationary_eigs, stationary_eigensystem
  use rd_frequency_response, only: frequency_response_stationary
  use rd_critical_speed, only: critical_speeds_stationary
  implicit none(type, external)
  private
  public :: rd_modal_legacy, rd_modal_full_legacy, rd_version, rd_assemble_legacy
  public :: rd_frequency_response_legacy, rd_critical_speeds_legacy, rd_critical_speeds_full_legacy
  public :: rd_shaft_element_legacy
contains
  integer(c_int) function rd_version(major,minor,patch) bind(C,name='rd_version')
    integer(c_int),intent(out) :: major,minor,patch
    major=0; minor=3; patch=0; rd_version=0
  end function rd_version

  integer(c_int) function rd_shaft_element_legacy(stype,L,params,mass,c1,stiff,kaux) &
      bind(C,name='rd_shaft_element_legacy')
    integer(c_int),value :: stype
    real(c_double),value :: L
    real(c_double),intent(in) :: params(*)
    real(c_double),intent(out) :: mass(*),c1(*),stiff(*),kaux(*)
    real(rk) :: M(8,8),C(8,8),K(8,8),KA(8,8)
    integer :: i,j,idx
    integer(ik) :: st
    select case(stype)
    case(1:8)
      ! params: do, di, rho, E, G, axial, torque, unused
      call shaft_circular_matrices(int(stype,ik),real(L,rk),params(1),params(2),params(4),params(5), &
        params(3),params(6),params(7),M,C,K,KA,st)
    case(11:18)
      ! params: EIx, EIy, Phix, Phiy, rhoA, rhoI, axial, unused
      call shaft_asymmetric_matrices(int(stype,ik),real(L,rk),params(1),params(2),params(3),params(4), &
        params(5),params(6),params(7),M,C,K,KA,st)
    case(21:28)
      ! params: do1, do2, di1, di2, rho, E, G, axial
      call shaft_tapered_matrices(int(stype,ik),real(L,rk),params(1),params(2),params(3),params(4), &
        params(6),params(7),params(5),params(8),M,C,K,KA,st)
    case default
      rd_shaft_element_legacy=RD_ERR_UNSUPPORTED; return
    end select
    if (st/=RD_OK) then; rd_shaft_element_legacy=st; return; end if
    idx=0
    do j=1,8
      do i=1,8
        idx=idx+1; mass(idx)=M(i,j); c1(idx)=C(i,j); stiff(idx)=K(i,j); kaux(idx)=KA(i,j)
      end do
    end do
    rd_shaft_element_legacy=RD_OK
  end function rd_shaft_element_legacy

  integer(c_int) function rd_modal_legacy(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,speed,nout,er,ei) &
      bind(C,name='rd_modal_legacy')
    integer(c_int),value :: nnode,nshaft,ndisc,nbear,nout
    real(c_double),intent(in) :: z(*),shaft(*),disc(*),bear(*)
    real(c_double),value :: speed
    real(c_double),intent(out) :: er(*),ei(*)
    real(rk),allocatable :: zz(:),sh(:,:),di(:,:),be(:,:),M(:,:),C0(:,:),C1(:,:),K0(:,:),K1(:,:)
    real(rk),allocatable :: Mb(:,:),Cb(:,:),Kb(:,:),Mc(:,:),Cc(:,:),Kc(:,:),wr(:),wi(:),ecc(:)
    logical,allocatable :: iz(:)
    integer,allocatable :: keep(:)
    integer :: i,j,ndof,nc,idx
    integer(ik) :: st

    rd_modal_legacy=RD_ERR_INPUT
    if (nnode<=0 .or. nshaft<0 .or. ndisc<0 .or. nbear<0) return
    ndof=4*nnode
    call unpack_model_arrays(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,zz,sh,di,be)
    allocate(M(ndof,ndof),C0(ndof,ndof),C1(ndof,ndof),K0(ndof,ndof),K1(ndof,ndof))
    allocate(Mb(ndof,ndof),Cb(ndof,ndof),Kb(ndof,ndof),iz(ndof),ecc(nbear))
    call assemble_rotor(nnode,zz,nshaft,sh,ndisc,di,M,C0,C1,K0,K1,st)
    if (st/=RD_OK) then; rd_modal_legacy=st; return; end if
    call assemble_bearings(nnode,nbear,be,speed,Mb,Cb,Kb,iz,ecc,st)
    if (st/=RD_OK) then; rd_modal_legacy=st; return; end if
    nc=count(.not.iz)
    if (nout<2*nc .or. nc<=0) return
    allocate(keep(nc)); idx=0
    do i=1,ndof
      if (.not.iz(i)) then; idx=idx+1; keep(idx)=i; end if
    end do
    allocate(Mc(nc,nc),Cc(nc,nc),Kc(nc,nc),wr(2*nc),wi(2*nc))
    call reduce_stationary_matrices(ndof,nc,keep,M,C0,C1,K0,K1,Mb,Cb,Kb,speed,Mc,Cc,Kc)
    call stationary_eigs(Mc,Cc,Kc,wr,wi,st)
    if (st/=RD_OK) then; rd_modal_legacy=st; return; end if
    do i=1,2*nc; er(i)=wr(i); ei(i)=wi(i); end do
    rd_modal_legacy=RD_OK
  end function rd_modal_legacy

  integer(c_int) function rd_modal_full_legacy(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,speed,nout, &
      er,ei,vr_out,vi_out,ecc_out) bind(C,name='rd_modal_full_legacy')
    integer(c_int),value :: nnode,nshaft,ndisc,nbear,nout
    real(c_double),intent(in) :: z(*),shaft(*),disc(*),bear(*)
    real(c_double),value :: speed
    real(c_double),intent(out) :: er(*),ei(*),vr_out(*),vi_out(*),ecc_out(*)
    real(rk),allocatable :: zz(:),sh(:,:),di(:,:),be(:,:),M(:,:),C0(:,:),C1(:,:),K0(:,:),K1(:,:)
    real(rk),allocatable :: Mb(:,:),Cb(:,:),Kb(:,:),Mc(:,:),Cc(:,:),Kc(:,:),ecc(:)
    complex(rk),allocatable :: w(:),u(:,:)
    logical,allocatable :: iz(:)
    integer,allocatable :: keep(:)
    integer :: i,j,ndof,nc,idx
    integer(ik) :: st

    rd_modal_full_legacy=RD_ERR_INPUT
    if (nnode<=0 .or. nshaft<0 .or. ndisc<0 .or. nbear<0) return
    ndof=4*nnode
    call unpack_model_arrays(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,zz,sh,di,be)
    allocate(M(ndof,ndof),C0(ndof,ndof),C1(ndof,ndof),K0(ndof,ndof),K1(ndof,ndof))
    allocate(Mb(ndof,ndof),Cb(ndof,ndof),Kb(ndof,ndof),iz(ndof),ecc(nbear))
    call assemble_rotor(nnode,zz,nshaft,sh,ndisc,di,M,C0,C1,K0,K1,st)
    if (st/=RD_OK) then; rd_modal_full_legacy=st; return; end if
    call assemble_bearings(nnode,nbear,be,speed,Mb,Cb,Kb,iz,ecc,st)
    if (st/=RD_OK) then; rd_modal_full_legacy=st; return; end if
    nc=count(.not.iz)
    if (nout<2*nc .or. nc<=0) return
    allocate(keep(nc)); idx=0
    do i=1,ndof
      if (.not.iz(i)) then; idx=idx+1; keep(idx)=i; end if
    end do
    allocate(Mc(nc,nc),Cc(nc,nc),Kc(nc,nc),w(2*nc),u(nc,2*nc))
    call reduce_stationary_matrices(ndof,nc,keep,M,C0,C1,K0,K1,Mb,Cb,Kb,speed,Mc,Cc,Kc)
    call stationary_eigensystem(Mc,Cc,Kc,w,u,st)
    if (st/=RD_OK) then; rd_modal_full_legacy=st; return; end if
    do i=1,2*nc; er(i)=real(w(i),rk); ei(i)=aimag(w(i)); end do
    idx=0
    do j=1,2*nc
      do i=1,ndof
        idx=idx+1; vr_out(idx)=0._rk; vi_out(idx)=0._rk
      end do
    end do
    do j=1,2*nc
      do i=1,nc
        idx=(j-1)*ndof+keep(i)
        vr_out(idx)=real(u(i,j),rk); vi_out(idx)=aimag(u(i,j))
      end do
    end do
    do i=1,nbear; ecc_out(i)=ecc(i); end do
    rd_modal_full_legacy=RD_OK
  end function rd_modal_full_legacy

  integer(c_int) function rd_assemble_legacy(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,speed, &
      mass,damp,gyro,stiff,kspin,zero_dof,ecc_out) bind(C,name='rd_assemble_legacy')
    integer(c_int),value :: nnode,nshaft,ndisc,nbear
    real(c_double),intent(in) :: z(*),shaft(*),disc(*),bear(*)
    real(c_double),value :: speed
    real(c_double),intent(out) :: mass(*),damp(*),gyro(*),stiff(*),kspin(*),ecc_out(*)
    integer(c_int),intent(out) :: zero_dof(*)
    real(rk),allocatable :: zz(:),sh(:,:),di(:,:),be(:,:),M0(:,:),C0(:,:),C1(:,:),K0(:,:),K1(:,:)
    real(rk),allocatable :: Mb(:,:),Cb(:,:),Kb(:,:),ecc(:)
    logical,allocatable :: iz(:)
    integer :: i,j,idx,ndof
    integer(ik) :: st

    rd_assemble_legacy=RD_ERR_INPUT
    if (nnode<=0 .or. nshaft<0 .or. ndisc<0 .or. nbear<0) return
    ndof=4*nnode
    call unpack_model_arrays(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,zz,sh,di,be)
    allocate(M0(ndof,ndof),C0(ndof,ndof),C1(ndof,ndof),K0(ndof,ndof),K1(ndof,ndof))
    allocate(Mb(ndof,ndof),Cb(ndof,ndof),Kb(ndof,ndof),ecc(nbear),iz(ndof))
    call assemble_rotor(nnode,zz,nshaft,sh,ndisc,di,M0,C0,C1,K0,K1,st)
    if (st/=RD_OK) then; rd_assemble_legacy=st; return; end if
    call assemble_bearings(nnode,nbear,be,speed,Mb,Cb,Kb,iz,ecc,st)
    if (st/=RD_OK) then; rd_assemble_legacy=st; return; end if
    idx=0
    do j=1,ndof
      do i=1,ndof
        idx=idx+1
        mass(idx)=M0(i,j)+Mb(i,j)
        damp(idx)=C0(i,j)+Cb(i,j)
        gyro(idx)=C1(i,j)
        stiff(idx)=K0(i,j)+Kb(i,j)
        kspin(idx)=K1(i,j)
      end do
    end do
    do i=1,ndof; zero_dof(i)=merge(1_c_int,0_c_int,iz(i)); end do
    do i=1,nbear; ecc_out(i)=ecc(i); end do
    rd_assemble_legacy=RD_OK
  end function rd_assemble_legacy

  integer(c_int) function rd_frequency_response_legacy(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear, &
      nforce,force,nbend,bend,nspeed,speeds,rr,ri) bind(C,name='rd_frequency_response_legacy')
    integer(c_int),value :: nnode,nshaft,ndisc,nbear,nforce,nbend,nspeed
    real(c_double),intent(in) :: z(*),shaft(*),disc(*),bear(*),force(*),bend(*),speeds(*)
    real(c_double),intent(out) :: rr(*),ri(*)
    real(rk),allocatable :: zz(:),sh(:,:),di(:,:),be(:,:),fo(:,:),bn(:,:),sp(:)
    complex(rk),allocatable :: resp(:,:)
    integer :: i,j,idx,ndof
    integer(ik) :: st

    rd_frequency_response_legacy=RD_ERR_INPUT
    if (nnode<=0 .or. nspeed<=0 .or. nforce<0 .or. nbend<0) return
    ndof=4*nnode
    call unpack_model_arrays(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,zz,sh,di,be)
    allocate(fo(5,nforce),bn(3,nbend),sp(nspeed),resp(ndof,nspeed))
    do j=1,nforce; do i=1,5; fo(i,j)=force((j-1)*5+i); end do; end do
    do j=1,nbend; do i=1,3; bn(i,j)=bend((j-1)*3+i); end do; end do
    do i=1,nspeed; sp(i)=speeds(i); end do
    call frequency_response_stationary(nnode,zz,nshaft,sh,ndisc,di,nbear,be,nforce,fo,nbend,bn,nspeed,sp,resp,st)
    if (st/=RD_OK) then; rd_frequency_response_legacy=st; return; end if
    idx=0
    do j=1,nspeed
      do i=1,ndof
        idx=idx+1; rr(idx)=real(resp(i,j),rk); ri(idx)=aimag(resp(i,j))
      end do
    end do
    rd_frequency_response_legacy=RD_OK
  end function rd_frequency_response_legacy

  integer(c_int) function rd_critical_speeds_legacy(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear, &
      method,nx,damped,ncrit,max_iterations,tol,initial,critical,iterations,converged) &
      bind(C,name='rd_critical_speeds_legacy')
    integer(c_int),value :: nnode,nshaft,ndisc,nbear,method,damped,ncrit,max_iterations
    real(c_double),intent(in) :: z(*),shaft(*),disc(*),bear(*),initial(*)
    real(c_double),value :: nx,tol
    real(c_double),intent(out) :: critical(*)
    integer(c_int),intent(out) :: iterations(*),converged(*)
    real(rk),allocatable :: zz(:),sh(:,:),di(:,:),be(:,:),ini(:),crit(:)
    integer(ik),allocatable :: it(:)
    logical,allocatable :: conv(:)
    integer :: i
    integer(ik) :: st

    rd_critical_speeds_legacy=RD_ERR_INPUT
    if (nnode<=0 .or. ncrit<=0) return
    call unpack_model_arrays(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,zz,sh,di,be)
    allocate(ini(ncrit),crit(ncrit),it(ncrit),conv(ncrit))
    do i=1,ncrit; ini(i)=initial(i); end do
    call critical_speeds_stationary(nnode,zz,nshaft,sh,ndisc,di,nbear,be,method,nx,damped,ncrit, &
      max_iterations,tol,ini,crit,it,conv,st)
    if (st/=RD_OK) then; rd_critical_speeds_legacy=st; return; end if
    do i=1,ncrit
      critical(i)=crit(i); iterations(i)=it(i); converged(i)=merge(1_c_int,0_c_int,conv(i))
    end do
    rd_critical_speeds_legacy=RD_OK
  end function rd_critical_speeds_legacy

  integer(c_int) function rd_critical_speeds_full_legacy(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear, &
      method,nx,damped,ncrit,max_iterations,tol,initial,critical,iterations,converged,mr,mi) &
      bind(C,name='rd_critical_speeds_full_legacy')
    integer(c_int),value :: nnode,nshaft,ndisc,nbear,method,damped,ncrit,max_iterations
    real(c_double),intent(in) :: z(*),shaft(*),disc(*),bear(*),initial(*)
    real(c_double),value :: nx,tol
    real(c_double),intent(out) :: critical(*),mr(*),mi(*)
    integer(c_int),intent(out) :: iterations(*),converged(*)
    real(rk),allocatable :: zz(:),sh(:,:),di(:,:),be(:,:),ini(:),crit(:)
    integer(ik),allocatable :: it(:)
    logical,allocatable :: conv(:)
    complex(rk),allocatable :: modes(:,:)
    integer :: i,j,idx,ndof
    integer(ik) :: st

    rd_critical_speeds_full_legacy=RD_ERR_INPUT
    if (nnode<=0 .or. ncrit<=0) return
    ndof=4*nnode
    call unpack_model_arrays(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,zz,sh,di,be)
    allocate(ini(ncrit),crit(ncrit),it(ncrit),conv(ncrit),modes(ndof,ncrit))
    do i=1,ncrit; ini(i)=initial(i); end do
    call critical_speeds_stationary(nnode,zz,nshaft,sh,ndisc,di,nbear,be,method,nx,damped,ncrit, &
      max_iterations,tol,ini,crit,it,conv,st,modes)
    if (st/=RD_OK) then; rd_critical_speeds_full_legacy=st; return; end if
    do i=1,ncrit
      critical(i)=crit(i); iterations(i)=it(i); converged(i)=merge(1_c_int,0_c_int,conv(i))
    end do
    idx=0
    do j=1,ncrit
      do i=1,ndof
        idx=idx+1; mr(idx)=real(modes(i,j),rk); mi(idx)=aimag(modes(i,j))
      end do
    end do
    rd_critical_speeds_full_legacy=RD_OK
  end function rd_critical_speeds_full_legacy

  subroutine reduce_stationary_matrices(ndof,nc,keep,M,C0,C1,K0,K1,Mb,Cb,Kb,speed,Mc,Cc,Kc)
    integer,intent(in) :: ndof,nc,keep(nc)
    real(rk),intent(in) :: M(ndof,ndof),C0(ndof,ndof),C1(ndof,ndof),K0(ndof,ndof),K1(ndof,ndof)
    real(rk),intent(in) :: Mb(ndof,ndof),Cb(ndof,ndof),Kb(ndof,ndof),speed
    real(rk),intent(out) :: Mc(nc,nc),Cc(nc,nc),Kc(nc,nc)
    integer :: i,j
    do j=1,nc
      do i=1,nc
        Mc(i,j)=M(keep(i),keep(j))+Mb(keep(i),keep(j))
        Cc(i,j)=C0(keep(i),keep(j))+Cb(keep(i),keep(j))+speed*C1(keep(i),keep(j))
        Kc(i,j)=K0(keep(i),keep(j))+Kb(keep(i),keep(j))+speed*K1(keep(i),keep(j))
      end do
    end do
  end subroutine reduce_stationary_matrices

  subroutine unpack_model_arrays(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,zz,sh,di,be)
    integer,intent(in) :: nnode,nshaft,ndisc,nbear
    real(c_double),intent(in) :: z(*),shaft(*),disc(*),bear(*)
    real(rk),allocatable,intent(out) :: zz(:),sh(:,:),di(:,:),be(:,:)
    integer :: i,j
    allocate(zz(nnode),sh(11,nshaft),di(6,ndisc),be(34,nbear))
    do i=1,nnode; zz(i)=z(i); end do
    do j=1,nshaft; do i=1,11; sh(i,j)=shaft((j-1)*11+i); end do; end do
    do j=1,ndisc; do i=1,6; di(i,j)=disc((j-1)*6+i); end do; end do
    do j=1,nbear; do i=1,34; be(i,j)=bear((j-1)*34+i); end do; end do
  end subroutine unpack_model_arrays
end module rd_c_api
