module rd_critical_speed
  use rd_kinds, only: rk, ik
  use rd_status, only: RD_OK, RD_ERR_INPUT
  use rd_assembly_stationary, only: assemble_rotor
  use rd_bearings, only: assemble_bearings
  use rd_eigensystem, only: stationary_eigs, stationary_eigensystem
  use rd_lapack, only: solve_complex, eig_complex
  implicit none(type, external)
  private
  public :: critical_speeds_stationary
contains
  subroutine critical_speeds_stationary(nnode,z,nshaft,shaft,ndisc,disc,nbear,bear,method_in, &
      NX_in,damped,ncrit,max_iterations,tol,initial_estimates,critical,iterations,converged,status,mode_shapes)
    integer(ik),intent(in) :: nnode,nshaft,ndisc,nbear,method_in,damped,ncrit,max_iterations
    real(rk),intent(in) :: z(nnode),shaft(11,nshaft),disc(6,ndisc),bear(34,nbear)
    real(rk),intent(in) :: NX_in,tol,initial_estimates(ncrit)
    real(rk),intent(out) :: critical(ncrit)
    integer(ik),intent(out) :: iterations(ncrit)
    logical,intent(out) :: converged(ncrit)
    integer(ik),intent(out) :: status
    complex(rk),intent(out),optional :: mode_shapes(:,:)
    integer :: ndof,nc,method,i,j,ic,ieig,idx,btype,ib
    integer,allocatable :: keep(:)
    logical,allocatable :: is_zero(:)
    logical :: constant_bearings
    real(rk),allocatable :: M0(:,:),C0(:,:),C1(:,:),K0(:,:),K1(:,:),Mb(:,:),Cb(:,:),Kb(:,:),ecc(:)
    real(rk),allocatable :: Mc(:,:),Cc(:,:),Kc(:,:),wr(:),wi(:)
    complex(rk),allocatable :: DMM(:,:),DCC(:,:),DKK(:,:),XK(:,:),XC(:,:),AA(:,:),w(:),vr(:,:),u(:,:)
    real(rk),allocatable :: est(:)
    real(rk) :: NX,omega,old,rel_change,best_delta
    integer :: best_index
    integer(ik) :: st

    critical=0._rk; iterations=0_ik; converged=.false.; status=RD_OK
    if (present(mode_shapes)) mode_shapes=(0._rk,0._rk)
    if (nnode<=0 .or. ncrit<=0 .or. max_iterations<=0 .or. tol<=0._rk) then
      status=RD_ERR_INPUT; return
    end if
    NX=max(abs(NX_in),0.2_rk)
    ndof=4*nnode
    if (present(mode_shapes)) then
      if (size(mode_shapes,1)<ndof .or. size(mode_shapes,2)<ncrit) then
        status=RD_ERR_INPUT; return
      end if
    end if
    allocate(M0(ndof,ndof),C0(ndof,ndof),C1(ndof,ndof),K0(ndof,ndof),K1(ndof,ndof))
    allocate(Mb(ndof,ndof),Cb(ndof,ndof),Kb(ndof,ndof),is_zero(ndof),ecc(nbear))
    call assemble_rotor(nnode,z,nshaft,shaft,ndisc,disc,M0,C0,C1,K0,K1,st)
    if (st/=RD_OK) then; status=st; return; end if

    constant_bearings=.true.
    do ib=1,nbear
      btype=nint(bear(1,ib))
      if (btype==7 .or. btype==8) constant_bearings=.false.
    end do
    method=method_in
    if (method==0) then
      if (constant_bearings) then; method=1; else; method=2; end if
    end if
    if (method<1 .or. method>3) then; status=RD_ERR_INPUT; return; end if
    if (method==1 .and. .not.constant_bearings) then; status=RD_ERR_INPUT; return; end if

    if (method==1) then
      call assemble_bearings(nnode,nbear,bear,0._rk,Mb,Cb,Kb,is_zero,ecc,st)
    else
      call assemble_bearings(nnode,nbear,bear,2._rk*acos(-1._rk)*500._rk/60._rk,Mb,Cb,Kb,is_zero,ecc,st)
    end if
    if (st/=RD_OK) then; status=st; return; end if
    nc=count(.not.is_zero)
    if (nc<=0 .or. ncrit>nc) then; status=RD_ERR_INPUT; return; end if
    allocate(keep(nc)); idx=0
    do i=1,ndof
      if (.not.is_zero(i)) then; idx=idx+1; keep(idx)=i; end if
    end do

    if (method==1) then
      allocate(DMM(nc,nc),DCC(nc,nc),DKK(nc,nc),XK(nc,nc),XC(nc,nc),AA(2*nc,2*nc),w(2*nc),vr(2*nc,2*nc))
      do j=1,nc
        do i=1,nc
          DMM(i,j)=cmplx(-NX*NX*(M0(keep(i),keep(j))+Mb(keep(i),keep(j))), &
                        NX*C1(keep(i),keep(j)),rk)
          DCC(i,j)=cmplx(K1(keep(i),keep(j)),NX*(C0(keep(i),keep(j))+Cb(keep(i),keep(j))),rk)
          DKK(i,j)=cmplx(K0(keep(i),keep(j))+Kb(keep(i),keep(j)),0._rk,rk)
        end do
      end do
      XK=DMM; XC=DMM
      call solve_complex(XK,DKK,st)
      if (st/=RD_OK) then; status=st; return; end if
      call solve_complex(XC,DCC,st)
      if (st/=RD_OK) then; status=st; return; end if
      AA=(0._rk,0._rk)
      do i=1,nc; AA(i,nc+i)=cmplx(1._rk,0._rk,rk); end do
      AA(nc+1:2*nc,1:nc)=-DKK
      AA(nc+1:2*nc,nc+1:2*nc)=-DCC
      call eig_complex(AA,w,vr,st)
      if (st/=RD_OK) then; status=st; return; end if
      call matlab_sort_complex_with_vectors(w,vr)
      do ic=1,ncrit
        ieig=2*ic-1
        if (damped/=0) then
          critical(ic)=abs(real(w(ieig),rk))
        else
          critical(ic)=abs(w(ieig))
        end if
        iterations(ic)=1_ik; converged(ic)=.true.
        if (present(mode_shapes)) then
          do i=1,nc
            mode_shapes(keep(i),ic)=vr(i,ieig)
          end do
        end if
      end do
      return
    end if

    allocate(Mc(nc,nc),Cc(nc,nc),Kc(nc,nc),wr(2*nc),wi(2*nc),est(2*nc))
    if (method==2) then
      omega=2._rk*acos(-1._rk)*500._rk/60._rk
      call reduced_matrices_at_speed(omega,Mc,Cc,Kc,st)
      if (st/=RD_OK) then; status=st; return; end if
      call stationary_eigs(Mc,Cc,Kc,wr,wi,st)
      if (st/=RD_OK) then; status=st; return; end if
    end if

    do ic=1,ncrit
      if (method==2) then
        ieig=2*ic-1
        if (damped/=0) then
          omega=abs(wi(ieig))/NX
        else
          omega=hypot(wr(ieig),wi(ieig))/NX
        end if
      else
        omega=abs(initial_estimates(ic))
      end if
      rel_change=1._rk
      do while (rel_change>tol .and. iterations(ic)<max_iterations)
        call reduced_matrices_at_speed(omega,Mc,Cc,Kc,st)
        if (st/=RD_OK) then; status=st; return; end if
        call stationary_eigs(Mc,Cc,Kc,wr,wi,st)
        if (st/=RD_OK) then; status=st; return; end if
        old=omega
        if (damped/=0) then
          est=abs(wi)/NX
        else
          do i=1,2*nc; est(i)=hypot(wr(i),wi(i))/NX; end do
        end if
        if (method==2) then
          omega=est(2*ic-1)
        else
          best_index=1; best_delta=abs(est(1)-initial_estimates(ic))
          do i=2,2*nc
            if (abs(est(i)-initial_estimates(ic))<best_delta) then
              best_delta=abs(est(i)-initial_estimates(ic)); best_index=i
            end if
          end do
          omega=est(best_index)
        end if
        if (old==0._rk) then
          rel_change=2._rk*tol
        else
          rel_change=abs((omega-old)/old)
        end if
        iterations(ic)=iterations(ic)+1_ik
      end do
      critical(ic)=omega
      converged(ic)=rel_change<=tol
    end do

    if (present(mode_shapes)) then
      allocate(w(2*nc),u(nc,2*nc))
      do ic=1,ncrit
        call reduced_matrices_at_speed(critical(ic),Mc,Cc,Kc,st)
        if (st/=RD_OK) then; status=st; return; end if
        call stationary_eigensystem(Mc,Cc,Kc,w,u,st)
        if (st/=RD_OK) then; status=st; return; end if
        if (method==2) then
          best_index=2*ic-1
        else
          if (damped/=0) then
            do i=1,2*nc; est(i)=abs(aimag(w(i)))/NX; end do
          else
            do i=1,2*nc; est(i)=abs(w(i))/NX; end do
          end if
          best_index=1; best_delta=abs(est(1)-critical(ic))
          do i=2,2*nc
            if (abs(est(i)-critical(ic))<best_delta) then
              best_delta=abs(est(i)-critical(ic)); best_index=i
            end if
          end do
        end if
        do i=1,nc
          mode_shapes(keep(i),ic)=u(i,best_index)
        end do
      end do
    end if
  contains
    subroutine reduced_matrices_at_speed(spd,Mout,Cout,Kout,stout)
      real(rk),intent(in) :: spd
      real(rk),intent(out) :: Mout(nc,nc),Cout(nc,nc),Kout(nc,nc)
      integer(ik),intent(out) :: stout
      integer :: ii,jj
      call assemble_bearings(nnode,nbear,bear,spd,Mb,Cb,Kb,is_zero,ecc,stout)
      if (stout/=RD_OK) return
      do jj=1,nc
        do ii=1,nc
          Mout(ii,jj)=M0(keep(ii),keep(jj))+Mb(keep(ii),keep(jj))
          Cout(ii,jj)=C0(keep(ii),keep(jj))+Cb(keep(ii),keep(jj))+spd*C1(keep(ii),keep(jj))
          Kout(ii,jj)=K0(keep(ii),keep(jj))+Kb(keep(ii),keep(jj))+spd*K1(keep(ii),keep(jj))
        end do
      end do
    end subroutine reduced_matrices_at_speed
  end subroutine critical_speeds_stationary

  subroutine matlab_sort_complex_with_vectors(w,v)
    complex(rk),intent(inout) :: w(:),v(:,:)
    integer :: i,j
    complex(rk) :: tmp
    complex(rk),allocatable :: col(:)
    real(rk) :: mi,mj,ai,aj
    allocate(col(size(v,1)))
    do i=1,size(w)-1
      do j=i+1,size(w)
        mi=abs(w(i)); mj=abs(w(j)); ai=atan2(aimag(w(i)),real(w(i),rk)); aj=atan2(aimag(w(j)),real(w(j),rk))
        if (mj<mi .or. (abs(mj-mi)<=epsilon(1._rk)*max(1._rk,mi) .and. aj<ai)) then
          tmp=w(i); w(i)=w(j); w(j)=tmp
          col=v(:,i); v(:,i)=v(:,j); v(:,j)=col
        end if
      end do
    end do
  end subroutine matlab_sort_complex_with_vectors
end module rd_critical_speed
