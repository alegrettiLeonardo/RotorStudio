module rd_external_response
  use rd_kinds, only: rk,ik
  use rd_status, only: RD_OK,RD_ERR_INPUT
  use rd_lapack, only: solve_complex
  implicit none(type, external)
  private
  public :: auxiliary_frequency_response, foundation_frequency_response
contains
  subroutine auxiliary_frequency_response(M,C,K,is_zero,force_def,nforce,omega,nfreq,direction,response,status)
    real(rk),intent(in)::M(:,:),C(:,:),K(:,:),force_def(5,nforce),omega(nfreq),direction
    logical,intent(in)::is_zero(:)
    integer(ik),intent(in)::nforce,nfreq
    complex(rk),intent(out)::response(size(M,1),nfreq)
    integer(ik),intent(out)::status
    integer::ndof,nc,i,j,ifreq,idx,iforce,node,ftype
    integer,allocatable::keep(:)
    complex(rk),allocatable::A(:,:),rhs(:,:),force(:)
    complex(rk)::q,jot
    ndof=size(M,1);response=(0._rk,0._rk);status=RD_OK;jot=(0._rk,1._rk)
    nc=count(.not.is_zero);allocate(keep(nc));idx=0
    do i=1,ndof;if(.not.is_zero(i))then;idx=idx+1;keep(idx)=i;endif;enddo
    iforce=0
    do i=1,nforce
      ftype=nint(force_def(1,i));if(ftype==6.or.ftype==7)then;iforce=i;exit;endif
    enddo
    if(iforce==0)then;status=RD_ERR_INPUT;return;endif
    node=nint(force_def(2,iforce));if(node<1.or.4*node>ndof)then;status=RD_ERR_INPUT;return;endif
    allocate(force(nc),A(nc,nc),rhs(nc,1));force=0
    if(nint(force_def(1,iforce))==6)then
      q=force_def(3,iforce)*cmplx(cos(force_def(4,iforce)),sin(force_def(4,iforce)),rk)
      call add_force(4*node-3,q)
      if(direction>0)then;call add_force(4*node-2,-jot*q);else;call add_force(4*node-2,jot*q);endif
    else
      call add_force(4*node-3,cmplx(force_def(3,iforce),0._rk,rk))
      call add_force(4*node-2,cmplx(force_def(4,iforce),0._rk,rk))
    endif
    do ifreq=1,nfreq
      do j=1,nc;do i=1,nc
        A(i,j)=cmplx(K(keep(i),keep(j))-omega(ifreq)**2*M(keep(i),keep(j)),omega(ifreq)*C(keep(i),keep(j)),rk)
      enddo;enddo
      if(nint(force_def(1,iforce))==6)then;rhs(:,1)=omega(ifreq)**2*force;else;rhs(:,1)=force;endif
      call solve_complex(A,rhs,status);if(status/=RD_OK)return
      do i=1,nc;response(keep(i),ifreq)=rhs(i,1);enddo
    enddo
  contains
    subroutine add_force(full,value)
      integer,intent(in)::full;complex(rk),intent(in)::value;integer::qidx
      do qidx=1,nc;if(keep(qidx)==full)then;force(qidx)=force(qidx)+value;return;endif;enddo
    end subroutine
  end subroutine

  subroutine foundation_frequency_response(M,C,K,Mb,Cb,Kb,is_zero,bear,nbear,force_def,nforce,omega,nfreq,response,status)
    real(rk),intent(in)::M(:,:),C(:,:),K(:,:),Mb(:,:),Cb(:,:),Kb(:,:),bear(34,nbear),force_def(5,nforce),omega(nfreq)
    logical,intent(in)::is_zero(:)
    integer(ik),intent(in)::nbear,nforce,nfreq
    complex(rk),intent(out)::response(size(M,1),nfreq)
    integer(ik),intent(out)::status
    integer::ndof,nc,i,j,ifreq,idx,iforce,node
    integer,allocatable::keep(:)
    real(rk),allocatable::qf(:),Mf(:),Cf(:),Kf(:)
    complex(rk),allocatable::A(:,:),rhs(:,:)
    complex(rk)::om
    ndof=size(M,1);response=(0._rk,0._rk);status=RD_OK
    iforce=0
    do i=1,nforce;if(nint(force_def(1,i))==4)then;iforce=i;exit;endif;enddo
    if(iforce==0.or.1+2*nbear>5)then;status=RD_ERR_INPUT;return;endif
    allocate(qf(ndof));qf=0
    do i=1,nbear
      node=nint(bear(2,i));if(node<1.or.4*node>ndof)then;status=RD_ERR_INPUT;return;endif
      ! Preserve V2 predicate (>2 | <9): true for every finite numeric bearing type.
      qf(4*node-3)=force_def(2*i,iforce);qf(4*node-2)=force_def(2*i+1,iforce)
    enddo
    nc=count(.not.is_zero);allocate(keep(nc));idx=0
    do i=1,ndof;if(.not.is_zero(i))then;idx=idx+1;keep(idx)=i;endif;enddo
    allocate(Mf(nc),Cf(nc),Kf(nc),A(nc,nc),rhs(nc,1))
    Mf=matmul(Mb(keep,:),qf);Cf=matmul(Cb(keep,:),qf);Kf=matmul(Kb(keep,:),qf)
    do ifreq=1,nfreq
      om=cmplx(0._rk,omega(ifreq),rk)
      do j=1,nc;do i=1,nc
        A(i,j)=cmplx(K(keep(i),keep(j)),0._rk,rk)+om*cmplx(C(keep(i),keep(j)),0._rk,rk)+om*om*cmplx(M(keep(i),keep(j)),0._rk,rk)
      enddo;enddo
      rhs(:,1)=om*om*cmplx(Mf,0._rk,rk)+om*cmplx(Cf,0._rk,rk)+cmplx(Kf,0._rk,rk)
      call solve_complex(A,rhs,status);if(status/=RD_OK)return
      do i=1,nc;response(keep(i),ifreq)=rhs(i,1);enddo
    enddo
  end subroutine
end module rd_external_response
