module rd_frequency_response
 use rd_kinds,only:rk,ik
 use rd_status,only:RD_OK,RD_ERR_INPUT,RD_ERR_UNSUPPORTED
 use rd_lapack,only:solve_real,solve_complex
 implicit none(type,external);private;public::synchronous_response
contains
 subroutine synchronous_response(M0,C0,C1,K0,K1,Mb,Cb,Kb,is_zero,speed,force_def,nforce,bend_def,nbend,response,status)
  real(rk),intent(in)::M0(:,:),C0(:,:),C1(:,:),K0(:,:),K1(:,:),Mb(:,:),Cb(:,:),Kb(:,:),speed
  logical,intent(in)::is_zero(:);integer(ik),intent(in)::nforce,nbend
  real(rk),intent(in)::force_def(5,nforce),bend_def(3,max(1,nbend))
  complex(rk),intent(out)::response(:);integer(ik),intent(out)::status
  integer::ndof,nc,i,node,n1,n2,idx,nmaster,nslave;integer,allocatable::keep(:),master(:),slave(:)
  complex(rk),allocatable::ub(:),pzt(:),bendf(:),force(:),fullf(:),A(:,:),rhs(:,:),xm(:),xs(:,:)
  real(rk),allocatable::M(:,:),C(:,:),K(:,:),Kss(:,:),Ksm(:,:),Kr(:,:)
  complex(rk)::phase,jot
  ndof=size(M0,1);response=(0._rk,0._rk);status=RD_OK;jot=(0._rk,1._rk)
  nc=count(.not.is_zero);allocate(keep(nc));idx=0;do i=1,ndof;if(.not.is_zero(i))then;idx=idx+1;keep(idx)=i;endif;enddo
  allocate(ub(nc),pzt(nc),bendf(nc),force(nc),M(nc,nc),C(nc,nc),K(nc,nc),A(nc,nc),rhs(nc,1));ub=0;pzt=0;bendf=0
  M=M0(keep,keep)+Mb(keep,keep);C=C0(keep,keep)+Cb(keep,keep)+speed*C1(keep,keep);K=K0(keep,keep)+Kb(keep,keep)+speed*K1(keep,keep)
  do i=1,nforce
    select case(nint(force_def(1,i)))
    case(1)
      node=nint(force_def(2,i));if(node<1.or.4*node>ndof)then;status=RD_ERR_INPUT;return;endif
      phase=cmplx(cos(force_def(4,i)),sin(force_def(4,i)),rk)*force_def(3,i)
      call add_full_force(4*node-3,phase,ub,keep);call add_full_force(4*node-2,-jot*phase,ub,keep)
    case(2)
      node=nint(force_def(2,i));if(node<1.or.4*node>ndof)then;status=RD_ERR_INPUT;return;endif
      phase=cmplx(cos(force_def(4,i)),sin(force_def(4,i)),rk)*force_def(3,i)
      call add_full_force(4*node-1,jot*phase,ub,keep);call add_full_force(4*node,phase,ub,keep)
    case(3)
      if(nbend<=0)then;status=RD_ERR_INPUT;return;endif
    case(8)
      n1=nint(force_def(2,i));n2=nint(force_def(3,i));phase=cmplx(cos(force_def(5,i)),sin(force_def(5,i)),rk)*force_def(4,i)
      call add_full_force(4*n1-1,jot*phase,pzt,keep);call add_full_force(4*n1,phase,pzt,keep)
      call add_full_force(4*n2-1,-jot*phase,pzt,keep);call add_full_force(4*n2,-phase,pzt,keep)
    case default
      ! Legacy freq_rsp ignores other force definitions.
    end select
  enddo
  if(any(nint(force_def(1,:))==3).and.nbend>0)then
    nmaster=2*nbend;allocate(master(nmaster),xm(nmaster));
    do i=1,nbend
      node=nint(bend_def(1,i));master(2*i-1)=4*node-3;master(2*i)=4*node-2
      xm(2*i-1)=cmplx(bend_def(2,i),bend_def(3,i),rk);xm(2*i)=cmplx(bend_def(3,i),-bend_def(2,i),rk)
    enddo
    nslave=ndof-nmaster;allocate(slave(nslave));idx=0
    do i=1,ndof;if(.not.any(master==i))then;idx=idx+1;slave(idx)=i;endif;enddo
    allocate(Kss(nslave,nslave),Ksm(nslave,nmaster),Kr(ndof,ndof),xs(nslave,1));Kss=K0(slave,slave);Ksm=K0(slave,master)
    xs(:,1)=-matmul(Ksm,xm);call solve_real_complex_rhs(Kss,xs,status);if(status/=RD_OK)return
    allocate(fullf(ndof));fullf=0;fullf(master)=xm;fullf(slave)=xs(:,1);fullf=matmul(cmplx(K0,0._rk,rk),fullf)
    do i=1,nc;bendf(i)=fullf(keep(i));enddo;deallocate(fullf)
  endif
  force=bendf+pzt+ub*speed**2
  A=cmplx(K-speed**2*M,speed*C,rk);rhs(:,1)=force;call solve_complex(A,rhs,status);if(status/=RD_OK)return
  do i=1,nc;response(keep(i))=rhs(i,1);enddo
 contains
  subroutine add_full_force(full,value,v,keepv)
    integer,intent(in)::full,keepv(:);complex(rk),intent(in)::value;complex(rk),intent(inout)::v(:);integer::q
    do q=1,size(keepv);if(keepv(q)==full)then;v(q)=v(q)+value;exit;endif;enddo
  end subroutine
  subroutine solve_real_complex_rhs(Ar,X,status2)
    real(rk),intent(in)::Ar(:,:);complex(rk),intent(inout)::X(:,:);integer(ik),intent(out)::status2
    complex(rk),allocatable::Ac(:,:);allocate(Ac(size(Ar,1),size(Ar,2)));Ac=cmplx(Ar,0._rk,rk);call solve_complex(Ac,X,status2)
  end subroutine
 end subroutine
end module rd_frequency_response
