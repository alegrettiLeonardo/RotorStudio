module rb_native_multiphysics
  use rb_kinds, only: rk, ik
  use rb_status, only: RB_OK, RB_ERR_INPUT, RB_ERR_CONVERGENCE
  use rb_reynolds_element, only: rb_reynolds_q4_element
  use rb_reynolds_banded, only: rb_assemble_q4_banded, rb_include_pressure_bc, &
                                rb_lu_factor_band, rb_lu_solve_band_cavitating, rb_lu_solve_band_signed
  use rb_thermal, only: RB_THERMAL_ISOVISCOUS, RB_THERMAL_ADIABATIC, RB_THERMAL_FULL, &
                        rb_thermal_adiabatic_pad, rb_thermal_full_pad
  use rb_pad_deformation, only: RB_DEFORM_NONE, RB_DEFORM_PAD_MECHANICAL, &
                                RB_DEFORM_PAD_MECHANICAL_THERMAL, rb_pad_surface_deformation
  use rb_dynamic_reduction, only: rb_dynamic_reduce_tilts
  implicit none(type, external)
  private

  public :: rb_plain_journal_multiphysics
  public :: rb_tilting_pad_multiphysics

contains

  subroutine rb_plain_journal_multiphysics(speed,weight,fxs_load,fys_load,d,cb,mu1,mu2,t1,t2,rho,cp,klube, &
      thermal_type,deform_type,pad_thickness,kpad,epad,nupad,alphapad,temp_supply,temp_journal,temp_ambient, &
      convec_edges,convec_back,np,piv,arc,alen,pre,off,nx,nz,ny_pad,ny_film,xj0,yj0,relax_p,relax_t, &
      max_iterations,outer_iterations,force_tol,field_tol,xj_ratio,yj_ratio,k_out,c_out,fx,fy,pmax,tmax,tout, &
      deform_max,iterations,status,pressure_field,temperature_field,deformation_field)
    real(rk),intent(in)::speed,weight,fxs_load,fys_load,d,cb,mu1,mu2,t1,t2,rho,cp,klube
    integer(ik),intent(in)::thermal_type,deform_type,np,nx,nz,ny_pad,ny_film,max_iterations,outer_iterations
    real(rk),intent(in)::pad_thickness,kpad,epad,nupad,alphapad,temp_supply,temp_journal,temp_ambient
    real(rk),intent(in)::convec_edges,convec_back,piv(np),arc(np),alen(np),pre(np),off(np)
    real(rk),intent(in)::xj0,yj0,relax_p,relax_t,force_tol,field_tol
    real(rk),intent(out)::xj_ratio,yj_ratio,k_out(2,2),c_out(2,2),fx,fy,pmax,tmax,tout,deform_max
    integer(ik),intent(out)::iterations,status
    real(rk),intent(out),optional::pressure_field(:,:),temperature_field(:,:),deformation_field(:,:)

    integer::nn,nfull,npp,it,p,ix,iy,iz,n,outer_done,stride
    integer(ik)::st
    real(rk)::xj,yj,delta,temp_delta,def_delta,tmi,touti,rms,pex
    real(rk),allocatable::mu(:,:),mu_new(:,:),dh(:,:),dh_new(:,:),press(:,:),h(:,:)
    real(rk),allocatable::tad(:,:),tad_new(:),tfull(:,:),tfull_new(:),muc(:)
    real(rk),allocatable::px(:),tpad(:),def(:)
    real(rk)::fxext,fyext

    status=RB_OK;xj_ratio=0._rk;yj_ratio=0._rk;k_out=0._rk;c_out=0._rk
    fx=0._rk;fy=0._rk;pmax=0._rk;tmax=temp_supply;tout=temp_supply;deform_max=0._rk;iterations=0_ik
    if(.not.rb_check_common(speed,d,cb,mu1,np,arc,alen,pre,off,nx,nz,relax_p,max_iterations,force_tol))then
      status=RB_ERR_INPUT;return
    end if
    if(thermal_type<0_ik .or. thermal_type>2_ik .or. deform_type<0_ik .or. deform_type>2_ik .or. &
       outer_iterations<1 .or. field_tol<=0._rk)then
      status=RB_ERR_INPUT;return
    end if
    if(thermal_type/=RB_THERMAL_ISOVISCOUS)then
      if(mu2<=0._rk .or. abs(t2-t1)<=tiny(1._rk) .or. rho<=0._rk .or. cp<=0._rk .or. klube<=0._rk .or. &
         relax_t<=0._rk .or. relax_t>1._rk)then;status=RB_ERR_INPUT;return;end if
    end if
    if(deform_type/=RB_DEFORM_NONE)then
      if(pad_thickness<=0._rk .or. epad<=0._rk .or. kpad<=0._rk .or. ny_pad<2)then
        status=RB_ERR_INPUT;return
      end if
    end if

    nn=(int(nx)+1)*(int(nz)+1);nfull=(int(nx)+1)*(int(ny_pad)+int(ny_film)+1)
    npp=(int(nx)+1)*(int(ny_pad)+1)
    allocate(mu(nn,np),mu_new(nn,np),dh(int(nx)+1,np),dh_new(int(nx)+1,np),press(nn,np),h(nn,np))
    allocate(tad(nn,np),tad_new(nn),tfull(nfull,np),tfull_new(nfull),muc(nn))
    allocate(px(int(nx)+1),tpad(npp),def(int(nx)+1))
    mu=mu1;mu_new=mu1;dh=0._rk;dh_new=0._rk;tad=temp_supply;tfull=temp_supply
    xj=xj0*cb;yj=yj0*cb;fxext=fxs_load;fyext=fys_load-weight;outer_done=0

    do it=1,int(outer_iterations)
      call plain_equilibrium(speed,fxext,fyext,d,cb,np,piv,arc,alen,pre,off,nx,nz,mu,dh,xj,yj,relax_p, &
                             max_iterations,force_tol,press,h,fx,fy,pmax,iterations,st)
      if(st/=RB_OK)then;status=st;return;end if

      mu_new=mu;dh_new=dh;temp_delta=0._rk;def_delta=0._rk;tmax=temp_supply;tout=0._rk
      do p=1,int(np)
        select case(thermal_type)
        case(RB_THERMAL_ISOVISCOUS)
          tad_new=tad(:,p);muc=mu(:,p);tmi=maxval(tad_new);touti=temp_supply
        case(RB_THERMAL_ADIABATIC)
          call rb_thermal_adiabatic_pad(nx,nz,0.5_rk*d*arc(p),alen(p),speed*0.5_rk*d,h(:,p),press(:,p),mu(:,p), &
               rho,cp,klube,temp_supply,relax_t,tad(:,p),mu1,mu2,t1,t2,tad_new,muc,tmi,touti,rms,st)
          if(st/=RB_OK)then;status=st;return;end if
          temp_delta=max(temp_delta,maxval(abs(tad_new-tad(:,p))))
          tad(:,p)=tad_new;mu_new(:,p)=muc
        case(RB_THERMAL_FULL)
          call rb_thermal_full_pad(nx,nz,ny_pad,ny_film,0.5_rk*d*arc(p),alen(p),pad_thickness,speed*0.5_rk*d, &
               h(:,p),press(:,p),mu(:,p),rho,cp,klube,kpad,temp_supply,temp_journal,temp_ambient,convec_edges, &
               convec_back,relax_t,tfull(:,p),mu1,mu2,t1,t2,tfull_new,muc,tmi,touti,rms,st)
          if(st/=RB_OK)then;status=st;return;end if
          temp_delta=max(temp_delta,maxval(abs(tfull_new-tfull(:,p))))
          tfull(:,p)=tfull_new;mu_new(:,p)=muc
        end select
        tmax=max(tmax,tmi);tout=tout+touti

        if(deform_type/=RB_DEFORM_NONE)then
          do ix=0,int(nx)
            px(ix+1)=0._rk
            do iz=0,int(nz)
              n=ix*(int(nz)+1)+iz+1;px(ix+1)=px(ix+1)+press(n,p)
            end do
            px(ix+1)=px(ix+1)/real(int(nz)+1,rk)
          end do
          if(deform_type==RB_DEFORM_PAD_MECHANICAL)then
            tpad=temp_supply
          else if(thermal_type==RB_THERMAL_FULL)then
            do ix=0,int(nx)
              do iy=0,int(ny_pad)
                tpad(ix*(int(ny_pad)+1)+iy+1)=tfull(ix*(int(ny_pad)+int(ny_film)+1)+iy+1,p)
              end do
            end do
          else
            do ix=0,int(nx)
              delta=0._rk
              do iz=0,int(nz);delta=delta+tad(ix*(int(nz)+1)+iz+1,p);end do
              delta=delta/real(int(nz)+1,rk)
              do iy=0,int(ny_pad);tpad(ix*(int(ny_pad)+1)+iy+1)=delta;end do
            end do
          end if
          pex=alphapad
          if(deform_type==RB_DEFORM_PAD_MECHANICAL)pex=0._rk
          call rb_pad_surface_deformation(nx,ny_pad,0.5_rk*d*arc(p),pad_thickness,epad,nupad,pex,temp_supply, &
                                          tpad,px,.false.,off(p),def,st)
          if(st/=RB_OK)then;status=st;return;end if
          dh_new(:,p)=-def
          def_delta=max(def_delta,maxval(abs(dh_new(:,p)-dh(:,p))))
        end if
      end do
      tout=tout/real(np,rk)
      mu=(1._rk-relax_t)*mu+relax_t*mu_new
      if(deform_type/=RB_DEFORM_NONE)dh=(1._rk-relax_t)*dh+relax_t*dh_new
      deform_max=maxval(abs(dh));outer_done=it
      if((thermal_type==RB_THERMAL_ISOVISCOUS .or. temp_delta<=field_tol) .and. &
         (deform_type==RB_DEFORM_NONE .or. def_delta<=field_tol*max(cb,1e-9_rk)))exit
    end do

    if(outer_done>=int(outer_iterations) .and. &
       ((thermal_type/=RB_THERMAL_ISOVISCOUS .and. temp_delta>field_tol) .or. &
        (deform_type/=RB_DEFORM_NONE .and. def_delta>field_tol*max(cb,1e-9_rk))))then
      status=RB_ERR_CONVERGENCE;return
    end if

    call plain_equilibrium(speed,fxext,fyext,d,cb,np,piv,arc,alen,pre,off,nx,nz,mu,dh,xj,yj,relax_p, &
                           max_iterations,force_tol,press,h,fx,fy,pmax,iterations,st)
    if(st/=RB_OK)then;status=st;return;end if
    call plain_coefficients(speed,d,cb,np,piv,arc,alen,pre,off,nx,nz,mu,dh,xj,yj,press,k_out,c_out,st)
    if(st/=RB_OK)then;status=st;return;end if
    xj_ratio=xj/cb;yj_ratio=yj/cb

    if(present(pressure_field))then
      if(size(pressure_field,1)<nn .or. size(pressure_field,2)<int(np))then;status=RB_ERR_INPUT;return;end if
      pressure_field(1:nn,1:int(np))=press(1:nn,1:int(np))
    end if
    if(present(temperature_field))then
      if(size(temperature_field,1)<nn .or. size(temperature_field,2)<int(np))then;status=RB_ERR_INPUT;return;end if
      select case(thermal_type)
      case(RB_THERMAL_ISOVISCOUS)
        temperature_field(1:nn,1:int(np))=temp_supply
      case(RB_THERMAL_ADIABATIC)
        temperature_field(1:nn,1:int(np))=tad(1:nn,1:int(np))
      case(RB_THERMAL_FULL)
        stride=int(ny_pad)+int(ny_film)+1
        do p=1,int(np)
          do ix=0,int(nx)
            delta=sum(tfull(ix*stride+int(ny_pad)+1:ix*stride+stride,p))/real(int(ny_film)+1,rk)
            do iz=0,int(nz)
              n=ix*(int(nz)+1)+iz+1
              temperature_field(n,p)=delta
            end do
          end do
        end do
      end select
    end if
    if(present(deformation_field))then
      if(size(deformation_field,1)<int(nx)+1 .or. size(deformation_field,2)<int(np))then
        status=RB_ERR_INPUT;return
      end if
      deformation_field(1:int(nx)+1,1:int(np))=dh(1:int(nx)+1,1:int(np))
    end if
  end subroutine rb_plain_journal_multiphysics


  subroutine rb_tilting_pad_multiphysics(speed,omega,weight,fxs_load,fys_load,d,cb,mu1,mu2,t1,t2,rho,cp,klube, &
      thermal_type,deform_type,tp,pad_density,kpad,epad,nupad,alphapad,temp_supply,temp_journal,temp_ambient, &
      convec_edges,convec_back,np,piv,arc,alen,pre,off,krot,nx,nz,ny_pad,ny_film,xj0,yj0,relax_p,relax_t, &
      max_iterations,outer_iterations,force_tol,field_tol,xj_ratio,yj_ratio,tilt,k_out,c_out,fx,fy,pmax,tmax,tout, &
      deform_max,iterations,status,pressure_field,temperature_field,deformation_field)
    real(rk),intent(in)::speed,omega,weight,fxs_load,fys_load,d,cb,mu1,mu2,t1,t2,rho,cp,klube
    integer(ik),intent(in)::thermal_type,deform_type,np,nx,nz,ny_pad,ny_film,max_iterations,outer_iterations
    real(rk),intent(in)::tp,pad_density,kpad,epad,nupad,alphapad,temp_supply,temp_journal,temp_ambient
    real(rk),intent(in)::convec_edges,convec_back,piv(np),arc(np),alen(np),pre(np),off(np),krot(np)
    real(rk),intent(in)::xj0,yj0,relax_p,relax_t,force_tol,field_tol
    real(rk),intent(out)::xj_ratio,yj_ratio,tilt(np),k_out(2,2),c_out(2,2),fx,fy,pmax,tmax,tout,deform_max
    integer(ik),intent(out)::iterations,status
    real(rk),intent(out),optional::pressure_field(:,:),temperature_field(:,:),deformation_field(:,:)

    integer::nn,nfull,npp,it,p,ix,iy,iz,n,outer_done,stride
    integer(ik)::st
    real(rk)::xj,yj,delta,temp_delta,def_delta,tmi,touti,rms,pex
    real(rk),allocatable::mu(:,:),mu_new(:,:),dh(:,:),dh_new(:,:),press(:,:),h(:,:)
    real(rk),allocatable::tad(:,:),tad_new(:),tfull(:,:),tfull_new(:),muc(:),mom(:)
    real(rk),allocatable::px(:),tpad(:),def(:)
    real(rk)::fxext,fyext

    status=RB_OK;xj_ratio=0._rk;yj_ratio=0._rk;tilt=0._rk;k_out=0._rk;c_out=0._rk
    fx=0._rk;fy=0._rk;pmax=0._rk;tmax=temp_supply;tout=temp_supply;deform_max=0._rk;iterations=0_ik
    if(.not.rb_check_common(speed,d,cb,mu1,np,arc,alen,pre,off,nx,nz,relax_p,max_iterations,force_tol) .or. &
       omega<=0._rk .or. tp<=0._rk .or. pad_density<0._rk .or. any(off<=0._rk) .or. any(off>=1._rk))then
      status=RB_ERR_INPUT;return
    end if
    if(thermal_type<0_ik .or. thermal_type>2_ik .or. deform_type<0_ik .or. deform_type>2_ik .or. &
       outer_iterations<1 .or. field_tol<=0._rk)then;status=RB_ERR_INPUT;return;end if
    if(thermal_type/=RB_THERMAL_ISOVISCOUS)then
      if(mu2<=0._rk .or. abs(t2-t1)<=tiny(1._rk) .or. rho<=0._rk .or. cp<=0._rk .or. klube<=0._rk .or. &
         relax_t<=0._rk .or. relax_t>1._rk)then;status=RB_ERR_INPUT;return;end if
    end if
    if(deform_type/=RB_DEFORM_NONE .and. (epad<=0._rk .or. kpad<=0._rk .or. ny_pad<2))then
      status=RB_ERR_INPUT;return
    end if

    nn=(int(nx)+1)*(int(nz)+1);nfull=(int(nx)+1)*(int(ny_pad)+int(ny_film)+1);npp=(int(nx)+1)*(int(ny_pad)+1)
    allocate(mu(nn,np),mu_new(nn,np),dh(int(nx)+1,np),dh_new(int(nx)+1,np),press(nn,np),h(nn,np),mom(np))
    allocate(tad(nn,np),tad_new(nn),tfull(nfull,np),tfull_new(nfull),muc(nn))
    allocate(px(int(nx)+1),tpad(npp),def(int(nx)+1))
    mu=mu1;mu_new=mu1;dh=0._rk;dh_new=0._rk;tad=temp_supply;tfull=temp_supply
    xj=xj0*cb;yj=yj0*cb;fxext=fxs_load;fyext=fys_load-weight;outer_done=0

    do it=1,int(outer_iterations)
      call tp_journal_equilibrium(speed,fxext,fyext,d,cb,tp,np,piv,arc,alen,pre,off,krot,nx,nz,mu,dh,xj,yj, &
                                  relax_p,max_iterations,force_tol,tilt,press,h,mom,fx,fy,pmax,iterations,st)
      if(st/=RB_OK)then;status=st;return;end if
      mu_new=mu;dh_new=dh;temp_delta=0._rk;def_delta=0._rk;tmax=temp_supply;tout=0._rk
      do p=1,int(np)
        select case(thermal_type)
        case(RB_THERMAL_ISOVISCOUS)
          tad_new=tad(:,p);muc=mu(:,p);tmi=maxval(tad_new);touti=temp_supply
        case(RB_THERMAL_ADIABATIC)
          call rb_thermal_adiabatic_pad(nx,nz,0.5_rk*d*arc(p),alen(p),speed*0.5_rk*d,h(:,p),press(:,p),mu(:,p), &
               rho,cp,klube,temp_supply,relax_t,tad(:,p),mu1,mu2,t1,t2,tad_new,muc,tmi,touti,rms,st)
          if(st/=RB_OK)then;status=st;return;end if
          temp_delta=max(temp_delta,maxval(abs(tad_new-tad(:,p))));tad(:,p)=tad_new;mu_new(:,p)=muc
        case(RB_THERMAL_FULL)
          call rb_thermal_full_pad(nx,nz,ny_pad,ny_film,0.5_rk*d*arc(p),alen(p),tp,speed*0.5_rk*d,h(:,p), &
               press(:,p),mu(:,p),rho,cp,klube,kpad,temp_supply,temp_journal,temp_ambient,convec_edges,convec_back, &
               relax_t,tfull(:,p),mu1,mu2,t1,t2,tfull_new,muc,tmi,touti,rms,st)
          if(st/=RB_OK)then;status=st;return;end if
          temp_delta=max(temp_delta,maxval(abs(tfull_new-tfull(:,p))));tfull(:,p)=tfull_new;mu_new(:,p)=muc
        end select
        tmax=max(tmax,tmi);tout=tout+touti

        if(deform_type/=RB_DEFORM_NONE)then
          do ix=0,int(nx)
            px(ix+1)=0._rk
            do iz=0,int(nz);n=ix*(int(nz)+1)+iz+1;px(ix+1)=px(ix+1)+press(n,p);end do
            px(ix+1)=px(ix+1)/real(int(nz)+1,rk)
          end do
          if(deform_type==RB_DEFORM_PAD_MECHANICAL)then
            tpad=temp_supply
          else if(thermal_type==RB_THERMAL_FULL)then
            do ix=0,int(nx)
              do iy=0,int(ny_pad)
                tpad(ix*(int(ny_pad)+1)+iy+1)=tfull(ix*(int(ny_pad)+int(ny_film)+1)+iy+1,p)
              end do
            end do
          else
            do ix=0,int(nx)
              delta=0._rk
              do iz=0,int(nz);delta=delta+tad(ix*(int(nz)+1)+iz+1,p);end do
              delta=delta/real(int(nz)+1,rk)
              do iy=0,int(ny_pad);tpad(ix*(int(ny_pad)+1)+iy+1)=delta;end do
            end do
          end if
          pex=alphapad;if(deform_type==RB_DEFORM_PAD_MECHANICAL)pex=0._rk
          call rb_pad_surface_deformation(nx,ny_pad,0.5_rk*d*arc(p),tp,epad,nupad,pex,temp_supply,tpad,px, &
                                          .true.,off(p),def,st)
          if(st/=RB_OK)then;status=st;return;end if
          dh_new(:,p)=-def;def_delta=max(def_delta,maxval(abs(dh_new(:,p)-dh(:,p))))
        end if
      end do
      tout=tout/real(np,rk);mu=(1._rk-relax_t)*mu+relax_t*mu_new
      if(deform_type/=RB_DEFORM_NONE)dh=(1._rk-relax_t)*dh+relax_t*dh_new
      deform_max=maxval(abs(dh));outer_done=it
      if((thermal_type==RB_THERMAL_ISOVISCOUS .or. temp_delta<=field_tol) .and. &
         (deform_type==RB_DEFORM_NONE .or. def_delta<=field_tol*max(cb,1e-9_rk)))exit
    end do
    if(outer_done>=int(outer_iterations) .and. &
       ((thermal_type/=RB_THERMAL_ISOVISCOUS .and. temp_delta>field_tol) .or. &
        (deform_type/=RB_DEFORM_NONE .and. def_delta>field_tol*max(cb,1e-9_rk))))then
      status=RB_ERR_CONVERGENCE;return
    end if

    call tp_journal_equilibrium(speed,fxext,fyext,d,cb,tp,np,piv,arc,alen,pre,off,krot,nx,nz,mu,dh,xj,yj, &
                                relax_p,max_iterations,force_tol,tilt,press,h,mom,fx,fy,pmax,iterations,st)
    if(st/=RB_OK)then;status=st;return;end if
    call tp_coefficients(speed,omega,d,cb,tp,pad_density,np,piv,arc,alen,pre,off,krot,nx,nz,mu,dh,xj,yj,tilt, &
                         press,k_out,c_out,st)
    if(st/=RB_OK)then;status=st;return;end if
    xj_ratio=xj/cb;yj_ratio=yj/cb

    if(present(pressure_field))then
      if(size(pressure_field,1)<nn .or. size(pressure_field,2)<int(np))then;status=RB_ERR_INPUT;return;end if
      pressure_field(1:nn,1:int(np))=press(1:nn,1:int(np))
    end if
    if(present(temperature_field))then
      if(size(temperature_field,1)<nn .or. size(temperature_field,2)<int(np))then;status=RB_ERR_INPUT;return;end if
      select case(thermal_type)
      case(RB_THERMAL_ISOVISCOUS)
        temperature_field(1:nn,1:int(np))=temp_supply
      case(RB_THERMAL_ADIABATIC)
        temperature_field(1:nn,1:int(np))=tad(1:nn,1:int(np))
      case(RB_THERMAL_FULL)
        stride=int(ny_pad)+int(ny_film)+1
        do p=1,int(np)
          do ix=0,int(nx)
            delta=sum(tfull(ix*stride+int(ny_pad)+1:ix*stride+stride,p))/real(int(ny_film)+1,rk)
            do iz=0,int(nz)
              n=ix*(int(nz)+1)+iz+1
              temperature_field(n,p)=delta
            end do
          end do
        end do
      end select
    end if
    if(present(deformation_field))then
      if(size(deformation_field,1)<int(nx)+1 .or. size(deformation_field,2)<int(np))then
        status=RB_ERR_INPUT;return
      end if
      deformation_field(1:int(nx)+1,1:int(np))=dh(1:int(nx)+1,1:int(np))
    end if
  end subroutine rb_tilting_pad_multiphysics


  logical function rb_check_common(speed,d,cb,mu,np,arc,alen,pre,off,nx,nz,relax_p,maxit,ftol)
    real(rk),intent(in)::speed,d,cb,mu,arc(np),alen(np),pre(np),off(np),relax_p,ftol
    integer(ik),intent(in)::np,nx,nz,maxit
    rb_check_common=speed>0._rk .and. d>0._rk .and. cb>0._rk .and. mu>0._rk .and. np>0 .and. &
       nx>=2 .and. nz>=2 .and. mod(nx,2_ik)==0 .and. mod(nz,2_ik)==0 .and. maxit>0 .and. &
       relax_p>0._rk .and. relax_p<=1._rk .and. ftol>0._rk .and. all(arc>0._rk) .and. all(alen>0._rk) .and. &
       all(pre>=0._rk) .and. all(pre<1._rk) .and. all(off>=0._rk) .and. all(off<=1._rk)
  end function rb_check_common


  subroutine pad_static(speed,d,cb,tp,piv,arc,alen,pre,off,krot,nx,nz,xj,yj,tilt,mu,dh,pressure,h,fx,fy,moment,pmax,status)
    real(rk),intent(in)::speed,d,cb,tp,piv,arc,alen,pre,off,krot,xj,yj,tilt,mu(:),dh(:)
    integer(ik),intent(in)::nx,nz
    real(rk),intent(out)::pressure(:),h(:),fx,fy,moment,pmax
    integer(ik),intent(out)::status
    integer::nn,ix,iz,node,n1,n2,n3,n4,bw,ncol,nbc,ix_min,step
    real(rk)::r,cpv,lead,xp,dx,dz,theta,theta2,hv,he,gamma,kcoef,q,u,area,ang,pavg,dhdx,hmin_local,xhmin_local
    real(rk),allocatable::a(:,:),rhs(:),alow(:,:),pres(:)
    integer(ik),allocatable::ipiv(:),bcidx(:),nodes0(:)
    real(rk)::em(4,4),ec(4)
    integer(ik)::st
    status=RB_OK;fx=0._rk;fy=0._rk;moment=0._rk;pmax=0._rk
    nn=(int(nx)+1)*(int(nz)+1)
    if(size(mu)<nn .or. size(dh)<int(nx)+1 .or. size(pressure)<nn .or. size(h)<nn .or. any(mu(1:nn)<=0._rk))then
      status=RB_ERR_INPUT;return
    end if
    r=.5_rk*d;cpv=cb/(1._rk-pre);lead=piv-arc*off;xp=off*arc;dx=r*arc/real(nx,rk);dz=alen/real(nz,rk)
    bw=int(nz)+3;ncol=2*bw-1
    allocate(a(nn,ncol),rhs(nn),alow(nn,bw-1),pres(nn),ipiv(nn),bcidx(nn),nodes0(4))
    a=0._rk;rhs=0._rk;pres=0._rk;h=0._rk
    do ix=0,int(nx)
      theta=arc*real(ix,rk)/real(nx,rk)
      do iz=0,int(nz)
        node=ix*(int(nz)+1)+iz+1
        hv=cpv-xj*cos(lead+theta)-yj*sin(lead+theta)-pre*cpv*cos(theta-xp) &
           -(r+cb+tp)*tilt*sin(theta-xp)+dh(ix+1)
        if(hv<=1e-10_rk)then;status=RB_ERR_CONVERGENCE;return;end if
        h(node)=hv
      end do
    end do
    u=speed*r
    do ix=0,int(nx)-1
      do iz=0,int(nz)-1
        n1=ix*(int(nz)+1)+iz+1;n2=(ix+1)*(int(nz)+1)+iz+1;n3=n2+1;n4=n1+1
        he=.25_rk*(h(n1)+h(n2)+h(n3)+h(n4))
        gamma=-(1._rk/mu(n1)+1._rk/mu(n2)+1._rk/mu(n3)+1._rk/mu(n4))/48._rk
        kcoef=he**3*gamma;dhdx=(-h(n1)+h(n2)+h(n3)-h(n4))/(2._rk*dx);q=.5_rk*u*dhdx
        call rb_reynolds_q4_element(kcoef,kcoef,q,dx,dz,em,ec,st)
        if(st/=RB_OK)then;status=st;return;end if
        nodes0=[int(n1-1,ik),int(n2-1,ik),int(n3-1,ik),int(n4-1,ik)]
        call rb_assemble_q4_banded(em,ec,nodes0,int(bw,ik),a,rhs,st)
        if(st/=RB_OK)then;status=st;return;end if
      end do
    end do
    nbc=0
    do ix=0,int(nx)
      do iz=0,int(nz)
        node=ix*(int(nz)+1)+iz+1
        if(iz==0 .or. iz==int(nz) .or. ix==0 .or. ix==int(nx))then
          nbc=nbc+1;bcidx(nbc)=int(node-1,ik);pres(nbc)=0._rk
        end if
      end do
    end do
    call rb_include_pressure_bc(a,rhs,int(bw,ik),int(nbc,ik),bcidx,pres,int(nn,ik),st)
    if(st/=RB_OK)then;status=st;return;end if
    call rb_lu_factor_band(a,int(nn,ik),int(bw,ik),alow,ipiv,st)
    if(st/=RB_OK)then;status=st;return;end if
    call rb_lu_solve_band_cavitating(a,int(nn,ik),int(bw,ik),alow,ipiv,rhs,0._rk,st)
    if(st/=RB_OK)then;status=st;return;end if
    pressure(1:nn)=rhs(1:nn)

    ! ROSS regular-flooded post-solve cavitation rule.  The LU back-substitution
    ! clamp alone is not the complete authority model: pressure nodes in the
    ! divergent region downstream of h_min are explicitly zeroed when the local
    ! clearance is closing toward the next circumferential station.
    hmin_local=huge(1._rk);ix_min=0;step=int(nz)+1
    do ix=0,int(nx)
      node=ix*step+1
      if(h(node)<hmin_local)then
        hmin_local=h(node);ix_min=ix
      end if
    end do
    xhmin_local=real(ix_min,rk)*dx
    if(ix_min==0)then
      pressure(1:nn)=0._rk
    else
      do ix=0,int(nx)-1
        do iz=0,int(nz)
          node=ix*step+iz+1
          if(h(node)>h(node+step) .and. h(node)>hmin_local .and. real(ix,rk)*dx>xhmin_local)then
            pressure(node)=0._rk
          end if
        end do
      end do
    end if
    pmax=maxval(pressure(1:nn))
    do ix=0,int(nx)-1
      do iz=0,int(nz)-1
        n1=ix*(int(nz)+1)+iz+1;n2=(ix+1)*(int(nz)+1)+iz+1;n3=n2+1;n4=n1+1
        area=dx*dz
        theta=arc*real(ix,rk)/real(nx,rk)
        theta2=arc*real(ix+1,rk)/real(nx,rk)
        ! Match ROSS integrate_xz exactly: form the nodal pressure-times-angle
        ! field first, then take the Q4 element average.  Using p_avg at the
        ! element-centre angle introduces a systematic coefficient bias.
        fx=fx-area*.25_rk*(pressure(n1)*cos(lead+theta)+pressure(n4)*cos(lead+theta)+ &
                           pressure(n2)*cos(lead+theta2)+pressure(n3)*cos(lead+theta2))
        fy=fy-area*.25_rk*(pressure(n1)*sin(lead+theta)+pressure(n4)*sin(lead+theta)+ &
                           pressure(n2)*sin(lead+theta2)+pressure(n3)*sin(lead+theta2))
        moment=moment-(r+tp)*area*.25_rk*(pressure(n1)*sin(theta-xp)+pressure(n4)*sin(theta-xp)+ &
                                          pressure(n2)*sin(theta2-xp)+pressure(n3)*sin(theta2-xp))
      end do
    end do
    moment=moment-krot*tilt
  end subroutine pad_static


  subroutine pad_pert(mode,d,cb,tp,piv,arc,alen,pre,off,nx,nz,xj,yj,tilt,mu,dh,pstatic,fx,fy,moment,status)
    integer(ik),intent(in)::mode,nx,nz
    real(rk),intent(in)::d,cb,tp,piv,arc,alen,pre,off,xj,yj,tilt,mu(:),dh(:),pstatic(:)
    real(rk),intent(out)::fx,fy,moment
    integer(ik),intent(out)::status
    integer::nn,ix,iz,node,n1,n2,n3,n4,bw,ncol,nbc
    real(rk)::r,cpv,lead,xp,dx,dz,theta,theta2,hv,he,gamma,kcoef,q,area,ang,pavg
    real(rk),allocatable::h(:),a(:,:),rhs(:),alow(:,:),pres(:)
    integer(ik),allocatable::ipiv(:),bcidx(:),nodes0(:)
    real(rk)::em(4,4),ec(4)
    integer(ik)::st
    status=RB_OK;fx=0._rk;fy=0._rk;moment=0._rk
    nn=(int(nx)+1)*(int(nz)+1);r=.5_rk*d;cpv=cb/(1._rk-pre);lead=piv-arc*off;xp=off*arc
    dx=r*arc/real(nx,rk);dz=alen/real(nz,rk);bw=int(nz)+3;ncol=2*bw-1
    if(size(mu)<nn .or. size(dh)<int(nx)+1 .or. size(pstatic)<nn .or. any(mu(1:nn)<=0._rk))then
      status=RB_ERR_INPUT;return
    end if
    allocate(h(nn),a(nn,ncol),rhs(nn),alow(nn,bw-1),pres(nn),ipiv(nn),bcidx(nn),nodes0(4))
    a=0._rk;rhs=0._rk;pres=0._rk
    do ix=0,int(nx)
      theta=arc*real(ix,rk)/real(nx,rk)
      do iz=0,int(nz)
        node=ix*(int(nz)+1)+iz+1
        hv=cpv-xj*cos(lead+theta)-yj*sin(lead+theta)-pre*cpv*cos(theta-xp) &
           -(r+cb+tp)*tilt*sin(theta-xp)+dh(ix+1)
        if(hv<=1e-10_rk)then;status=RB_ERR_CONVERGENCE;return;end if
        h(node)=hv
      end do
    end do
    do ix=0,int(nx)-1
      do iz=0,int(nz)-1
        n1=ix*(int(nz)+1)+iz+1;n2=(ix+1)*(int(nz)+1)+iz+1;n3=n2+1;n4=n1+1
        he=.25_rk*(h(n1)+h(n2)+h(n3)+h(n4))
        gamma=-(1._rk/mu(n1)+1._rk/mu(n2)+1._rk/mu(n3)+1._rk/mu(n4))/48._rk;kcoef=he**3*gamma
        theta=arc*(real(ix,rk)+.5_rk)/real(nx,rk);ang=lead+theta
        select case(mode)
        case(1);q=-cos(ang)
        case(2);q=-sin(ang)
        case(3);q=-(r+tp)*sin(theta-xp)
        case default;status=RB_ERR_INPUT;return
        end select
        call rb_reynolds_q4_element(kcoef,kcoef,q,dx,dz,em,ec,st)
        if(st/=RB_OK)then;status=st;return;end if
        nodes0=[int(n1-1,ik),int(n2-1,ik),int(n3-1,ik),int(n4-1,ik)]
        call rb_assemble_q4_banded(em,ec,nodes0,int(bw,ik),a,rhs,st)
        if(st/=RB_OK)then;status=st;return;end if
      end do
    end do
    nbc=0
    do ix=0,int(nx)
      do iz=0,int(nz)
        node=ix*(int(nz)+1)+iz+1
        if(iz==0 .or. iz==int(nz) .or. ix==0 .or. ix==int(nx) .or. abs(pstatic(node))<1e-6_rk)then
          nbc=nbc+1;bcidx(nbc)=int(node-1,ik);pres(nbc)=0._rk
        end if
      end do
    end do
    call rb_include_pressure_bc(a,rhs,int(bw,ik),int(nbc,ik),bcidx,pres,int(nn,ik),st)
    if(st/=RB_OK)then;status=st;return;end if
    call rb_lu_factor_band(a,int(nn,ik),int(bw,ik),alow,ipiv,st)
    if(st/=RB_OK)then;status=st;return;end if
    call rb_lu_solve_band_signed(a,int(nn,ik),int(bw,ik),alow,ipiv,rhs,st)
    if(st/=RB_OK)then;status=st;return;end if
    do ix=0,int(nx)-1
      do iz=0,int(nz)-1
        n1=ix*(int(nz)+1)+iz+1;n2=(ix+1)*(int(nz)+1)+iz+1;n3=n2+1;n4=n1+1
        area=dx*dz
        theta=arc*real(ix,rk)/real(nx,rk)
        theta2=arc*real(ix+1,rk)/real(nx,rk)
        fx=fx+area*.25_rk*(rhs(n1)*cos(lead+theta)+rhs(n4)*cos(lead+theta)+ &
                           rhs(n2)*cos(lead+theta2)+rhs(n3)*cos(lead+theta2))
        fy=fy+area*.25_rk*(rhs(n1)*sin(lead+theta)+rhs(n4)*sin(lead+theta)+ &
                           rhs(n2)*sin(lead+theta2)+rhs(n3)*sin(lead+theta2))
        moment=moment+(r+tp)*area*.25_rk*(rhs(n1)*sin(theta-xp)+rhs(n4)*sin(theta-xp)+ &
                                          rhs(n2)*sin(theta2-xp)+rhs(n3)*sin(theta2-xp))
      end do
    end do
  end subroutine pad_pert


  subroutine plain_force(speed,d,cb,np,piv,arc,alen,pre,off,nx,nz,mu,dh,xj,yj,press,h,fx,fy,pmax,status)
    real(rk),intent(in)::speed,d,cb,piv(np),arc(np),alen(np),pre(np),off(np),mu(:,:),dh(:,:),xj,yj
    integer(ik),intent(in)::np,nx,nz
    real(rk),intent(out)::press(:,:),h(:,:),fx,fy,pmax
    integer(ik),intent(out)::status
    integer::p,nn
    real(rk)::fi,gi,mi,pm
    integer(ik)::st
    status=RB_OK;fx=0._rk;fy=0._rk;pmax=0._rk;nn=(int(nx)+1)*(int(nz)+1)
    do p=1,int(np)
      call pad_static(speed,d,cb,0._rk,piv(p),arc(p),alen(p),pre(p),off(p),0._rk,nx,nz,xj,yj,0._rk, &
                      mu(1:nn,p),dh(:,p),press(1:nn,p),h(1:nn,p),fi,gi,mi,pm,st)
      if(st/=RB_OK)then;status=st;return;end if
      fx=fx+fi;fy=fy+gi;pmax=max(pmax,pm)
    end do
  end subroutine plain_force


  subroutine plain_equilibrium(speed,fxext,fyext,d,cb,np,piv,arc,alen,pre,off,nx,nz,mu,dh,xj,yj,relax,maxit,tol, &
                               press,h,fx,fy,pmax,iterations,status)
    real(rk),intent(in)::speed,fxext,fyext,d,cb,piv(np),arc(np),alen(np),pre(np),off(np),mu(:,:),dh(:,:),relax,tol
    integer(ik),intent(in)::np,nx,nz,maxit
    real(rk),intent(inout)::xj,yj
    real(rk),intent(out)::press(:,:),h(:,:),fx,fy,pmax
    integer(ik),intent(out)::iterations,status
    real(rk)::eps,fxn,fyn,scale,fp,gp,fm,gm,pm,k11,k21,k12,k22,det,dx,dy,normd
    real(rk),allocatable::pw(:,:),hw(:,:)
    integer::nn,it
    integer(ik)::st
    nn=(int(nx)+1)*(int(nz)+1);allocate(pw(nn,np),hw(nn,np));eps=max(cb*1e-5_rk,1e-10_rk)
    scale=max(1._rk,sqrt(fxext*fxext+fyext*fyext));status=RB_OK;iterations=0_ik
    do it=1,int(maxit)
      call plain_force(speed,d,cb,np,piv,arc,alen,pre,off,nx,nz,mu,dh,xj,yj,press,h,fx,fy,pmax,st)
      if(st/=RB_OK)then;status=st;return;end if
      fxn=fx+fxext;fyn=fy+fyext;iterations=int(it,ik)
      if(sqrt(fxn*fxn+fyn*fyn)<=tol*scale)exit
      call plain_force(speed,d,cb,np,piv,arc,alen,pre,off,nx,nz,mu,dh,xj+eps,yj,pw,hw,fp,gp,pm,st)
      if(st/=RB_OK)then;status=st;return;end if
      call plain_force(speed,d,cb,np,piv,arc,alen,pre,off,nx,nz,mu,dh,xj-eps,yj,pw,hw,fm,gm,pm,st)
      if(st/=RB_OK)then;status=st;return;end if
      k11=-(fp-fm)/(2*eps);k21=-(gp-gm)/(2*eps)
      call plain_force(speed,d,cb,np,piv,arc,alen,pre,off,nx,nz,mu,dh,xj,yj+eps,pw,hw,fp,gp,pm,st)
      if(st/=RB_OK)then;status=st;return;end if
      call plain_force(speed,d,cb,np,piv,arc,alen,pre,off,nx,nz,mu,dh,xj,yj-eps,pw,hw,fm,gm,pm,st)
      if(st/=RB_OK)then;status=st;return;end if
      k12=-(fp-fm)/(2*eps);k22=-(gp-gm)/(2*eps);det=k11*k22-k12*k21
      if(abs(det)<=1e-14_rk*max(1._rk,abs(k11*k22),abs(k12*k21)))then;status=RB_ERR_CONVERGENCE;return;end if
      dx=(k22*fxn-k12*fyn)/det;dy=(-k21*fxn+k11*fyn)/det;normd=sqrt(dx*dx+dy*dy)
      if(normd>.2_rk*cb)then;dx=dx*.2_rk*cb/normd;dy=dy*.2_rk*cb/normd;end if
      xj=xj+relax*dx;yj=yj+relax*dy
      normd=sqrt(xj*xj+yj*yj)
      if(normd>=.995_rk*cb)then;xj=xj*.995_rk*cb/normd;yj=yj*.995_rk*cb/normd;end if
    end do
    if(sqrt((fx+fxext)**2+(fy+fyext)**2)>tol*scale)status=RB_ERR_CONVERGENCE
  end subroutine plain_equilibrium


  subroutine plain_coefficients(speed,d,cb,np,piv,arc,alen,pre,off,nx,nz,mu,dh,xj,yj,pstatic,k,c,status)
    real(rk),intent(in)::speed,d,cb,piv(np),arc(np),alen(np),pre(np),off(np),mu(:,:),dh(:,:),xj,yj,pstatic(:,:)
    integer(ik),intent(in)::np,nx,nz
    real(rk),intent(out)::k(2,2),c(2,2)
    integer(ik),intent(out)::status
    integer::nn,p
    real(rk)::eps,fp,gp,fm,gm,pm,mi
    real(rk),allocatable::pw(:,:),hw(:,:)
    integer(ik)::st
    nn=(int(nx)+1)*(int(nz)+1);allocate(pw(nn,np),hw(nn,np));eps=max(cb*1e-5_rk,1e-10_rk);status=RB_OK;k=0._rk;c=0._rk
    call plain_force(speed,d,cb,np,piv,arc,alen,pre,off,nx,nz,mu,dh,xj+eps,yj,pw,hw,fp,gp,pm,st);if(st/=RB_OK)goto 900
    call plain_force(speed,d,cb,np,piv,arc,alen,pre,off,nx,nz,mu,dh,xj-eps,yj,pw,hw,fm,gm,pm,st);if(st/=RB_OK)goto 900
    k(1,1)=-(fp-fm)/(2*eps);k(2,1)=-(gp-gm)/(2*eps)
    call plain_force(speed,d,cb,np,piv,arc,alen,pre,off,nx,nz,mu,dh,xj,yj+eps,pw,hw,fp,gp,pm,st);if(st/=RB_OK)goto 900
    call plain_force(speed,d,cb,np,piv,arc,alen,pre,off,nx,nz,mu,dh,xj,yj-eps,pw,hw,fm,gm,pm,st);if(st/=RB_OK)goto 900
    k(1,2)=-(fp-fm)/(2*eps);k(2,2)=-(gp-gm)/(2*eps)
    do p=1,int(np)
      call pad_pert(1_ik,d,cb,0._rk,piv(p),arc(p),alen(p),pre(p),off(p),nx,nz,xj,yj,0._rk,mu(:,p),dh(:,p), &
                    pstatic(:,p),fp,gp,mi,st);if(st/=RB_OK)goto 900;c(1,1)=c(1,1)+fp;c(2,1)=c(2,1)+gp
      call pad_pert(2_ik,d,cb,0._rk,piv(p),arc(p),alen(p),pre(p),off(p),nx,nz,xj,yj,0._rk,mu(:,p),dh(:,p), &
                    pstatic(:,p),fp,gp,mi,st);if(st/=RB_OK)goto 900;c(1,2)=c(1,2)+fp;c(2,2)=c(2,2)+gp
    end do
    return
900 status=st
  end subroutine plain_coefficients


  subroutine tp_equilibrate_fields(speed,d,cb,tp,np,piv,arc,alen,pre,off,krot,nx,nz,mu,dh,xj,yj,tilt,press,h,mom,fx,fy,pmax,status)
    real(rk),intent(in)::speed,d,cb,tp,piv(np),arc(np),alen(np),pre(np),off(np),krot(np),mu(:,:),dh(:,:),xj,yj
    integer(ik),intent(in)::np,nx,nz
    real(rk),intent(out)::tilt(np),press(:,:),h(:,:),mom(np),fx,fy,pmax
    integer(ik),intent(out)::status
    integer::p,iter,nn
    real(rk)::r,lead,xp,rtilt,lo,hi,t,fi,gi,mi,pm,s1,s2,h1,h2
    integer(ik)::st
    status=RB_OK;fx=0._rk;fy=0._rk;pmax=0._rk;nn=(int(nx)+1)*(int(nz)+1);r=.5_rk*d
    do p=1,int(np)
      lead=piv(p)-arc(p)*off(p);xp=off(p)*arc(p);rtilt=r+cb+tp
      s1=sin(-xp);s2=sin(arc(p)-xp)
      if(abs(s1)<1e-12_rk .or. abs(s2)<1e-12_rk)then;status=RB_ERR_INPUT;return;end if
      h1=cb/(1._rk-pre(p))-xj*cos(lead)-yj*sin(lead)-pre(p)*(cb/(1._rk-pre(p)))*cos(-xp)+dh(1,p)
      h2=cb/(1._rk-pre(p))-xj*cos(lead+arc(p))-yj*sin(lead+arc(p))-pre(p)*(cb/(1._rk-pre(p)))*cos(arc(p)-xp)+dh(int(nx)+1,p)
      lo=h1/(rtilt*s1);hi=h2/(rtilt*s2);if(lo>hi)then;t=lo;lo=hi;hi=t;end if
      lo=lo-1e-4_rk;hi=hi+1e-4_rk
      do iter=1,120
        t=.5_rk*(lo+hi)
        call pad_static(speed,d,cb,tp,piv(p),arc(p),alen(p),pre(p),off(p),krot(p),nx,nz,xj,yj,t,mu(:,p),dh(:,p), &
                        press(1:nn,p),h(1:nn,p),fi,gi,mi,pm,st)
        if(st/=RB_OK)then
          if(t>0._rk)then;hi=t;else;lo=t;end if
          cycle
        end if
        if(abs(mi)<=1e-6_rk*max(1._rk,abs(krot(p)*max(abs(t),1e-9_rk)),abs(fi*r)))exit
        if(mi>=0._rk)then;lo=t;else;hi=t;end if
      end do
      if(st/=RB_OK)then;status=st;return;end if
      tilt(p)=t;mom(p)=mi;fx=fx+fi;fy=fy+gi;pmax=max(pmax,pm)
    end do
  end subroutine tp_equilibrate_fields


  subroutine tp_force_eq(speed,d,cb,tp,np,piv,arc,alen,pre,off,krot,nx,nz,mu,dh,xj,yj,tilt,fx,fy,pmax,status)
    real(rk),intent(in)::speed,d,cb,tp,piv(np),arc(np),alen(np),pre(np),off(np),krot(np),mu(:,:),dh(:,:),xj,yj
    integer(ik),intent(in)::np,nx,nz
    real(rk),intent(out)::tilt(np),fx,fy,pmax
    integer(ik),intent(out)::status
    integer::nn
    real(rk),allocatable::p(:,:),h(:,:),m(:)
    nn=(int(nx)+1)*(int(nz)+1);allocate(p(nn,np),h(nn,np),m(np))
    call tp_equilibrate_fields(speed,d,cb,tp,np,piv,arc,alen,pre,off,krot,nx,nz,mu,dh,xj,yj,tilt,p,h,m,fx,fy,pmax,status)
  end subroutine tp_force_eq


  subroutine tp_journal_equilibrium(speed,fxext,fyext,d,cb,tp,np,piv,arc,alen,pre,off,krot,nx,nz,mu,dh,xj,yj, &
                                    relax,maxit,tol,tilt,press,h,mom,fx,fy,pmax,iterations,status)
    real(rk),intent(in)::speed,fxext,fyext,d,cb,tp,piv(np),arc(np),alen(np),pre(np),off(np),krot(np),mu(:,:),dh(:,:),relax,tol
    integer(ik),intent(in)::np,nx,nz,maxit
    real(rk),intent(inout)::xj,yj
    real(rk),intent(out)::tilt(np),press(:,:),h(:,:),mom(np),fx,fy,pmax
    integer(ik),intent(out)::iterations,status
    integer::it
    real(rk)::eps,fxn,fyn,scale,fp,gp,fm,gm,pm,k11,k21,k12,k22,det,dx,dy,normd
    real(rk),allocatable::tw(:)
    integer(ik)::st
    allocate(tw(np));eps=max(cb*1e-5_rk,1e-10_rk);scale=max(1._rk,sqrt(fxext**2+fyext**2));status=RB_OK
    do it=1,int(maxit)
      call tp_equilibrate_fields(speed,d,cb,tp,np,piv,arc,alen,pre,off,krot,nx,nz,mu,dh,xj,yj,tilt,press,h,mom,fx,fy,pmax,st)
      if(st/=RB_OK)then;status=st;return;end if
      fxn=fx+fxext;fyn=fy+fyext;iterations=int(it,ik)
      if(sqrt(fxn**2+fyn**2)<=tol*scale .and. it>1)exit
      call tp_force_eq(speed,d,cb,tp,np,piv,arc,alen,pre,off,krot,nx,nz,mu,dh,xj+eps,yj,tw,fp,gp,pm,st);if(st/=RB_OK)goto 900
      call tp_force_eq(speed,d,cb,tp,np,piv,arc,alen,pre,off,krot,nx,nz,mu,dh,xj-eps,yj,tw,fm,gm,pm,st);if(st/=RB_OK)goto 900
      k11=-(fp-fm)/(2*eps);k21=-(gp-gm)/(2*eps)
      call tp_force_eq(speed,d,cb,tp,np,piv,arc,alen,pre,off,krot,nx,nz,mu,dh,xj,yj+eps,tw,fp,gp,pm,st);if(st/=RB_OK)goto 900
      call tp_force_eq(speed,d,cb,tp,np,piv,arc,alen,pre,off,krot,nx,nz,mu,dh,xj,yj-eps,tw,fm,gm,pm,st);if(st/=RB_OK)goto 900
      k12=-(fp-fm)/(2*eps);k22=-(gp-gm)/(2*eps);det=k11*k22-k12*k21
      if(abs(det)<=1e-14_rk*max(1._rk,abs(k11*k22),abs(k12*k21)))then;status=RB_ERR_CONVERGENCE;return;end if
      dx=(k22*fxn-k12*fyn)/det;dy=(-k21*fxn+k11*fyn)/det;normd=sqrt(dx*dx+dy*dy)
      if(normd>.2_rk*cb)then;dx=dx*.2_rk*cb/normd;dy=dy*.2_rk*cb/normd;end if
      xj=xj+relax*dx;yj=yj+relax*dy;normd=sqrt(xj*xj+yj*yj)
      if(normd>=.995_rk*cb)then;xj=xj*.995_rk*cb/normd;yj=yj*.995_rk*cb/normd;end if
    end do
    if(sqrt((fx+fxext)**2+(fy+fyext)**2)>tol*scale)status=RB_ERR_CONVERGENCE
    return
900 status=st
  end subroutine tp_journal_equilibrium


  subroutine tp_fixedtilt_fields(speed,d,cb,tp,np,piv,arc,alen,pre,off,krot,nx,nz,mu,dh,xj,yj,tilt,press,h,fx,fy,mom,pmax,status)
    real(rk),intent(in)::speed,d,cb,tp,piv(np),arc(np),alen(np),pre(np),off(np),krot(np),mu(:,:),dh(:,:),xj,yj,tilt(np)
    integer(ik),intent(in)::np,nx,nz
    real(rk),intent(out)::press(:,:),h(:,:),fx,fy,mom(np),pmax
    integer(ik),intent(out)::status
    integer::p,nn
    real(rk)::fi,gi,mi,pm
    integer(ik)::st
    nn=(int(nx)+1)*(int(nz)+1);fx=0._rk;fy=0._rk;pmax=0._rk;status=RB_OK
    do p=1,int(np)
      call pad_static(speed,d,cb,tp,piv(p),arc(p),alen(p),pre(p),off(p),krot(p),nx,nz,xj,yj,tilt(p),mu(:,p),dh(:,p), &
                      press(1:nn,p),h(1:nn,p),fi,gi,mi,pm,st)
      if(st/=RB_OK)then;status=st;return;end if
      fx=fx+fi;fy=fy+gi;mom(p)=mi;pmax=max(pmax,pm)
    end do
  end subroutine tp_fixedtilt_fields


  subroutine tp_coefficients(speed,omega,d,cb,tp,pad_density,np,piv,arc,alen,pre,off,krot,nx,nz,mu,dh,xj,yj,tilt,pstatic,kred,cred,status)
    real(rk),intent(in)::speed,omega,d,cb,tp,pad_density,piv(np),arc(np),alen(np),pre(np),off(np),krot(np)
    real(rk),intent(in)::mu(:,:),dh(:,:),xj,yj,tilt(np),pstatic(:,:)
    integer(ik),intent(in)::np,nx,nz
    real(rk),intent(out)::kred(2,2),cred(2,2)
    integer(ik),intent(out)::status
    integer::nn,p
    real(rk)::eps,epst,fp,gp,fm,gm,pm,mp,mm
    real(rk)::kj(2,2),cj(2,2)
    real(rk),allocatable::pw(:,:),hw(:,:),mom(:),vp(:),vm(:),kdx(:),kdy(:),kxd(:),kyd(:),kdd(:)
    real(rk),allocatable::cdx(:),cdy(:),cxd(:),cyd(:),cdd(:),plen(:),ip(:)
    integer(ik)::st
    nn=(int(nx)+1)*(int(nz)+1);eps=max(cb*1e-5_rk,1e-10_rk);status=RB_OK
    allocate(pw(nn,np),hw(nn,np),mom(np),vp(np),vm(np),kdx(np),kdy(np),kxd(np),kyd(np),kdd(np))
    allocate(cdx(np),cdy(np),cxd(np),cyd(np),cdd(np),plen(np),ip(np));plen=.5_rk*d*arc

    call tp_fixedtilt_fields(speed,d,cb,tp,np,piv,arc,alen,pre,off,krot,nx,nz,mu,dh,xj+eps,yj,tilt,pw,hw,fp,gp,mom,pm,st);if(st/=RB_OK)goto 900;vp=mom
    call tp_fixedtilt_fields(speed,d,cb,tp,np,piv,arc,alen,pre,off,krot,nx,nz,mu,dh,xj-eps,yj,tilt,pw,hw,fm,gm,mom,pm,st);if(st/=RB_OK)goto 900;vm=mom
    kj(1,1)=-(fp-fm)/(2*eps);kj(2,1)=-(gp-gm)/(2*eps);kdx=-(vp-vm)/(2*eps)
    call tp_fixedtilt_fields(speed,d,cb,tp,np,piv,arc,alen,pre,off,krot,nx,nz,mu,dh,xj,yj+eps,tilt,pw,hw,fp,gp,mom,pm,st);if(st/=RB_OK)goto 900;vp=mom
    call tp_fixedtilt_fields(speed,d,cb,tp,np,piv,arc,alen,pre,off,krot,nx,nz,mu,dh,xj,yj-eps,tilt,pw,hw,fm,gm,mom,pm,st);if(st/=RB_OK)goto 900;vm=mom
    kj(1,2)=-(fp-fm)/(2*eps);kj(2,2)=-(gp-gm)/(2*eps);kdy=-(vp-vm)/(2*eps)
    do p=1,int(np)
      epst=max(1e-8_rk,abs(tilt(p))*1e-4_rk);vp=tilt;vm=tilt;vp(p)=vp(p)+epst;vm(p)=vm(p)-epst
      call pad_static(speed,d,cb,tp,piv(p),arc(p),alen(p),pre(p),off(p),krot(p),nx,nz,xj,yj,vp(p),mu(:,p),dh(:,p), &
                      pw(:,p),hw(:,p),fp,gp,mp,pm,st);if(st/=RB_OK)goto 900
      call pad_static(speed,d,cb,tp,piv(p),arc(p),alen(p),pre(p),off(p),krot(p),nx,nz,xj,yj,vm(p),mu(:,p),dh(:,p), &
                      pw(:,p),hw(:,p),fm,gm,mm,pm,st);if(st/=RB_OK)goto 900
      kxd(p)=-(fp-fm)/(2*epst);kyd(p)=-(gp-gm)/(2*epst);kdd(p)=-(mp-mm)/(2*epst)-krot(p)
    end do
    cj=0._rk;cdx=0._rk;cdy=0._rk;cxd=0._rk;cyd=0._rk;cdd=0._rk
    do p=1,int(np)
      call pad_pert(1_ik,d,cb,tp,piv(p),arc(p),alen(p),pre(p),off(p),nx,nz,xj,yj,tilt(p),mu(:,p),dh(:,p),pstatic(:,p),fp,gp,mp,st);if(st/=RB_OK)goto 900
      cj(1,1)=cj(1,1)+fp;cj(2,1)=cj(2,1)+gp;cdx(p)=mp
      call pad_pert(2_ik,d,cb,tp,piv(p),arc(p),alen(p),pre(p),off(p),nx,nz,xj,yj,tilt(p),mu(:,p),dh(:,p),pstatic(:,p),fp,gp,mp,st);if(st/=RB_OK)goto 900
      cj(1,2)=cj(1,2)+fp;cj(2,2)=cj(2,2)+gp;cdy(p)=mp
      call pad_pert(3_ik,d,cb,tp,piv(p),arc(p),alen(p),pre(p),off(p),nx,nz,xj,yj,tilt(p),mu(:,p),dh(:,p),pstatic(:,p),fp,gp,mp,st);if(st/=RB_OK)goto 900
      cxd(p)=fp;cyd(p)=gp;cdd(p)=mp
    end do
    call rb_dynamic_reduce_tilts(np,kj,cj,kdx,kdy,kxd,kyd,kdd,cdx,cdy,cxd,cyd,cdd,plen,tp,alen,pad_density,omega, &
                                 krot,kred,cred,ip,st)
    if(st/=RB_OK)goto 900
    return
900 status=st
  end subroutine tp_coefficients

end module rb_native_multiphysics
