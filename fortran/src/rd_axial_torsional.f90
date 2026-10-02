! SPDX-License-Identifier: Apache-2.0
! B3 dedicated axial/torsional modal kernels.
! Consumes the qualified B2 6-DOF global matrices and solves only invariant
! z/theta subspaces. No lateral, fault, forced-response or transient physics.
module rd_axial_torsional
  use iso_c_binding, only: c_double,c_int
  use, intrinsic :: ieee_arithmetic, only: ieee_is_finite
  use rd_lapack, only: generalized_eig_real
  use rd_status, only: RD_OK
  implicit none(type,external)
  private
  integer,parameter::dp=c_double
  real(dp),parameter::RIGID_CUTOFF=1.0e-1_dp
  integer(c_int),parameter,public::B3_OK=0_c_int
  integer(c_int),parameter,public::B3_INVALID_INPUT=40_c_int
  integer(c_int),parameter,public::B3_UNSUPPORTED=41_c_int
  integer(c_int),parameter,public::B3_LAPACK=42_c_int
  integer(c_int),parameter,public::B3_NONFINITE=43_c_int
  integer(c_int),parameter,public::B3_MODE_COUNT=44_c_int
  public::family_modal_from_global,family_decoupling_ratio,extract_family_matrix
contains

  pure integer function family_offset(family) result(offset)
    integer(c_int),intent(in)::family
    select case(family)
    case(1_c_int);offset=3      ! z
    case(2_c_int);offset=6      ! theta
    case default;offset=0
    end select
  end function

  pure real(dp) function fro_norm(A) result(value)
    real(dp),intent(in)::A(:,:)
    value=sqrt(sum(A*A))
  end function

  pure real(dp) function family_decoupling_ratio(A,nn,family) result(value)
    integer(c_int),intent(in)::nn,family
    real(dp),intent(in)::A(6*nn,6*nn)
    integer::i,j,offset
    real(dp)::lr,rl,scale
    offset=family_offset(family)
    if(offset==0)then;value=huge(1._dp);return;end if
    lr=0._dp;rl=0._dp
    do i=1,nn
      do j=1,6*nn
        if(mod(j-1,6)+1/=offset)then
          lr=lr+A(6*(i-1)+offset,j)**2
          rl=rl+A(j,6*(i-1)+offset)**2
        end if
      end do
    end do
    scale=max(1._dp,fro_norm(A))
    value=(sqrt(lr)+sqrt(rl))/scale
  end function

  pure subroutine extract_family_matrix(A,nn,family,R,status)
    integer(c_int),intent(in)::nn,family
    real(dp),intent(in)::A(6*nn,6*nn)
    real(dp),intent(out)::R(nn,nn)
    integer(c_int),intent(out)::status
    integer::i,j,offset
    status=B3_INVALID_INPUT;R=0._dp
    offset=family_offset(family);if(offset==0)return
    do j=1,nn
      do i=1,nn
        R(i,j)=A(6*(i-1)+offset,6*(j-1)+offset)
      end do
    end do
    if(.not.all(ieee_is_finite(R)))then;status=B3_NONFINITE;return;end if
    status=B3_OK
  end subroutine

  subroutine sort_modes(lambda,source,count)
    real(dp),intent(in)::lambda(:)
    integer,intent(inout)::source(:)
    integer,intent(in)::count
    integer::i,j,key
    do i=1,count;source(i)=source(i);end do
    do i=2,count
      key=source(i);j=i-1
      do while(j>=1)
        if(lambda(source(j))<=lambda(key))exit
        source(j+1)=source(j);j=j-1
      end do
      source(j+1)=key
    end do
  end subroutine

  subroutine family_modal_from_global(nn,family,speed,M6,K6,C6,G6,S6, &
      M,K,C,G,Ksdt,wn,wd,zeta,logdec,q,residual,max_decouple,nmode,status)
    integer(c_int),intent(in)::nn,family
    real(dp),intent(in)::speed
    real(dp),intent(in)::M6(6*nn,6*nn),K6(6*nn,6*nn),C6(6*nn,6*nn),G6(6*nn,6*nn),S6(6*nn,6*nn)
    real(dp),intent(out)::M(nn,nn),K(nn,nn),C(nn,nn),G(nn,nn),Ksdt(nn,nn)
    real(dp),intent(out)::wn(max(1,nn-1)),wd(max(1,nn-1)),zeta(max(1,nn-1)),logdec(max(1,nn-1))
    real(dp),intent(out)::q(nn,max(1,nn-1)),residual(max(1,nn-1)),max_decouple
    integer(c_int),intent(out)::nmode,status
    real(dp),allocatable::Aw(:,:),Bw(:,:),ar(:),ai(:),beta(:),vr(:,:),lambda(:),R(:)
    integer,allocatable::keep(:)
    integer(c_int)::st
    integer::i,j,count,pivot,offset
    real(dp)::lam,normq,scale,nm,nk,nc,ratio(5)
    status=B3_INVALID_INPUT;nmode=0;max_decouple=0._dp
    M=0;K=0;C=0;G=0;Ksdt=0;wn=0;wd=0;zeta=0;logdec=0;q=0;residual=0
    if(nn<2.or..not.ieee_is_finite(speed))return
    offset=family_offset(family);if(offset==0)return
    if(.not.all(ieee_is_finite(M6)).or..not.all(ieee_is_finite(K6)).or. &
       .not.all(ieee_is_finite(C6)).or..not.all(ieee_is_finite(G6)).or. &
       .not.all(ieee_is_finite(S6)))return

    ratio=[family_decoupling_ratio(M6,nn,family),family_decoupling_ratio(K6,nn,family), &
           family_decoupling_ratio(C6,nn,family),family_decoupling_ratio(G6,nn,family), &
           family_decoupling_ratio(S6,nn,family)]
    max_decouple=maxval(ratio)
    if(max_decouple>1.0e-12_dp)then;status=B3_UNSUPPORTED;return;end if

    call extract_family_matrix(M6,nn,family,M,st);if(st/=B3_OK)then;status=st;return;end if
    call extract_family_matrix(K6,nn,family,K,st);if(st/=B3_OK)then;status=st;return;end if
    call extract_family_matrix(C6,nn,family,C,st);if(st/=B3_OK)then;status=st;return;end if
    call extract_family_matrix(G6,nn,family,G,st);if(st/=B3_OK)then;status=st;return;end if
    call extract_family_matrix(S6,nn,family,Ksdt,st);if(st/=B3_OK)then;status=st;return;end if

    ! Initial B3 authority is the undamped invariant axial/torsional subspace.
    ! Any future axial/torsional damping, gyro or dynamic-stiffness term requires
    ! a new authority stage rather than silent reduction.
    if(any(C/=0._dp).or.any(G/=0._dp).or.any(Ksdt/=0._dp))then
      status=B3_UNSUPPORTED;return
    end if

    allocate(Aw(nn,nn),Bw(nn,nn),ar(nn),ai(nn),beta(nn),vr(nn,nn),lambda(nn),keep(nn))
    Aw=K;Bw=M
    call generalized_eig_real(Aw,Bw,ar,ai,beta,vr,st)
    if(st/=RD_OK)then;status=B3_LAPACK;return;end if
    lambda=huge(1._dp);count=0
    do i=1,nn
      if(.not.ieee_is_finite(ar(i)).or..not.ieee_is_finite(ai(i)).or..not.ieee_is_finite(beta(i)))then
        status=B3_NONFINITE;return
      end if
      if(abs(beta(i))<=tiny(1._dp))cycle
      if(abs(ai(i)/beta(i))>1.0e-8_dp)then;status=B3_UNSUPPORTED;return;end if
      lam=ar(i)/beta(i);lambda(i)=lam
      if(lam>RIGID_CUTOFF**2)then
        count=count+1;keep(count)=i
      end if
    end do
    if(count/=nn-1)then;status=B3_MODE_COUNT;return;end if
    call sort_modes(lambda,keep,count)

    nm=fro_norm(M);nk=fro_norm(K);nc=fro_norm(C+speed*G)
    allocate(R(nn))
    do j=1,count
      i=keep(j);lam=lambda(i)
      wn(j)=sqrt(lam);wd(j)=wn(j);zeta(j)=0._dp;logdec(j)=0._dp
      q(:,j)=vr(:,i)
      normq=sqrt(sum(q(:,j)*q(:,j)))
      if(.not.ieee_is_finite(normq).or.normq<=tiny(1._dp))then;status=B3_NONFINITE;return;end if
      q(:,j)=q(:,j)/normq
      pivot=maxloc(abs(q(:,j)),dim=1)
      if(q(pivot,j)<0._dp)q(:,j)=-q(:,j)
      R=matmul(K,q(:,j))-lam*matmul(M,q(:,j))
      scale=(nk+abs(lam)*nm+wn(j)*nc)*sqrt(sum(q(:,j)*q(:,j)))
      residual(j)=merge(sqrt(sum(R*R))/scale,sqrt(sum(R*R)),scale>0._dp)
    end do
    nmode=int(count,c_int)
    if(.not.all(ieee_is_finite(wn(1:count))).or..not.all(ieee_is_finite(q(:,1:count))).or. &
       .not.all(ieee_is_finite(residual(1:count))))then;status=B3_NONFINITE;return;end if
    status=B3_OK
  end subroutine
end module rd_axial_torsional
