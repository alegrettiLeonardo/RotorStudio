module rd_critical_speed
 use rd_kinds,only:rk,ik
 use rd_status,only:RD_OK,RD_ERR_INPUT
 use rd_lapack,only:solve_complex,eig_complex
 use rd_eigensystem,only:stationary_eigs
 use rd_assembly_stationary,only:assemble_bearings
 implicit none(type,external);private
 public::critical_speeds,critical_speeds_ex
contains
 subroutine critical_speeds(nnode,nbear,bear,M0,C0,C1,K0,K1,NX,damped,ncrit,maxiter,tol,crit,status)
  integer(ik),intent(in)::nnode,nbear,ncrit,maxiter;real(rk),intent(in)::bear(34,nbear),M0(:,:),C0(:,:),C1(:,:),K0(:,:),K1(:,:),NX,tol
  logical,intent(in)::damped;real(rk),intent(out)::crit(ncrit);integer(ik),intent(out)::status
  integer(ik),allocatable::iterations(:);logical,allocatable::converged(:);real(rk),allocatable::initial(:)
  integer(ik)::method
  integer::i
  method=1
  do i=1,nbear;if(nint(bear(1,i))==7.or.nint(bear(1,i))==8)method=2;enddo
  allocate(iterations(ncrit),converged(ncrit),initial(1));initial=0
  call critical_speeds_ex(nnode,nbear,bear,M0,C0,C1,K0,K1,NX,damped,ncrit,maxiter,tol,method,initial,0_ik,crit,iterations,converged,status)
 end subroutine

 subroutine critical_speeds_ex(nnode,nbear,bear,M0,C0,C1,K0,K1,NX_in,damped,ncrit,maxiter,tol,method,initial,ninitial,crit,iterations,converged,status)
  integer(ik),intent(in)::nnode,nbear,ncrit,maxiter,method,ninitial
  real(rk),intent(in)::bear(34,nbear),M0(:,:),C0(:,:),C1(:,:),K0(:,:),K1(:,:),NX_in,tol,initial(*)
  logical,intent(in)::damped
  real(rk),intent(out)::crit(ncrit);integer(ik),intent(out)::iterations(ncrit);logical,intent(out)::converged(ncrit);integer(ik),intent(out)::status
  integer::i,ic,ieig,ndof,nc,idx,iter,idxc;logical::speed_dep;logical,allocatable::iz(:);integer,allocatable::keep(:)
  real(rk),allocatable::Mb(:,:),Cb(:,:),Kb(:,:),M(:,:),C(:,:),K(:,:),wr(:),wi(:),est(:)
  real(rk)::NX,ci,old,rel,guess,best,delta
  ndof=4*nnode;crit=0;iterations=0;converged=.false.;status=RD_OK;NX=max(abs(NX_in),.2_rk);speed_dep=.false.
  do i=1,nbear;if(nint(bear(1,i))==7.or.nint(bear(1,i))==8)speed_dep=.true.;enddo
  if(method<1.or.method>3)then;status=RD_ERR_INPUT;return;endif
  if(method==1.and.speed_dep)then;status=RD_ERR_INPUT;return;endif
  if(method==3.and.ninitial<ncrit)then;status=RD_ERR_INPUT;return;endif
  allocate(Mb(ndof,ndof),Cb(ndof,ndof),Kb(ndof,ndof),iz(ndof))
  if(method==1)then
    call assemble_bearings(nnode,nbear,bear,0._rk,Mb,Cb,Kb,iz,status);if(status/=RD_OK)return
    call direct_method(M0+Mb,C0+Cb,C1,K0+Kb,K1,iz,NX,damped,ncrit,crit,status)
    converged=(status==RD_OK);iterations=0;return
  endif
  guess=2*acos(-1._rk)*500/60
  call assemble_bearings(nnode,nbear,bear,guess,Mb,Cb,Kb,iz,status);if(status/=RD_OK)return
  nc=count(.not.iz);if(ncrit>nc)then;status=RD_ERR_INPUT;return;endif;allocate(keep(nc));idx=0
  do i=1,ndof;if(.not.iz(i))then;idx=idx+1;keep(idx)=i;endif;enddo
  allocate(M(nc,nc),C(nc,nc),K(nc,nc),wr(2*nc),wi(2*nc),est(2*nc))
  if(method==2)then
    M=M0(keep,keep)+Mb(keep,keep);C=C0(keep,keep)+Cb(keep,keep)+guess*C1(keep,keep);K=K0(keep,keep)+Kb(keep,keep)+guess*K1(keep,keep)
    call stationary_eigs(M,C,K,wr,wi,status);if(status/=RD_OK)return
  endif
  do ic=1,ncrit
    if(method==2)then
      ieig=2*ic-1
      if(damped)then;ci=abs(wi(ieig))/NX;else;ci=hypot(wr(ieig),wi(ieig))/NX;endif
    else
      ci=abs(initial(ic))
    endif
    rel=1;iter=0
    do while(rel>tol.and.iter<maxiter)
      call assemble_bearings(nnode,nbear,bear,ci,Mb,Cb,Kb,iz,status);if(status/=RD_OK)return
      M=M0(keep,keep)+Mb(keep,keep);C=C0(keep,keep)+Cb(keep,keep)+ci*C1(keep,keep);K=K0(keep,keep)+Kb(keep,keep)+ci*K1(keep,keep)
      call stationary_eigs(M,C,K,wr,wi,status);if(status/=RD_OK)return;old=ci
      if(method==2)then
        ieig=2*ic-1
        if(damped)then;ci=abs(wi(ieig))/NX;else;ci=hypot(wr(ieig),wi(ieig))/NX;endif
      else
        if(damped)then;est=abs(wi)/NX;else;est=hypot(wr,wi)/NX;endif
        best=huge(1._rk);idxc=1
        do i=1,2*nc
          delta=abs(est(i)-initial(ic))
          if(delta<best)then;best=delta;idxc=i;endif
        enddo
        ci=est(idxc)
      endif
      if(old==0)then;rel=2*tol;else;rel=abs((ci-old)/old);endif;iter=iter+1
    enddo
    crit(ic)=ci;iterations(ic)=iter;converged(ic)=rel<=tol
  enddo
 end subroutine

 subroutine direct_method(M,C0,C1,K,K1,iz,NX,damped,ncrit,crit,status)
  real(rk),intent(in)::M(:,:),C0(:,:),C1(:,:),K(:,:),K1(:,:),NX;logical,intent(in)::iz(:),damped;integer,intent(in)::ncrit
  real(rk),intent(out)::crit(ncrit);integer(ik),intent(out)::status
  integer::ndof,nc,i,idx;integer,allocatable::keep(:);complex(rk),allocatable::MM(:,:),CC(:,:),KK(:,:),XK(:,:),XC(:,:),A(:,:),w(:),vr(:,:)
  ndof=size(M,1);nc=count(.not.iz);if(ncrit>nc)then;status=RD_ERR_INPUT;return;endif;allocate(keep(nc));idx=0
  do i=1,ndof;if(.not.iz(i))then;idx=idx+1;keep(idx)=i;endif;enddo
  allocate(MM(nc,nc),CC(nc,nc),KK(nc,nc),XK(nc,nc),XC(nc,nc),A(2*nc,2*nc),w(2*nc),vr(2*nc,2*nc))
  MM=cmplx(-NX**2*M(keep,keep),NX*C1(keep,keep),rk);CC=cmplx(K1(keep,keep),NX*C0(keep,keep),rk);KK=cmplx(K(keep,keep),0._rk,rk)
  XK=KK;XC=CC;call solve_complex(MM,XK,status);if(status/=RD_OK)return
  MM=cmplx(-NX**2*M(keep,keep),NX*C1(keep,keep),rk);call solve_complex(MM,XC,status);if(status/=RD_OK)return
  A=0;do i=1,nc;A(i,nc+i)=1;enddo;A(nc+1:2*nc,1:nc)=-XK;A(nc+1:2*nc,nc+1:2*nc)=-XC
  call eig_complex(A,w,vr,status);if(status/=RD_OK)return;call sort_complex(w)
  do i=1,ncrit;if(damped)then;crit(i)=abs(real(w(2*i-1),rk));else;crit(i)=abs(w(2*i-1));endif;enddo
 end subroutine

 subroutine sort_complex(w)
  complex(rk),intent(inout)::w(:);integer::i,j;complex(rk)::t;real(rk)::mi,mj,ai,aj
  do i=1,size(w)-1;do j=i+1,size(w);mi=abs(w(i));mj=abs(w(j));ai=atan2(aimag(w(i)),real(w(i),rk));aj=atan2(aimag(w(j)),real(w(j),rk))
    if(mj<mi.or.(abs(mj-mi)<=epsilon(1._rk)*max(1._rk,mi).and.aj<ai))then;t=w(i);w(i)=w(j);w(j)=t;endif
  enddo;enddo
 end subroutine
end module rd_critical_speed
