! SPDX-License-Identifier: Apache-2.0
! B2 dense constant-speed 6-DOF modal kernel. ROSS ordering/classification authority:
! petrobras/ross@6320eab9f890f1b3cc1710d508b446fe063ca68d.
module rd_6dof_modal
  use iso_c_binding, only: c_double,c_int
  use, intrinsic :: ieee_arithmetic, only: ieee_is_finite,ieee_value,ieee_quiet_nan
  use rd_lapack, only: solve_real,eig_real
  use rd_6dof_assembly, only: B2_OK,B2_INVALID_INPUT,B2_SINGULAR,B2_LAPACK,B2_NONFINITE
  implicit none(type,external)
  private
  integer,parameter::dp=c_double
  real(dp),parameter::RIGID_CUTOFF=1.0e-1_dp,MODE_DOF_THRESHOLD=8.0e-2_dp,MODE_FRACTION=9.0e-1_dp
  public :: modal_from_matrices,build_state_space,classify_mode,whirl_value
  interface
    subroutine dgetrf(m,n,a,lda,ipiv,info)
      import dp
      integer::m,n,lda,ipiv(*),info
      real(dp)::a(lda,*)
    end subroutine
    subroutine dgecon(norm,n,a,lda,anorm,rcond,work,iwork,info)
      import dp
      character::norm
      integer::n,lda,iwork(*),info
      real(dp)::a(lda,*),anorm,rcond,work(*)
    end subroutine
  end interface
contains
  pure real(dp) function round10(x)
    real(dp),intent(in)::x
    if(abs(x)<1.0e290_dp)then
      round10=anint(x*1.0e10_dp)/1.0e10_dp
    else
      round10=x
    end if
  end function

  pure integer function sort_sign(z)
    complex(dp),intent(in)::z
    real(dp)::w
    w=round10(aimag(z))
    if(w>0._dp)then;sort_sign=0
    elseif(w==0._dp)then;sort_sign=1
    else;sort_sign=2
    end if
  end function

  pure logical function comes_after(a,b)
    complex(dp),intent(in)::a,b
    integer::sa,sb
    real(dp)::ia,ib,na,nb
    sa=sort_sign(a);sb=sort_sign(b)
    ia=round10(aimag(a));ib=round10(aimag(b))
    na=abs(cmplx(round10(real(a,dp)),ia,kind=dp))
    nb=abs(cmplx(round10(real(b,dp)),ib,kind=dp))
    if(sa/=sb)then;comes_after=sa>sb
    elseif(ia/=ib)then;comes_after=ia>ib
    else;comes_after=na>nb
    end if
  end function

  subroutine sorted_indices(values,idx)
    complex(dp),intent(in)::values(:)
    integer,intent(out)::idx(size(values))
    integer::i,j,key
    do i=1,size(values);idx(i)=i;end do
    do i=2,size(values)
      key=idx(i);j=i-1
      do while(j>=1)
        if(.not.comes_after(values(idx(j)),values(key)))exit
        idx(j+1)=idx(j);j=j-1
      end do
      idx(j+1)=key
    end do
  end subroutine

  subroutine estimate_rcond(M,rcond,status)
    real(dp),intent(in)::M(:,:)
    real(dp),intent(out)::rcond
    integer(c_int),intent(out)::status
    real(dp),allocatable::A(:,:),work(:)
    integer,allocatable::ipiv(:),iwork(:)
    integer::n,info
    real(dp)::anorm
    status=B2_INVALID_INPUT;rcond=0._dp
    n=size(M,1);if(n<1.or.size(M,2)/=n)return
    anorm=maxval(sum(abs(M),dim=1));if(.not.ieee_is_finite(anorm).or.anorm<=0)return
    allocate(A(n,n),work(4*n),ipiv(n),iwork(n));A=M
    call dgetrf(n,n,A,n,ipiv,info)
    if(info/=0)then;status=B2_SINGULAR;return;end if
    call dgecon('1',n,A,n,anorm,rcond,work,iwork,info)
    if(info/=0.or..not.ieee_is_finite(rcond))then;status=B2_LAPACK;return;end if
    if(rcond<1.0e-14_dp)then;status=B2_SINGULAR;return;end if
    status=B2_OK
  end subroutine

  subroutine build_state_space(M,K,C,G,speed,A,rcond,status)
    real(dp),intent(in)::M(:,:),K(:,:),C(:,:),G(:,:),speed
    real(dp),intent(out)::A(2*size(M,1),2*size(M,1)),rcond
    integer(c_int),intent(out)::status
    real(dp),allocatable::Mc(:,:),X(:,:),Y(:,:),RX(:,:),RY(:,:)
    integer::n,i
    integer(c_int)::st
    status=B2_INVALID_INPUT;A=0._dp;rcond=0._dp
    n=size(M,1)
    if(n<1.or.size(M,2)/=n.or.any(shape(K)/=[n,n]).or.any(shape(C)/=[n,n]).or.any(shape(G)/=[n,n]))return
    if(.not.ieee_is_finite(speed).or..not.all(ieee_is_finite(M)).or..not.all(ieee_is_finite(K)).or. &
       .not.all(ieee_is_finite(C)).or..not.all(ieee_is_finite(G)))return
    call estimate_rcond(M,rcond,st);if(st/=B2_OK)then;status=st;return;end if
    allocate(Mc(n,n),X(n,n),Y(n,n),RX(n,n),RY(n,n))
    ! Preserve the frozen ROSS formulation literally:
    ! A21 = solve(-M, K) and A22 = solve(-M, C + speed*G).
    X=K;Mc=-M;call solve_real(Mc,X,st);if(st/=0)then;status=B2_LAPACK;return;end if
    Y=C+speed*G;Mc=-M;call solve_real(Mc,Y,st);if(st/=0)then;status=B2_LAPACK;return;end if
    ! One DGESV iterative-refinement correction suppresses platform-dependent
    ! cancellation noise without changing the frozen solver contract or
    ! forming an explicit inverse.  The correction solves A*dX=(B-A*X).
    RX=K-matmul(-M,X)
    Mc=-M;call solve_real(Mc,RX,st);if(st/=0)then;status=B2_LAPACK;return;end if
    X=X+RX
    RY=(C+speed*G)-matmul(-M,Y)
    Mc=-M;call solve_real(Mc,RY,st);if(st/=0)then;status=B2_LAPACK;return;end if
    Y=Y+RY
    do i=1,n;A(i,n+i)=1._dp;end do
    A(n+1:2*n,1:n)=X;A(n+1:2*n,n+1:2*n)=Y
    if(.not.all(ieee_is_finite(A)))then;status=B2_NONFINITE;return;end if
    status=B2_OK
  end subroutine

  subroutine reconstruct_vectors(wi,vr,V)
    real(dp),intent(in)::wi(:),vr(:,:)
    complex(dp),intent(out)::V(size(vr,1),size(vr,2))
    integer::j,n
    n=size(wi);V=cmplx(0._dp,0._dp,kind=dp);j=1
    do while(j<=n)
      if(wi(j)>0._dp .and. j<n)then
        V(:,j)=cmplx(vr(:,j),vr(:,j+1),kind=dp)
        V(:,j+1)=conjg(V(:,j));j=j+2
      elseif(wi(j)<0._dp)then
        if(j==1.or.wi(j-1)<=0._dp)V(:,j)=cmplx(vr(:,j),0._dp,kind=dp)
        j=j+1
      else
        V(:,j)=cmplx(vr(:,j),0._dp,kind=dp);j=j+1
      end if
    end do
  end subroutine

  integer(c_int) function classify_mode(q,nn) result(kind)
    complex(dp),intent(in)::q(6*nn)
    integer(c_int),intent(in)::nn
    real(dp)::normv
    integer::counts(6),i,d,total
    counts=0;kind=1_c_int
    normv=sqrt(sum(abs(q)**2));if(normv<=tiny(1._dp))return
    do i=1,6*nn
      if(abs(q(i))/normv>MODE_DOF_THRESHOLD)then
        d=mod(i-1,6)+1;counts(d)=counts(d)+1
      end if
    end do
    total=sum(counts);if(total<=0)return
    if(real(counts(3),dp)/real(total,dp)>MODE_FRACTION)then
      kind=2_c_int
    elseif(real(counts(6),dp)/real(total,dp)>MODE_FRACTION)then
      kind=3_c_int
    end if
  end function

  real(dp) function whirl_value(q,nn,kind) result(value)
    complex(dp),intent(in)::q(6*nn)
    integer(c_int),intent(in)::nn,kind
    integer::n,nf,nb,ix,iy
    real(dp)::ru,rv,nu,nv,diff,h11,h22,h12,disc,lmin,lmax,minor,major,kappa,pi
    value=ieee_value(0._dp,ieee_quiet_nan);if(kind/=1_c_int)return
    nf=0;nb=0;pi=acos(-1._dp)
    do n=1,nn
      ix=6*(n-1)+1;iy=ix+1
      ru=abs(q(ix));rv=abs(q(iy));nu=atan2(aimag(q(ix)),real(q(ix),dp));nv=atan2(aimag(q(iy)),real(q(iy),dp))
      h11=ru*ru;h22=rv*rv;h12=ru*rv*cos(nu-nv)
      disc=sqrt(max((h11-h22)**2+4*h12*h12,0._dp))
      lmin=max((h11+h22-disc)/2,0._dp);lmax=max((h11+h22+disc)/2,0._dp)
      minor=sqrt(lmin);major=sqrt(lmax);diff=nv-nu
      if(diff < -pi)diff=diff+2*pi
      if(diff > pi)diff=diff-2*pi
      kappa=0._dp
      if(major>tiny(1._dp).and.minor>epsilon(1._dp)*major)then
        if(diff>0._dp.and.diff<pi)then;kappa=-minor/major
        else;kappa=minor/major
        end if
      end if
      if(kappa>0._dp)then;nf=nf+1
      else;nb=nb+1
      end if
    end do
    if(nf==nn)then;value=0._dp
    elseif(nb==nn)then;value=1._dp
    else;value=0.5_dp
    end if
  end function

  subroutine modal_from_matrices(M,K,C,G,speed,num_modes,eall,Vall,nret,evals,qvec,wn,wd,zeta,logdec,mode_type,whirl,residual,nsel,rcond,status)
    real(dp),intent(in)::M(:,:),K(:,:),C(:,:),G(:,:),speed
    integer(c_int),intent(in)::num_modes
    complex(dp),allocatable,intent(out)::eall(:),Vall(:,:),evals(:),qvec(:,:)
    real(dp),allocatable,intent(out)::wn(:),wd(:),zeta(:),logdec(:),whirl(:),residual(:)
    integer(c_int),allocatable,intent(out)::mode_type(:)
    integer(c_int),intent(out)::nret,nsel,status
    real(dp),intent(out)::rcond
    real(dp),allocatable::A(:,:),Aw(:,:),wr(:),wi(:),vr(:,:)
    complex(dp),allocatable::Vraw(:,:),etmp(:),Vtmp(:,:)
    integer,allocatable::keep(:),idx(:)
    integer::n,state,i,j,nk
    integer(c_int)::st
    real(dp)::den,nm,nc,nkmat,qnorm
    complex(dp),allocatable::R(:)
    status=B2_INVALID_INPUT;nret=0;nsel=0;rcond=0._dp
    n=size(M,1);if(n<1.or.mod(num_modes,2_c_int)/=0.or.num_modes<2)return
    state=2*n;allocate(A(state,state),Aw(state,state),wr(state),wi(state),vr(state,state),Vraw(state,state))
    call build_state_space(M,K,C,G,speed,A,rcond,st);if(st/=B2_OK)then;status=st;return;end if
    Aw=A;call eig_real(Aw,wr,wi,vr,st);if(st/=0)then;status=B2_LAPACK;return;end if
    call reconstruct_vectors(wi,vr,Vraw)
    allocate(keep(state));nk=0
    do i=1,state
      if(abs(cmplx(wr(i),wi(i),kind=dp))>RIGID_CUTOFF)then;nk=nk+1;keep(nk)=i;end if
    end do
    if(nk<1)then;status=B2_SINGULAR;return;end if
    allocate(etmp(nk),Vtmp(state,nk),idx(nk))
    do i=1,nk;etmp(i)=cmplx(wr(keep(i)),wi(keep(i)),kind=dp);Vtmp(:,i)=Vraw(:,keep(i));end do
    call sorted_indices(etmp,idx)
    allocate(eall(nk),Vall(state,nk))
    do i=1,nk;eall(i)=etmp(idx(i));Vall(:,i)=Vtmp(:,idx(i));end do
    nret=nk;nsel=min(int(num_modes/2,c_int),nret)
    allocate(evals(nsel),qvec(n,nsel),wn(nsel),wd(nsel),zeta(nsel),logdec(nsel),mode_type(nsel),whirl(nsel),residual(nsel),R(n))
    nm=sqrt(sum(M*M));nc=sqrt(sum((C+speed*G)**2));nkmat=sqrt(sum(K*K))
    do j=1,nsel
      evals(j)=eall(j);qvec(:,j)=Vall(1:n,j)
      wn(j)=abs(evals(j));wd(j)=aimag(evals(j))
      if(wn(j)>0)then;zeta(j)=-real(evals(j),dp)/wn(j)
      else;zeta(j)=0._dp
      end if
      if(1._dp-zeta(j)**2>0._dp)then
        logdec(j)=2*acos(-1._dp)*zeta(j)/sqrt(1._dp-zeta(j)**2)
      else
        logdec(j)=ieee_value(0._dp,ieee_quiet_nan)
      end if
      mode_type(j)=classify_mode(qvec(:,j),int(n/6,c_int));whirl(j)=whirl_value(qvec(:,j),int(n/6,c_int),mode_type(j))
      R=(evals(j)**2)*matmul(M,qvec(:,j))+evals(j)*matmul(C+speed*G,qvec(:,j))+matmul(K,qvec(:,j))
      qnorm=sqrt(sum(abs(qvec(:,j))**2))
      den=abs(evals(j))**2*nm*qnorm+abs(evals(j))*nc*qnorm+nkmat*qnorm
      residual(j)=merge(sqrt(sum(abs(R)**2))/den,sqrt(sum(abs(R)**2)),den>0._dp)
    end do
    if(.not.all(ieee_is_finite(wn)).or..not.all(ieee_is_finite(wd)).or..not.all(ieee_is_finite(zeta)).or. &
       .not.all(ieee_is_finite(residual)))then;status=B2_NONFINITE;return;end if
    status=B2_OK
  end subroutine
end module rd_6dof_modal
