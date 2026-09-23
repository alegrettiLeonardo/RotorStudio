module rd_dp45
  use rd_kinds, only: rk, ik
  use rd_status, only: RD_OK, RD_ERR_INPUT
  implicit none(type, external)
  private
  public :: dp45_time_fdn_grid, dp45_runup_span
contains
  subroutine dp45_time_fdn_grid(XK,XC,B2,B1,B0,pulse_duration,y0,t_eval,rtol,atol,h_init,h_max,yout,naccept,nreject,status)
    real(rk),intent(in)::XK(:,:),XC(:,:),B2(:),B1(:),B0(:),pulse_duration,y0(:),t_eval(:),rtol,atol,h_init,h_max
    real(rk),intent(out)::yout(size(y0),size(t_eval))
    integer(ik),intent(out)::naccept,nreject,status
    real(rk),allocatable::y(:),yn(:)
    real(rk)::t,h,target,hs,errn,fac
    logical::accepted
    integer::k,guard
    status=RD_OK;naccept=0;nreject=0
    if(size(t_eval)<1.or.size(y0)<1.or.rtol<=0._rk.or.atol<=0._rk)then;status=RD_ERR_INPUT;return;endif
    allocate(y(size(y0)),yn(size(y0)));y=y0;t=t_eval(1);yout(:,1)=y
    h=initial_step(h_init,h_max,max(1e-12_rk,t_eval(size(t_eval))-t_eval(1)))
    do k=2,size(t_eval)
      target=t_eval(k);guard=0
      do while(t<target)
        guard=guard+1;if(guard>1000000)then;status=RD_ERR_INPUT;return;endif
        hs=min(h,target-t)
        call step_time_fdn(XK,XC,B2,B1,B0,pulse_duration,t,y,hs,rtol,atol,yn,errn,accepted)
        if(accepted)then
          t=t+hs;y=yn;naccept=naccept+1;fac=step_factor(errn,.true.);h=hs*fac
        else
          nreject=nreject+1;fac=step_factor(errn,.false.);h=hs*fac
        endif
        if(h_max>0._rk)h=min(h,h_max)
        if(h<=spacing(max(1._rk,abs(t))))then;status=RD_ERR_INPUT;return;endif
      enddo
      t=target;yout(:,k)=y
    enddo
  end subroutine

  subroutine dp45_runup_span(XK,XC,XC1,BFre,BFim,alpha,t0,tf,y0,rtol,atol,h_init,h_max,max_out,tout,yout,nout,naccept,nreject,status)
    real(rk),intent(in)::XK(:,:),XC(:,:),XC1(:,:),BFre(:),BFim(:),alpha(3),t0,tf,y0(:),rtol,atol,h_init,h_max
    integer(ik),intent(in)::max_out
    real(rk),intent(out)::tout(max_out),yout(size(y0),max_out)
    integer(ik),intent(out)::nout,naccept,nreject,status
    real(rk),allocatable::y(:),yn(:)
    real(rk)::t,h,errn,fac
    logical::accepted
    integer::guard
    status=RD_OK;naccept=0;nreject=0;nout=0
    if(tf<t0.or.size(y0)<1.or.max_out<1.or.rtol<=0._rk.or.atol<=0._rk)then;status=RD_ERR_INPUT;return;endif
    allocate(y(size(y0)),yn(size(y0)));y=y0;t=t0;nout=1;tout(1)=t;yout(:,1)=y
    if(tf<=t0)return
    h=initial_step(h_init,h_max,tf-t0);guard=0
    do while(t<tf)
      guard=guard+1;if(guard>10000000)then;status=RD_ERR_INPUT;return;endif
      h=min(h,tf-t)
      call step_runup(XK,XC,XC1,BFre,BFim,alpha,t,y,h,rtol,atol,yn,errn,accepted)
      if(accepted)then
        t=t+h;y=yn;naccept=naccept+1
        if(nout>=max_out)then;status=RD_ERR_INPUT;return;endif
        nout=nout+1;tout(nout)=t;yout(:,nout)=y;fac=step_factor(errn,.true.);h=h*fac
      else
        nreject=nreject+1;fac=step_factor(errn,.false.);h=h*fac
      endif
      if(h_max>0._rk)h=min(h,h_max)
      if(h<=spacing(max(1._rk,abs(t))))then;status=RD_ERR_INPUT;return;endif
    enddo
  end subroutine

  subroutine step_time_fdn(XK,XC,B2,B1,B0,pulse,t,y,h,rtol,atol,y5,errn,accepted)
    real(rk),intent(in)::XK(:,:),XC(:,:),B2(:),B1(:),B0(:),pulse,t,y(:),h,rtol,atol
    real(rk),intent(out)::y5(:),errn;logical,intent(out)::accepted
    real(rk),allocatable::k1(:),k2(:),k3(:),k4(:),k5(:),k6(:),k7(:),yt(:),y4(:),sc(:);integer::n
    n=size(y);allocate(k1(n),k2(n),k3(n),k4(n),k5(n),k6(n),k7(n),yt(n),y4(n),sc(n))
    call eval_time_fdn(XK,XC,B2,B1,B0,pulse,t,y,k1)
    yt=y+h*(1._rk/5._rk)*k1;call eval_time_fdn(XK,XC,B2,B1,B0,pulse,t+h/5._rk,yt,k2)
    yt=y+h*((3._rk/40._rk)*k1+(9._rk/40._rk)*k2);call eval_time_fdn(XK,XC,B2,B1,B0,pulse,t+3*h/10._rk,yt,k3)
    yt=y+h*((44._rk/45._rk)*k1-(56._rk/15._rk)*k2+(32._rk/9._rk)*k3);call eval_time_fdn(XK,XC,B2,B1,B0,pulse,t+4*h/5._rk,yt,k4)
    yt=y+h*((19372._rk/6561._rk)*k1-(25360._rk/2187._rk)*k2+(64448._rk/6561._rk)*k3-(212._rk/729._rk)*k4);call eval_time_fdn(XK,XC,B2,B1,B0,pulse,t+8*h/9._rk,yt,k5)
    yt=y+h*((9017._rk/3168._rk)*k1-(355._rk/33._rk)*k2+(46732._rk/5247._rk)*k3+(49._rk/176._rk)*k4-(5103._rk/18656._rk)*k5);call eval_time_fdn(XK,XC,B2,B1,B0,pulse,t+h,yt,k6)
    y5=y+h*((35._rk/384._rk)*k1+(500._rk/1113._rk)*k3+(125._rk/192._rk)*k4-(2187._rk/6784._rk)*k5+(11._rk/84._rk)*k6)
    call eval_time_fdn(XK,XC,B2,B1,B0,pulse,t+h,y5,k7)
    y4=y+h*((5179._rk/57600._rk)*k1+(7571._rk/16695._rk)*k3+(393._rk/640._rk)*k4-(92097._rk/339200._rk)*k5+(187._rk/2100._rk)*k6+(1._rk/40._rk)*k7)
    call error_norm(y,y5,y4,rtol,atol,errn,accepted)
  end subroutine

  subroutine step_runup(XK,XC,XC1,BFre,BFim,alpha,t,y,h,rtol,atol,y5,errn,accepted)
    real(rk),intent(in)::XK(:,:),XC(:,:),XC1(:,:),BFre(:),BFim(:),alpha(3),t,y(:),h,rtol,atol
    real(rk),intent(out)::y5(:),errn;logical,intent(out)::accepted
    real(rk),allocatable::k1(:),k2(:),k3(:),k4(:),k5(:),k6(:),k7(:),yt(:),y4(:),sc(:);integer::n
    n=size(y);allocate(k1(n),k2(n),k3(n),k4(n),k5(n),k6(n),k7(n),yt(n),y4(n),sc(n))
    call eval_runup(XK,XC,XC1,BFre,BFim,alpha,t,y,k1)
    yt=y+h*k1/5._rk;call eval_runup(XK,XC,XC1,BFre,BFim,alpha,t+h/5._rk,yt,k2)
    yt=y+h*((3._rk/40._rk)*k1+(9._rk/40._rk)*k2);call eval_runup(XK,XC,XC1,BFre,BFim,alpha,t+3*h/10._rk,yt,k3)
    yt=y+h*((44._rk/45._rk)*k1-(56._rk/15._rk)*k2+(32._rk/9._rk)*k3);call eval_runup(XK,XC,XC1,BFre,BFim,alpha,t+4*h/5._rk,yt,k4)
    yt=y+h*((19372._rk/6561._rk)*k1-(25360._rk/2187._rk)*k2+(64448._rk/6561._rk)*k3-(212._rk/729._rk)*k4);call eval_runup(XK,XC,XC1,BFre,BFim,alpha,t+8*h/9._rk,yt,k5)
    yt=y+h*((9017._rk/3168._rk)*k1-(355._rk/33._rk)*k2+(46732._rk/5247._rk)*k3+(49._rk/176._rk)*k4-(5103._rk/18656._rk)*k5);call eval_runup(XK,XC,XC1,BFre,BFim,alpha,t+h,yt,k6)
    y5=y+h*((35._rk/384._rk)*k1+(500._rk/1113._rk)*k3+(125._rk/192._rk)*k4-(2187._rk/6784._rk)*k5+(11._rk/84._rk)*k6)
    call eval_runup(XK,XC,XC1,BFre,BFim,alpha,t+h,y5,k7)
    y4=y+h*((5179._rk/57600._rk)*k1+(7571._rk/16695._rk)*k3+(393._rk/640._rk)*k4-(92097._rk/339200._rk)*k5+(187._rk/2100._rk)*k6+(1._rk/40._rk)*k7)
    call error_norm(y,y5,y4,rtol,atol,errn,accepted)
  end subroutine

  subroutine eval_time_fdn(XK,XC,B2,B1,B0,pulse,t,y,dy)
    real(rk),intent(in)::XK(:,:),XC(:,:),B2(:),B1(:),B0(:),pulse,t,y(:);real(rk),intent(out)::dy(:)
    integer::nr;real(rk)::om,yy,yd,ydd
    nr=size(XK,1);dy(1:nr)=y(nr+1:2*nr);dy(nr+1:2*nr)=-matmul(XK,y(1:nr))-matmul(XC,y(nr+1:2*nr))
    if(t<=pulse)then;om=acos(-1._rk)/pulse;yy=sin(om*t);yd=om*cos(om*t);ydd=-om*om*yy;dy(nr+1:2*nr)=dy(nr+1:2*nr)+B2*ydd+B1*yd+B0*yy;endif
  end subroutine

  subroutine eval_runup(XK,XC,XC1,BFre,BFim,alpha,t,y,dy)
    real(rk),intent(in)::XK(:,:),XC(:,:),XC1(:,:),BFre(:),BFim(:),alpha(3),t,y(:);real(rk),intent(out)::dy(:)
    integer::nr;real(rk)::phi,dphi,ddphi,cr,ci
    nr=size(XK,1);phi=alpha(1)*t*t+alpha(2)*t+alpha(3);dphi=2*alpha(1)*t+alpha(2);ddphi=2*alpha(1)
    cr=dphi*dphi*cos(phi)+ddphi*sin(phi);ci=dphi*dphi*sin(phi)-ddphi*cos(phi)
    dy(1:nr)=y(nr+1:2*nr);dy(nr+1:2*nr)=-matmul(XK,y(1:nr))-matmul(XC,y(nr+1:2*nr))-dphi*matmul(XC1,y(nr+1:2*nr))+BFre*cr-BFim*ci
  end subroutine

  subroutine error_norm(y,y5,y4,rtol,atol,errn,accepted)
    real(rk),intent(in)::y(:),y5(:),y4(:),rtol,atol;real(rk),intent(out)::errn;logical,intent(out)::accepted
    real(rk),allocatable::sc(:);allocate(sc(size(y)));sc=atol+rtol*max(abs(y),abs(y5));errn=sqrt(sum(((y5-y4)/sc)**2)/real(size(y),rk));accepted=(errn<=1._rk)
  end subroutine

  pure real(rk) function step_factor(errn,accepted) result(f)
    real(rk),intent(in)::errn;logical,intent(in)::accepted
    if(errn<=tiny(1._rk))then;f=5._rk;else;f=.9_rk*errn**(-.2_rk);endif
    if(accepted)then;f=min(5._rk,max(.2_rk,f));else;f=min(1._rk,max(.1_rk,f));endif
  end function

  pure real(rk) function initial_step(h_init,h_max,span) result(h)
    real(rk),intent(in)::h_init,h_max,span
    if(h_init>0._rk)then;h=h_init;else;h=max(1e-10_rk,min(span/100._rk,1e-2_rk));endif
    if(h_max>0._rk)h=min(h,h_max);h=min(h,max(span,1e-10_rk))
  end function
end module rd_dp45
