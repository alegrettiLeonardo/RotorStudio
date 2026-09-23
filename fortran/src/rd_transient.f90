module rd_transient
  use rd_kinds,only:rk,ik
  use rd_status,only:RD_OK,RD_ERR_INPUT,RD_ERR_UNSUPPORTED
  use rd_lapack,only:solve_real
  use rd_reduction,only:modal_truncation
  use rd_dp45,only:dp45_time_fdn_grid,dp45_runup_span
  implicit none(type,external)
  private
  public :: time_foundation_response,runup_response
contains
  subroutine time_foundation_response(M,C,K,Mb,Cb,Kb,is_zero,bear,nbear,foundation_amp,pulse_duration,dt,npts,nr_request,rtol,atol,h_init,h_max,response,force,time,nr_used,max_frequency_hz,naccept,nreject,status)
    real(rk),intent(in)::M(:,:),C(:,:),K(:,:),Mb(:,:),Cb(:,:),Kb(:,:),bear(34,nbear),foundation_amp(2*nbear),pulse_duration,dt,rtol,atol,h_init,h_max
    logical,intent(in)::is_zero(:);integer(ik),intent(in)::nbear,npts,nr_request
    real(rk),intent(out)::response(size(M,1),npts),force(npts),time(npts),max_frequency_hz
    integer(ik),intent(out)::nr_used,naccept,nreject,status
    integer::ndof,nc,i,j,idx,node,npulse,nstate;integer,allocatable::keep(:)
    real(rk),allocatable::qf(:),Mr(:,:),Cr(:,:),Kr(:,:),Mf(:),Cf(:),Kf(:),Tr(:,:),evals(:),Mred(:,:),Cred(:,:),Kred(:,:),Mfr(:,:),Cfr(:,:),Kfr(:,:),XK(:,:),XC(:,:),XB2(:,:),XB1(:,:),XB0(:,:),y0(:),yout(:,:)
    real(rk)::om
    ndof=size(M,1);response=0;force=0;time=0;status=RD_OK;nr_used=0;max_frequency_hz=0;naccept=0;nreject=0
    if(npts<1.or.dt<=0.or.pulse_duration<=0.or.nbear<1)then;status=RD_ERR_INPUT;return;endif
    nc=count(.not.is_zero);allocate(keep(nc));idx=0;do i=1,ndof;if(.not.is_zero(i))then;idx=idx+1;keep(idx)=i;endif;enddo
    allocate(qf(ndof));qf=0
    do i=1,nbear
      node=nint(bear(2,i));if(node<1.or.4*node>ndof)then;status=RD_ERR_INPUT;return;endif
      ! Preserve V2 predicate (>2 | <9): it is true for every finite numeric bearing type.
      qf(4*node-3)=foundation_amp(2*i-1);qf(4*node-2)=foundation_amp(2*i)
    enddo
    allocate(Mr(nc,nc),Cr(nc,nc),Kr(nc,nc),Mf(nc),Cf(nc),Kf(nc))
    Mr=M(keep,keep);Cr=C(keep,keep);Kr=K(keep,keep)
    Mf=matmul(Mb(keep,:),qf);Cf=matmul(Cb(keep,:),qf);Kf=matmul(Kb(keep,:),qf)
    call modal_truncation(Mr,Kr,nr_request,Tr,evals,nr_used,max_frequency_hz,status);if(status/=RD_OK)return
    allocate(Mred(nr_used,nr_used),Cred(nr_used,nr_used),Kred(nr_used,nr_used),Mfr(nr_used,1),Cfr(nr_used,1),Kfr(nr_used,1))
    Mred=matmul(transpose(Tr),matmul(Mr,Tr));Cred=matmul(transpose(Tr),matmul(Cr,Tr));Kred=matmul(transpose(Tr),matmul(Kr,Tr))
    Mfr(:,1)=matmul(transpose(Tr),Mf);Cfr(:,1)=matmul(transpose(Tr),Cf);Kfr(:,1)=matmul(transpose(Tr),Kf)
    allocate(XK(nr_used,nr_used),XC(nr_used,nr_used),XB2(nr_used,1),XB1(nr_used,1),XB0(nr_used,1))
    XK=Kred;call solve_left(Mred,XK,status);if(status/=RD_OK)return
    XC=Cred;call solve_left(Mred,XC,status);if(status/=RD_OK)return
    XB2=Mfr;call solve_left(Mred,XB2,status);if(status/=RD_OK)return
    XB1=Cfr;call solve_left(Mred,XB1,status);if(status/=RD_OK)return
    XB0=Kfr;call solve_left(Mred,XB0,status);if(status/=RD_OK)return
    do i=1,npts;time(i)=dt*real(i-1,rk);enddo
    npulse=min(npts,floor(pulse_duration/dt)+1);om=acos(-1._rk)/pulse_duration
    do i=1,npulse;force(i)=sin(om*time(i));enddo
    nstate=2*nr_used;allocate(y0(nstate),yout(nstate,npts));y0=0
    call dp45_time_fdn_grid(XK,XC,XB2(:,1),XB1(:,1),XB0(:,1),pulse_duration,y0,time,rtol,atol,h_init,h_max,yout,naccept,nreject,status);if(status/=RD_OK)return
    do j=1,npts
      response(keep,j)=matmul(Tr,yout(1:nr_used,j))
    enddo
  end subroutine

  subroutine runup_response(M,C,C1,K,is_zero,force_complex,alpha,t0,tf,nr_request,rtol,atol,h_init,h_max,max_out,time,response,speed,nout,nr_used,max_frequency_hz,naccept,nreject,status)
    real(rk),intent(in)::M(:,:),C(:,:),C1(:,:),K(:,:),force_complex(:,:),alpha(3),t0,tf,rtol,atol,h_init,h_max
    logical,intent(in)::is_zero(:);integer(ik),intent(in)::nr_request,max_out
    real(rk),intent(out)::time(max_out),response(size(M,1),max_out),speed(max_out),max_frequency_hz
    integer(ik),intent(out)::nout,nr_used,naccept,nreject,status
    integer::ndof,nc,i,j,idx,nstate;integer,allocatable::keep(:)
    real(rk),allocatable::Mr(:,:),Cr(:,:),C1r0(:,:),Kr(:,:),Tr(:,:),evals(:),Mred(:,:),Cred(:,:),C1red(:,:),Kred(:,:),XK(:,:),XC(:,:),XC1(:,:),frre(:,:),frim(:,:),BFre(:,:),BFim(:,:),y0(:),yout(:,:)
    real(rk)::a2,a1,a0
    ndof=size(M,1);response=0;time=0;speed=0;status=RD_OK;nout=0;nr_used=0;max_frequency_hz=0;naccept=0;nreject=0
    if(tf<t0.or.max_out<2.or.size(force_complex,1)/=ndof.or.size(force_complex,2)/=2)then;status=RD_ERR_INPUT;return;endif
    nc=count(.not.is_zero);allocate(keep(nc));idx=0;do i=1,ndof;if(.not.is_zero(i))then;idx=idx+1;keep(idx)=i;endif;enddo
    allocate(Mr(nc,nc),Cr(nc,nc),C1r0(nc,nc),Kr(nc,nc));Mr=M(keep,keep);Cr=C(keep,keep);C1r0=C1(keep,keep);Kr=K(keep,keep)
    call modal_truncation(Mr,Kr,nr_request,Tr,evals,nr_used,max_frequency_hz,status);if(status/=RD_OK)return
    allocate(Mred(nr_used,nr_used),Cred(nr_used,nr_used),C1red(nr_used,nr_used),Kred(nr_used,nr_used))
    Mred=matmul(transpose(Tr),matmul(Mr,Tr));Cred=matmul(transpose(Tr),matmul(Cr,Tr));C1red=matmul(transpose(Tr),matmul(C1r0,Tr));Kred=matmul(transpose(Tr),matmul(Kr,Tr))
    allocate(XK(nr_used,nr_used),XC(nr_used,nr_used),XC1(nr_used,nr_used),frre(nr_used,1),frim(nr_used,1),BFre(nr_used,1),BFim(nr_used,1))
    XK=Kred;call solve_left(Mred,XK,status);if(status/=RD_OK)return
    XC=Cred;call solve_left(Mred,XC,status);if(status/=RD_OK)return
    XC1=C1red;call solve_left(Mred,XC1,status);if(status/=RD_OK)return
    frre(:,1)=matmul(transpose(Tr),force_complex(keep,1));frim(:,1)=matmul(transpose(Tr),force_complex(keep,2))
    BFre=frre;call solve_left(Mred,BFre,status);if(status/=RD_OK)return
    BFim=frim;call solve_left(Mred,BFim,status);if(status/=RD_OK)return
    a2=alpha(1);a1=alpha(2);a0=alpha(3);nstate=2*nr_used;allocate(y0(nstate),yout(nstate,max_out));y0=0
    call dp45_runup_span(XK,XC,XC1,BFre(:,1),BFim(:,1),alpha,t0,tf,y0,rtol,atol,h_init,h_max,max_out,time,yout,nout,naccept,nreject,status);if(status/=RD_OK)return
    do j=1,nout
      response(keep,j)=matmul(Tr,yout(1:nr_used,j));speed(j)=2*a2*time(j)+a1
    enddo
  end subroutine

  subroutine solve_left(A,B,status)
    real(rk),intent(in)::A(:,:);real(rk),intent(inout)::B(:,:);integer(ik),intent(out)::status
    real(rk),allocatable::Ac(:,:);allocate(Ac(size(A,1),size(A,2)));Ac=A;call solve_real(Ac,B,status)
  end subroutine
end module rd_transient
