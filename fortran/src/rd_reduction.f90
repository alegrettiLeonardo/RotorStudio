module rd_reduction
  use rd_kinds, only: rk,ik
  use rd_status, only: RD_OK,RD_ERR_INPUT,RD_ERR_UNSUPPORTED,RD_ERR_LAPACK
  use rd_lapack, only: generalized_eig_real
  implicit none(type,external)
  private
  public :: modal_truncation
contains
  subroutine modal_truncation(M,K,nr_requested,Tr,eigvals,nr_used,max_frequency_hz,status)
    real(rk),intent(in)::M(:,:),K(:,:)
    integer(ik),intent(in)::nr_requested
    real(rk),allocatable,intent(out)::Tr(:,:),eigvals(:)
    integer(ik),intent(out)::nr_used,status
    real(rk),intent(out)::max_frequency_hz
    real(rk),allocatable::A(:,:),B(:,:),ar(:),ai(:),beta(:),VR(:,:),lam(:)
    integer::n,i,j,ikmax,imin
    real(rk)::tmp
    real(rk),allocatable::vtmp(:)
    n=size(M,1);status=RD_OK;max_frequency_hz=0
    if(n<1.or.size(M,2)/=n.or.any(shape(K)/=shape(M)))then;status=RD_ERR_INPUT;return;endif
    allocate(A(n,n),B(n,n),ar(n),ai(n),beta(n),VR(n,n),lam(n));A=K;B=M
    call generalized_eig_real(A,B,ar,ai,beta,VR,status);if(status/=RD_OK)return
    do i=1,n
      if(abs(beta(i))<=tiny(1._rk))then;status=RD_ERR_LAPACK;return;endif
      if(abs(ai(i)/beta(i))>1e-9_rk*max(1._rk,abs(ar(i)/beta(i))))then
        status=RD_ERR_UNSUPPORTED;return
      endif
      lam(i)=ar(i)/beta(i)
    enddo
    ! V2 uses sort(diag(eigval)): for the real modal-reduction cases this is ascending numeric order.
    allocate(vtmp(n))
    do i=1,n-1
      imin=i
      do j=i+1,n;if(lam(j)<lam(imin))imin=j;enddo
      if(imin/=i)then
        tmp=lam(i);lam(i)=lam(imin);lam(imin)=tmp
        vtmp=VR(:,i);VR(:,i)=VR(:,imin);VR(:,imin)=vtmp
      endif
    enddo
    if(nr_requested>0.and.nr_requested<n)then;nr_used=nr_requested;else;nr_used=n;endif
    allocate(Tr(n,nr_used),eigvals(n));eigvals=lam
    if(nr_used<n)then
      Tr=VR(:,1:nr_used)
    else
      Tr=0._rk;do i=1,n;Tr(i,i)=1._rk;enddo
    endif
    ikmax=nr_used;if(lam(ikmax)>=0._rk)max_frequency_hz=sqrt(lam(ikmax))/(2*acos(-1._rk))
  end subroutine
end module rd_reduction
