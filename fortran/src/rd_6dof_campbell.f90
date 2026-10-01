! SPDX-License-Identifier: Apache-2.0
! B2 standard Campbell sweep: dense modal solve at each speed and ROSS MAC>0.9 tracking.
module rd_6dof_campbell
  use iso_c_binding, only: c_double,c_int
  use, intrinsic :: ieee_arithmetic, only: ieee_is_finite
  use rd_6dof_assembly, only: assemble_6dof,B2_OK,B2_INVALID_INPUT,B2_NONFINITE
  use rd_6dof_modal, only: modal_from_matrices
  implicit none(type,external)
  private
  integer,parameter::dp=c_double
  real(dp),parameter::TRACK_THRESHOLD=0.9_dp
  public :: campbell_6dof
contains
  pure real(dp) function vector_mac(u,v)
    complex(dp),intent(in)::u(:),v(:)
    complex(dp)::uv
    real(dp)::den
    uv=sum(conjg(u)*v);den=real(sum(conjg(u)*u),dp)*real(sum(conjg(v)*v),dp)
    if(den<=tiny(1._dp))then;vector_mac=0._dp
    else;vector_mac=abs(uv)**2/den
    end if
  end function

  pure logical function is_permutation(order,n)
    integer,intent(in)::order(n),n
    integer::i,j,count
    is_permutation=.true.
    do i=1,n
      count=0
      do j=1,n;if(order(j)==i)count=count+1;end do
      if(count/=1)then;is_permutation=.false.;return;end if
    end do
  end function

  subroutine campbell_6dof(nn,ns,shaft_nodes,shaft_par,shaft_flags,nd,disk_nodes,disk_par,nb,bearing_nodes, &
                           nsp,speeds,bearing_map,frequencies,wd_out,wn_out,zeta_out,logdec_out,whirl_out,type_out, &
                           tracking_index,tracking_mac,mac_matrix,status)
    integer(c_int),intent(in)::nn,ns,nd,nb,nsp,frequencies
    integer(c_int),intent(in)::shaft_nodes(2,max(1,ns)),shaft_flags(4,max(1,ns)),disk_nodes(max(1,nd)),bearing_nodes(max(1,nb))
    real(dp),intent(in)::shaft_par(10,max(1,ns)),disk_par(3,max(1,nd)),speeds(nsp)
    real(dp),intent(in)::bearing_map(12,max(1,nb),nsp)
    real(dp),intent(out)::wd_out(frequencies,nsp),wn_out(frequencies,nsp),zeta_out(frequencies,nsp), &
                              logdec_out(frequencies,nsp),whirl_out(frequencies,nsp)
    integer(c_int),intent(out)::type_out(frequencies,nsp),tracking_index(frequencies+2,nsp)
    real(dp),intent(out)::tracking_mac(frequencies+2,nsp),mac_matrix(frequencies+2,frequencies+2,nsp)
    integer(c_int),intent(out)::status
    integer::ndof,ntrack,s,i,j,bestj,nmissing,kmiss
    integer,allocatable::found(:),missing(:),used(:)
    real(dp)::best
    real(dp),allocatable::MM(:,:),KK(:,:),CC(:,:),GG(:,:),KSD(:,:),wn(:),wd(:),zeta(:),logdec(:),whirl(:),residual(:)
    complex(dp),allocatable::eall(:),Vall(:,:),evals(:),qvec(:,:),rawV(:,:),trackedV(:,:),prevV(:,:)
    integer(c_int),allocatable::mtype(:)
    integer(c_int)::nret,nsel,st
    real(dp)::rcond
    status=B2_INVALID_INPUT
    if(nn<2.or.nsp<2.or.frequencies<1.or.frequencies+2>6*nn)return
    if(.not.all(ieee_is_finite(speeds)))return
    do s=2,nsp;if(speeds(s)<=speeds(s-1))return;end do
    ndof=6*nn;ntrack=frequencies+2
    allocate(MM(ndof,ndof),KK(ndof,ndof),CC(ndof,ndof),GG(ndof,ndof),KSD(ndof,ndof), &
             found(ntrack),missing(ntrack),used(ntrack),rawV(2*ndof,ntrack),trackedV(2*ndof,ntrack),prevV(2*ndof,ntrack))
    wd_out=0;wn_out=0;zeta_out=0;logdec_out=0;whirl_out=0;type_out=0;tracking_index=0;tracking_mac=0;mac_matrix=0
    do s=1,nsp
      call assemble_6dof(nn,ns,shaft_nodes,shaft_par,shaft_flags,nd,disk_nodes,disk_par,nb,bearing_nodes,bearing_map(:,:,s),MM,KK,CC,GG,KSD,st)
      if(st/=B2_OK)then;status=st;return;end if
      call modal_from_matrices(MM,KK,CC,GG,speeds(s),int(2*ntrack,c_int),eall,Vall,nret,evals,qvec,wn,wd,zeta,logdec,mtype,whirl,residual,nsel,rcond,st)
      if(st/=B2_OK)then;status=st;return;end if
      if(nsel<ntrack)then;status=B2_INVALID_INPUT;return;end if
      rawV=Vall(:,1:ntrack)
      if(s==1)then
        do i=1,ntrack;found(i)=i;tracking_mac(i,s)=1._dp;mac_matrix(i,i,s)=1._dp;end do
      else
        do i=1,ntrack
          do j=1,ntrack;mac_matrix(i,j,s)=vector_mac(prevV(:,i),rawV(:,j));end do
        end do
        found=-1
        do i=1,ntrack
          best=-1._dp;bestj=-1
          do j=1,ntrack
            if(mac_matrix(i,j,s)>TRACK_THRESHOLD .and. mac_matrix(i,j,s)>best)then
              best=mac_matrix(i,j,s);bestj=j
            end if
          end do
          found(i)=bestj
        end do
        used=0
        do i=1,ntrack;if(found(i)>0)used(found(i))=1;end do
        nmissing=0
        do j=1,ntrack;if(used(j)==0)then;nmissing=nmissing+1;missing(nmissing)=j;end if;end do
        kmiss=0
        do i=1,ntrack
          if(found(i)<1)then;kmiss=kmiss+1;if(kmiss>nmissing)then;status=B2_INVALID_INPUT;return;end if;found(i)=missing(kmiss);end if
        end do
        if(.not.is_permutation(found,ntrack))then;status=B2_INVALID_INPUT;return;end if
        do i=1,ntrack;tracking_mac(i,s)=mac_matrix(i,found(i),s);end do
      end if
      do i=1,ntrack;trackedV(:,i)=rawV(:,found(i));tracking_index(i,s)=int(found(i)-1,c_int);end do
      do i=1,frequencies
        wd_out(i,s)=wd(found(i));wn_out(i,s)=wn(found(i));zeta_out(i,s)=zeta(found(i));logdec_out(i,s)=logdec(found(i))
        whirl_out(i,s)=whirl(found(i));type_out(i,s)=mtype(found(i))
      end do
      prevV=trackedV
      deallocate(eall,Vall,evals,qvec,wn,wd,zeta,logdec,mtype,whirl,residual)
    end do
    if(.not.all(ieee_is_finite(wd_out)).or..not.all(ieee_is_finite(wn_out)).or..not.all(ieee_is_finite(zeta_out)).or. &
       .not.all(ieee_is_finite(tracking_mac)).or..not.all(ieee_is_finite(mac_matrix)))then;status=B2_NONFINITE;return;end if
    status=B2_OK
  end subroutine
end module rd_6dof_campbell
