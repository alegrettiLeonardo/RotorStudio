module rb_thermal
  use rb_kinds, only: rk, ik
  use rb_status, only: RB_OK, RB_ERR_INPUT, RB_ERR_CONVERGENCE
  use rb_reynolds_banded, only: rb_assemble_q4_banded, rb_include_pressure_bc, &
                                rb_lu_factor_band, rb_lu_solve_band_signed
  implicit none(type, external)
  private

  integer(ik), parameter, public :: RB_THERMAL_ISOVISCOUS = 0_ik
  integer(ik), parameter, public :: RB_THERMAL_ADIABATIC = 1_ik
  integer(ik), parameter, public :: RB_THERMAL_FULL = 2_ik

  public :: rb_viscosity_temperature
  public :: rb_pressure_gradients_smooth
  public :: rb_thermal_adiabatic_pad
  public :: rb_thermal_full_pad

contains

  pure elemental real(rk) function rb_mu_of_t(mu1,mu2,t1,t2,t) result(mu)
    real(rk), intent(in) :: mu1,mu2,t1,t2,t
    real(rk) :: beta
    beta=log(mu2/mu1)/(t2-t1)
    mu=mu1*exp(beta*(t-t1))
  end function rb_mu_of_t

  subroutine rb_viscosity_temperature(mu1,mu2,t1,t2,temp,mu,status)
    real(rk), intent(in) :: mu1,mu2,t1,t2,temp(:)
    real(rk), intent(out) :: mu(:)
    integer(ik), intent(out) :: status
    status=RB_OK
    if(mu1<=0._rk .or. mu2<=0._rk .or. abs(t2-t1)<=tiny(1._rk) .or. size(mu)<size(temp))then
      status=RB_ERR_INPUT; return
    end if
    mu(1:size(temp))=rb_mu_of_t(mu1,mu2,t1,t2,temp)
  end subroutine rb_viscosity_temperature

  subroutine rb_pressure_gradients_smooth(nx,nz,pad_length,axial_length,pressure,dpdx,dpdz,status)
    integer(ik),intent(in)::nx,nz
    real(rk),intent(in)::pad_length,axial_length,pressure(:)
    real(rk),intent(out)::dpdx(:),dpdz(:)
    integer(ik),intent(out)::status
    integer::ix,iz,n,step,nn
    real(rk)::dx,dz
    status=RB_OK
    nn=(int(nx)+1)*(int(nz)+1)
    if(nx<2 .or. nz<2 .or. pad_length<=0._rk .or. axial_length<=0._rk .or. &
       size(pressure)<nn .or. size(dpdx)<nn .or. size(dpdz)<nn)then
      status=RB_ERR_INPUT; return
    end if
    dx=pad_length/real(nx,rk); dz=axial_length/real(nz,rk); step=int(nz)+1
    do ix=0,int(nx)
      do iz=0,int(nz)
        n=ix*step+iz+1
        if(ix<=int(nx)-2)then
          dpdx(n)=(-3._rk*pressure(n)+4._rk*pressure(n+step)-pressure(n+2*step))/(2._rk*dx)
        else
          dpdx(n)=(3._rk*pressure(n)-4._rk*pressure(n-step)+pressure(n-2*step))/(2._rk*dx)
        end if
        if(iz<int(nz)/2)then
          dpdz(n)=(-3._rk*pressure(n)+4._rk*pressure(n+1)-pressure(n+2))/(2._rk*dz)
        else if(iz>int(nz)/2)then
          dpdz(n)=(3._rk*pressure(n)-4._rk*pressure(n-1)+pressure(n-2))/(2._rk*dz)
        else
          dpdz(n)=(pressure(n+1)-pressure(n-1))/(2._rk*dz)
        end if
      end do
    end do
  end subroutine rb_pressure_gradients_smooth

  subroutine rb_thermal_adiabatic_pad(nx,nz,pad_length,axial_length,speed_surface,h,pressure,mu_nodes, &
                                      density,cp,conduct,temp_inlet,relax_t,temp_old,mu1,mu2,t1,t2, &
                                      temp_new,mu_new,temp_max,temp_outlet,rms_temp,status)
    integer(ik),intent(in)::nx,nz
    real(rk),intent(in)::pad_length,axial_length,speed_surface,h(:),pressure(:),mu_nodes(:)
    real(rk),intent(in)::density,cp,conduct,temp_inlet,relax_t,temp_old(:),mu1,mu2,t1,t2
    real(rk),intent(out)::temp_new(:),mu_new(:),temp_max,temp_outlet,rms_temp
    integer(ik),intent(out)::status
    integer::nn,ix,iz,n,n1,n2,n3,n4,bw,ncol,nbc,e,i
    real(rk)::dx,dz,he,mue,fluxx,fluxz,diss,kx,kz,mx,mz,q,avg_old,avg_raw,rt
    real(rk),allocatable::dpdx(:),dpdz(:),kx_n(:),kz_n(:),mx_n(:),mz_n(:),q_n(:)
    real(rk),allocatable::a(:,:),rhs(:),alow(:,:),pres(:),raw(:)
    integer(ik),allocatable::ipiv(:),bcidx(:),nodes0(:)
    real(rk)::em(4,4),ec(4)
    integer(ik)::st

    status=RB_OK; temp_max=0._rk; temp_outlet=0._rk; rms_temp=0._rk
    nn=(int(nx)+1)*(int(nz)+1)
    if(nx<2 .or. nz<2 .or. pad_length<=0._rk .or. axial_length<=0._rk .or. speed_surface<=0._rk .or. &
       density<=0._rk .or. cp<=0._rk .or. conduct<=0._rk .or. relax_t<=0._rk .or. relax_t>1._rk .or. &
       mu1<=0._rk .or. mu2<=0._rk .or. abs(t2-t1)<=tiny(1._rk) .or. &
       size(h)<nn .or. size(pressure)<nn .or. size(mu_nodes)<nn .or. size(temp_old)<nn .or. &
       size(temp_new)<nn .or. size(mu_new)<nn)then
      status=RB_ERR_INPUT; return
    end if
    if(any(h(1:nn)<=0._rk) .or. any(mu_nodes(1:nn)<=0._rk))then
      status=RB_ERR_INPUT; return
    end if

    dx=pad_length/real(nx,rk); dz=axial_length/real(nz,rk)
    bw=int(nz)+3; ncol=2*bw-1
    allocate(dpdx(nn),dpdz(nn),kx_n(nn),kz_n(nn),mx_n(nn),mz_n(nn),q_n(nn))
    allocate(a(nn,ncol),rhs(nn),alow(nn,bw-1),ipiv(nn),bcidx(nn),pres(nn),raw(nn),nodes0(4))
    call rb_pressure_gradients_smooth(nx,nz,pad_length,axial_length,pressure,dpdx,dpdz,st)
    if(st/=RB_OK)then;status=st;return;end if

    do n=1,nn
      he=h(n); mue=mu_nodes(n)
      fluxx=.5_rk*speed_surface*he-dpdx(n)*he**3/(12._rk*mue)
      fluxz=-dpdz(n)*he**3/(12._rk*mue)
      diss=mue*speed_surface**2/he+(dpdx(n)**2+dpdz(n)**2)*he**3/(12._rk*mue)
      kx_n(n)=-conduct; kz_n(n)=-conduct
      mx_n(n)=density*cp*fluxx/he
      mz_n(n)=density*cp*fluxz/he
      q_n(n)=-diss/he
    end do

    a=0._rk;rhs=0._rk;pres=0._rk
    do ix=0,int(nx)-1
      do iz=0,int(nz)-1
        n1=ix*(int(nz)+1)+iz+1; n2=(ix+1)*(int(nz)+1)+iz+1; n3=n2+1; n4=n1+1
        kx=.25_rk*(kx_n(n1)+kx_n(n2)+kx_n(n3)+kx_n(n4))
        kz=.25_rk*(kz_n(n1)+kz_n(n2)+kz_n(n3)+kz_n(n4))
        mx=.25_rk*(mx_n(n1)+mx_n(n2)+mx_n(n3)+mx_n(n4))
        mz=.25_rk*(mz_n(n1)+mz_n(n2)+mz_n(n3)+mz_n(n4))
        q =.25_rk*(q_n(n1)+q_n(n2)+q_n(n3)+q_n(n4))
        call rb_element_adiabatic(kx,kz,mx,mz,q,dx,dz,em,ec)
        nodes0=[int(n1-1,ik),int(n2-1,ik),int(n3-1,ik),int(n4-1,ik)]
        call rb_assemble_q4_banded(em,ec,nodes0,int(bw,ik),a,rhs,st)
        if(st/=RB_OK)then;status=st;return;end if
      end do
    end do

    nbc=0
    do iz=0,int(nz)
      n=iz+1; nbc=nbc+1; bcidx(nbc)=int(n-1,ik); pres(nbc)=temp_inlet
    end do
    call rb_include_pressure_bc(a,rhs,int(bw,ik),int(nbc,ik),bcidx,pres,int(nn,ik),st)
    if(st/=RB_OK)then;status=st;return;end if
    call rb_lu_factor_band(a,int(nn,ik),int(bw,ik),alow,ipiv,st)
    if(st/=RB_OK)then;status=st;return;end if
    call rb_lu_solve_band_signed(a,int(nn,ik),int(bw,ik),alow,ipiv,rhs,st)
    if(st/=RB_OK)then;status=st;return;end if
    raw=rhs

    avg_old=sum(temp_old(1:nn))/real(nn,rk); avg_raw=sum(raw)/real(nn,rk)
    if(abs(avg_raw-avg_old)>10._rk)then
      rt=min(relax_t,10._rk/abs(avg_raw-avg_old))
    else
      rt=relax_t
    end if
    temp_new(1:nn)=rt*raw+(1._rk-rt)*temp_old(1:nn)
    rms_temp=sqrt(sum((temp_new(1:nn)-temp_old(1:nn))**2)/real(nn,rk))
    temp_max=maxval(temp_new(1:nn))
    do iz=0,int(nz)
      n=int(nx)*(int(nz)+1)+iz+1; temp_outlet=temp_outlet+temp_new(n)
    end do
    temp_outlet=temp_outlet/real(int(nz)+1,rk)
    mu_new(1:nn)=rb_mu_of_t(mu1,mu2,t1,t2,temp_new(1:nn))
  end subroutine rb_thermal_adiabatic_pad

  subroutine rb_element_adiabatic(kx,kz,mx,mz,q,l,w,e,f)
    real(rk),intent(in)::kx,kz,mx,mz,q,l,w
    real(rk),intent(out)::e(4,4),f(4)
    real(rk)::kxw,kzl,mxw,mzl
    kxw=kx*w; kzl=kz*l; mxw=mx*w; mzl=mz*l
    e(1,1)= kxw/(3*l)+kzl/(3*w)+mxw/6+mzl/6
    e(1,2)=-kxw/(3*l)+kzl/(6*w)-mxw/6+mzl/12
    e(1,3)=-kxw/(6*l)-kzl/(6*w)-mxw/12-mzl/12
    e(1,4)= kxw/(6*l)-kzl/(3*w)+mxw/12-mzl/6
    e(2,1)=-kxw/(3*l)+kzl/(6*w)+mxw/6+mzl/12
    e(2,2)= kxw/(3*l)+kzl/(3*w)-mxw/6+mzl/6
    e(2,3)= kxw/(6*l)-kzl/(3*w)-mxw/12-mzl/6
    e(2,4)=-kxw/(6*l)-kzl/(6*w)+mxw/12-mzl/12
    e(3,1)=-kxw/(6*l)-kzl/(6*w)+mxw/12+mzl/12
    e(3,2)= kxw/(6*l)-kzl/(3*w)-mxw/12+mzl/6
    e(3,3)= kxw/(3*l)+kzl/(3*w)-mxw/6-mzl/6
    e(3,4)=-kxw/(3*l)+kzl/(6*w)+mxw/6-mzl/12
    e(4,1)= kxw/(6*l)-kzl/(3*w)+mxw/12+mzl/6
    e(4,2)=-kxw/(6*l)-kzl/(6*w)-mxw/12+mzl/12
    e(4,3)=-kxw/(3*l)+kzl/(6*w)-mxw/6-mzl/12
    e(4,4)= kxw/(3*l)+kzl/(3*w)+mxw/6-mzl/6
    f=q*l*w/4._rk
  end subroutine rb_element_adiabatic

  subroutine rb_thermal_full_pad(nx,nz,ny_pad,ny_film,pad_length,axial_length,pad_thickness,speed_surface,h,pressure, &
                                 mu_nodes,density,cp,lube_conduct,pad_conduct,temp_inlet,temp_journal,temp_ambient, &
                                 convec_edges,convec_back,relax_t,temp_old,mu1,mu2,t1,t2,temp_new,mu_center, &
                                 temp_max,temp_outlet,q_in,q_out,rms_temp,status,g_reynolds)
    integer(ik),intent(in)::nx,nz,ny_pad,ny_film
    real(rk),intent(in)::pad_length,axial_length,pad_thickness,speed_surface,h(:),pressure(:),mu_nodes(:)
    real(rk),intent(in)::density,cp,lube_conduct,pad_conduct,temp_inlet,temp_journal,temp_ambient
    real(rk),intent(in)::convec_edges,convec_back,relax_t,temp_old(:),mu1,mu2,t1,t2
    real(rk),intent(out)::temp_new(:),mu_center(:),temp_max,temp_outlet,q_in,q_out,rms_temp
    integer(ik),intent(out)::status
    real(rk),intent(out),optional::g_reynolds(:)
    integer::nr,ny,nne,ix,iy,iz,n,n1,n2,n3,n4,bw,ncol,nbc,nnr,center,jf,ix_min
    real(rk)::dx,dz,eta,yrel,hx,mu,u,v,dudy,dwdy,avg_u,avg_v,avg_diss,dhdx
    real(rk)::kx,ky,mx,my,pe,q,rt,avg_old,avg_raw,xi1h,xi2h,ratio,deta,gamma_eq,g_eq
    real(rk)::qrad,qax,turad,tuax,wz,hmin_local
    real(rk),allocatable::x(:),y(:),kx_n(:),ky_n(:),mx_n(:),my_n(:),p_n(:),q_n(:)
    real(rk),allocatable::mur(:),invr(:),cum1(:),cum2(:),igam(:)
    real(rk),allocatable::dpdx(:),dpdz(:),a(:,:),rhs(:),alow(:,:),pres(:),raw(:)
    integer(ik),allocatable::ipiv(:),bcidx(:),nodes0(:)
    real(rk)::em(4,4),ec(4)
    integer(ik)::st

    status=RB_OK;temp_max=0._rk;temp_outlet=0._rk;q_in=0._rk;q_out=0._rk;rms_temp=0._rk
    nnr=(int(nx)+1)*(int(nz)+1); ny=int(ny_pad)+int(ny_film)+1; nne=(int(nx)+1)*ny
    if(nx<2 .or. nz<2 .or. ny_pad<1 .or. ny_film<2 .or. pad_length<=0._rk .or. axial_length<=0._rk .or. &
       pad_thickness<=0._rk .or. speed_surface<=0._rk .or. density<=0._rk .or. cp<=0._rk .or. &
       lube_conduct<=0._rk .or. pad_conduct<=0._rk .or. relax_t<=0._rk .or. relax_t>1._rk .or. &
       size(h)<nnr .or. size(pressure)<nnr .or. size(mu_nodes)<nnr .or. size(temp_old)<nne .or. &
       size(temp_new)<nne .or. size(mu_center)<nnr)then
      status=RB_ERR_INPUT;return
    end if
    if(present(g_reynolds))then
      if(size(g_reynolds)<nnr)then;status=RB_ERR_INPUT;return;end if
    end if

    dx=pad_length/real(nx,rk);dz=axial_length/real(nz,rk);center=int(nz)/2
    allocate(dpdx(nnr),dpdz(nnr))
    call rb_pressure_gradients_smooth(nx,nz,pad_length,axial_length,pressure,dpdx,dpdz,st)
    if(st/=RB_OK)then;status=st;return;end if

    allocate(x(nne),y(nne),kx_n(nne),ky_n(nne),mx_n(nne),my_n(nne),p_n(nne),q_n(nne))
    allocate(mur(int(ny_film)+1),invr(int(ny_film)+1),cum1(int(ny_film)+1), &
             cum2(int(ny_film)+1),igam(int(ny_film)+1))
    do ix=0,int(nx)
      n=ix*(int(nz)+1)+center+1;hx=h(n)
      if(ix==0)then
        dhdx=(h((ix+1)*(int(nz)+1)+center+1)-hx)/dx
      else if(ix==int(nx))then
        dhdx=(hx-h((ix-1)*(int(nz)+1)+center+1))/dx
      else
        dhdx=(h((ix+1)*(int(nz)+1)+center+1)-h((ix-1)*(int(nz)+1)+center+1))/(2._rk*dx)
      end if
      ! ROSS full-THD uses the complete through-film viscosity profile in
      ! velocity, shear and dissipation.  Build the dimensional Xi1/Xi2
      ! integrals from the previous relaxed temperature field before solving
      ! the next energy iterate.
      do jf=0,int(ny_film)
        mur(jf+1)=max(rb_mu_of_t(mu1,mu2,t1,t2, &
             temp_new(ix*ny+int(ny_pad)+jf+1)),tiny(1._rk))
        invr(jf+1)=1._rk/mur(jf+1)
      end do
      cum1=0._rk;cum2=0._rk
      do jf=1,int(ny_film)
        yrel=hx*real(jf,rk)/real(ny_film,rk)
        deta=hx/real(ny_film,rk)
        cum1(jf+1)=cum1(jf)+.5_rk*deta*(invr(jf)+invr(jf+1))
        cum2(jf+1)=cum2(jf)+.5_rk*deta*( &
             hx*real(jf-1,rk)/real(ny_film,rk)*invr(jf)+yrel*invr(jf+1))
      end do
      xi1h=max(cum1(int(ny_film)+1),tiny(1._rk))
      xi2h=cum2(int(ny_film)+1);ratio=xi2h/xi1h

      do iy=0,ny-1
        n=ix*ny+iy+1;x(n)=real(ix,rk)*dx
        if(iy<=int(ny_pad))then
          y(n)=pad_thickness*real(iy,rk)/real(ny_pad,rk)
        else
          eta=real(iy-int(ny_pad),rk)/real(ny_film,rk)
          y(n)=pad_thickness+eta*hx
        end if

        if(iy<int(ny_pad))then
          kx_n(n)=-pad_conduct;ky_n(n)=-pad_conduct;mx_n(n)=0._rk;my_n(n)=0._rk;p_n(n)=0._rk;q_n(n)=0._rk
        else
          eta=max(0._rk,min(1._rk,(y(n)-pad_thickness)/hx));yrel=eta*hx
          jf=max(0,min(int(ny_film),iy-int(ny_pad)))
          mu=mur(jf+1)
          avg_u=0._rk;avg_v=0._rk;avg_diss=0._rk
          do iz=0,int(nz)
            nr=ix*(int(nz)+1)+iz+1
            u=dpdx(nr)*cum2(jf+1)+(speed_surface/xi1h-dpdx(nr)*ratio)*cum1(jf+1)
            v=eta**2*speed_surface*dhdx
            dudy=(dpdx(nr)*yrel+(speed_surface/xi1h-dpdx(nr)*ratio))/mu
            dwdy=dpdz(nr)*(yrel-ratio)/mu
            if(iz==0 .or. iz==int(nz))then
              avg_u=avg_u+.5_rk*u;avg_v=avg_v+.5_rk*v;avg_diss=avg_diss+.5_rk*mu*(dudy*dudy+dwdy*dwdy)
            else
              avg_u=avg_u+u;avg_v=avg_v+v;avg_diss=avg_diss+mu*(dudy*dudy+dwdy*dwdy)
            end if
          end do
          avg_u=avg_u/real(nz,rk);avg_v=avg_v/real(nz,rk);avg_diss=avg_diss/real(nz,rk)
          if(iy==int(ny_pad))then
            kx_n(n)=-(pad_conduct*lube_conduct)/(pad_conduct+lube_conduct)
            ky_n(n)=kx_n(n)
          else
            kx_n(n)=-lube_conduct;ky_n(n)=-lube_conduct
          end if
          mx_n(n)=density*cp*avg_u;my_n(n)=density*cp*avg_v;p_n(n)=0._rk;q_n(n)=-avg_diss
        end if
      end do
    end do

    bw=ny+2;ncol=2*bw-1
    allocate(a(nne,ncol),rhs(nne),alow(nne,bw-1),ipiv(nne),bcidx(nne),pres(nne),raw(nne),nodes0(4))
    a=0._rk;rhs=0._rk;pres=0._rk
    do ix=0,int(nx)-1
      do iy=0,ny-2
        n1=ix*ny+iy+1;n2=(ix+1)*ny+iy+1;n3=n2+1;n4=n1+1
        kx=.25_rk*(kx_n(n1)+kx_n(n2)+kx_n(n3)+kx_n(n4))
        ky=.25_rk*(ky_n(n1)+ky_n(n2)+ky_n(n3)+ky_n(n4))
        mx=.25_rk*(mx_n(n1)+mx_n(n2)+mx_n(n3)+mx_n(n4))
        my=.25_rk*(my_n(n1)+my_n(n2)+my_n(n3)+my_n(n4))
        pe=.25_rk*(p_n(n1)+p_n(n2)+p_n(n3)+p_n(n4))
        q =.25_rk*(q_n(n1)+q_n(n2)+q_n(n3)+q_n(n4))
        ! ROSS temp_xy_assemble_all_jit suppresses reaction/dissipation for
        ! every element wholly inside the solid pad, including the last solid
        ! row whose upper nodes lie exactly on the pad/film interface.
        if(iy<int(ny_pad))then
          pe=0._rk;q=0._rk
        end if
        call rb_energy_q4(x([n1,n2,n3,n4]),y([n1,n2,n3,n4]),kx,ky,mx,my,pe,q,em,ec)
        if(iy<int(ny_pad))then
          if(ix==0 .and. convec_edges>0._rk)call rb_add_edge_convection(1,convec_edges,temp_ambient,x([n1,n2,n3,n4]),y([n1,n2,n3,n4]),em,ec)
          if(ix==int(nx)-1 .and. convec_edges>0._rk)call rb_add_edge_convection(2,convec_edges,temp_ambient,x([n1,n2,n3,n4]),y([n1,n2,n3,n4]),em,ec)
          if(iy==0 .and. convec_back>0._rk)call rb_add_edge_convection(3,convec_back,temp_ambient,x([n1,n2,n3,n4]),y([n1,n2,n3,n4]),em,ec)
        end if
        nodes0=[int(n1-1,ik),int(n2-1,ik),int(n3-1,ik),int(n4-1,ik)]
        call rb_assemble_q4_banded(em,ec,nodes0,int(bw,ik),a,rhs,st)
        if(st/=RB_OK)then;status=st;return;end if
      end do
    end do

    nbc=0
    do iy=int(ny_pad)+1,ny-2
      n=iy+1;nbc=nbc+1;bcidx(nbc)=int(n-1,ik);pres(nbc)=temp_inlet
    end do
    do ix=0,int(nx)
      n=ix*ny+ny;nbc=nbc+1;bcidx(nbc)=int(n-1,ik);pres(nbc)=temp_journal
    end do
    call rb_include_pressure_bc(a,rhs,int(bw,ik),int(nbc,ik),bcidx,pres,int(nne,ik),st)
    if(st/=RB_OK)then;status=st;return;end if
    call rb_lu_factor_band(a,int(nne,ik),int(bw,ik),alow,ipiv,st)
    if(st/=RB_OK)then;status=st;return;end if
    call rb_lu_solve_band_signed(a,int(nne,ik),int(bw,ik),alow,ipiv,rhs,st)
    if(st/=RB_OK)then;status=st;return;end if
    raw=rhs;avg_old=sum(temp_old(1:nne))/real(nne,rk);avg_raw=sum(raw)/real(nne,rk)
    if(abs(avg_raw-avg_old)>10._rk)then;rt=min(relax_t,10._rk/abs(avg_raw-avg_old));else;rt=relax_t;end if
    temp_new(1:nne)=rt*raw+(1._rk-rt)*temp_old(1:nne)
    rms_temp=sqrt(sum((temp_new(1:nne)-temp_old(1:nne))**2)/real(nne,rk))
    ! B12 golden T_max is max(fields["film_temperature"]) from pinned ROSS.
    ! The smooth-pad full-energy mesh contains the complete radial film field,
    ! so retain the film/global maximum rather than a pad-surface-only metric.
    ! ROSS reports tpad_max over the lubricant film, not the solid pad.
    ! For the regular-flooded full model the 2-D film profile is replicated
    ! axially, so scan only y >= pad_thickness (jf=0..ny_film) at each x.
    temp_max=-huge(1._rk)
    do ix=0,int(nx)
      do jf=0,int(ny_film)
        n=ix*ny+int(ny_pad)+jf+1
        temp_max=max(temp_max,temp_new(n))
      end do
    end do
    ! Collapse the relaxed radial viscosity profile to the exact discrete
    ! generalized-Reynolds Gamma used by ROSS.  pad_static/pad_*_pert consume
    ! mu_center through -1/(12*mu_center), so this preserves the full radial
    ! viscosity effect in the pressure matrix instead of sampling one layer.
    do ix=0,int(nx)
      do jf=0,int(ny_film)
        mur(jf+1)=max(rb_mu_of_t(mu1,mu2,t1,t2, &
             temp_new(ix*ny+int(ny_pad)+jf+1)),tiny(1._rk))
        invr(jf+1)=1._rk/mur(jf+1)
      end do
      cum1=0._rk;cum2=0._rk
      deta=1._rk/real(ny_film,rk)
      do jf=1,int(ny_film)
        cum1(jf+1)=cum1(jf)+.5_rk*deta*(invr(jf)+invr(jf+1))
        cum2(jf+1)=cum2(jf)+.5_rk*deta*( &
             real(jf-1,rk)/real(ny_film,rk)*invr(jf)+ &
             real(jf,rk)/real(ny_film,rk)*invr(jf+1))
      end do
      xi1h=max(cum1(int(ny_film)+1),tiny(1._rk))
      xi2h=cum2(int(ny_film)+1);ratio=xi2h/xi1h
      do jf=0,int(ny_film)
        eta=real(jf,rk)/real(ny_film,rk)
        igam(jf+1)=cum2(jf+1)-ratio*cum1(jf+1)
      end do
      gamma_eq=0._rk;g_eq=0._rk
      do jf=1,int(ny_film)
        gamma_eq=gamma_eq+.5_rk*deta*(igam(jf)+igam(jf+1))
        ! Generalized-Reynolds Couette function G = integral(Xi1/Xi1h)deta.
        ! For constant viscosity this reduces exactly to 0.5; with a THD
        ! cross-film viscosity gradient it is not 0.5 and must be retained in
        ! the static Reynolds source term.
        g_eq=g_eq+.5_rk*deta*(cum1(jf)/xi1h+cum1(jf+1)/xi1h)
      end do
      if(gamma_eq>=-tiny(1._rk))then
        status=RB_ERR_INPUT;return
      end if
      mu=-1._rk/(12._rk*gamma_eq)
      do iz=0,int(nz)
        nr=ix*(int(nz)+1)+iz+1
        mu_center(nr)=mu
        if(present(g_reynolds))g_reynolds(nr)=g_eq
      end do
    end do
    ! ROSS flow bookkeeping for regular-flooded smooth pads.  q_in is the
    ! leading-edge circumferential flow; q_out is the flow at h_min.  The
    ! reported outlet is the mass-flux-weighted trailing-edge temperature.
    hmin_local=huge(1._rk);ix_min=0
    do ix=0,int(nx)
      nr=ix*(int(nz)+1)+center+1
      if(h(nr)<hmin_local)then
        hmin_local=h(nr);ix_min=ix
      end if
    end do

    do ix=0,int(nx)
      if(ix/=0 .and. ix/=ix_min .and. ix/=int(nx))cycle
      nr=ix*(int(nz)+1)+center+1;hx=h(nr)
      do jf=0,int(ny_film)
        mur(jf+1)=max(rb_mu_of_t(mu1,mu2,t1,t2, &
             temp_new(ix*ny+int(ny_pad)+jf+1)),tiny(1._rk))
        invr(jf+1)=1._rk/mur(jf+1)
      end do
      cum1=0._rk;cum2=0._rk
      deta=hx/real(ny_film,rk)
      do jf=1,int(ny_film)
        yrel=hx*real(jf,rk)/real(ny_film,rk)
        cum1(jf+1)=cum1(jf)+.5_rk*deta*(invr(jf)+invr(jf+1))
        cum2(jf+1)=cum2(jf)+.5_rk*deta*( &
             hx*real(jf-1,rk)/real(ny_film,rk)*invr(jf)+yrel*invr(jf+1))
      end do
      xi1h=max(cum1(int(ny_film)+1),tiny(1._rk))
      xi2h=cum2(int(ny_film)+1);ratio=xi2h/xi1h
      qax=0._rk;tuax=0._rk
      do iz=0,int(nz)
        nr=ix*(int(nz)+1)+iz+1
        qrad=0._rk;turad=0._rk
        do jf=0,int(ny_film)
          yrel=hx*real(jf,rk)/real(ny_film,rk)
          u=dpdx(nr)*cum2(jf+1)+(speed_surface/xi1h-dpdx(nr)*ratio)*cum1(jf+1)
          wz=1._rk;if(jf==0 .or. jf==int(ny_film))wz=.5_rk
          qrad=qrad+wz*u*deta
          if(ix==int(nx))then
            turad=turad+wz*temp_new(ix*ny+int(ny_pad)+jf+1)*u*deta
          end if
        end do
        wz=1._rk;if(iz==0 .or. iz==int(nz))wz=.5_rk
        qax=qax+wz*qrad*dz
        if(ix==int(nx))tuax=tuax+wz*turad*dz
      end do
      if(ix==0)q_in=qax
      if(ix==ix_min)q_out=qax
      if(ix==int(nx) .and. abs(qax)>tiny(1._rk))temp_outlet=tuax/qax
    end do
    if(q_out>q_in)q_out=q_in
  end subroutine rb_thermal_full_pad

  subroutine rb_energy_q4(x,y,kx,ky,mx,my,p,q,e,f)
    real(rk),intent(in)::x(4),y(4),kx,ky,mx,my,p,q
    real(rk),intent(out)::e(4,4),f(4)
    real(rk),parameter::g=.57735026918962576451_rk
    real(rk)::r,s,nv(4),fr(4),fs(4),b0(4),b1(4),j00,j01,j10,j11,det
    integer::gp,i,j
    e=0._rk;f=0._rk
    do gp=1,4
      select case(gp)
      case(1);r=-g;s=-g
      case(2);r= g;s=-g
      case(3);r=-g;s= g
      case default;r=g;s=g
      end select
      nv=[(1-r)*(1-s)/4._rk,(1+r)*(1-s)/4._rk,(1+r)*(1+s)/4._rk,(1-r)*(1+s)/4._rk]
      fr=[-(1-s)/4._rk,(1-s)/4._rk,(1+s)/4._rk,-(1+s)/4._rk]
      fs=[-(1-r)/4._rk,-(1+r)/4._rk,(1+r)/4._rk,(1-r)/4._rk]
      j00=sum(fr*x);j01=sum(fr*y);j10=sum(fs*x);j11=sum(fs*y);det=j00*j11-j01*j10
      if(abs(det)<=tiny(1._rk))cycle
      b0=( j11*fr-j01*fs)/det;b1=(-j10*fr+j00*fs)/det
      do i=1,4
        do j=1,4
          e(i,j)=e(i,j)+(b0(i)*kx*b0(j)+b1(i)*ky*b1(j)-nv(i)*(mx*b0(j)+my*b1(j))-p*nv(i)*nv(j))*det
        end do
        f(i)=f(i)+nv(i)*q*det
      end do
    end do
  end subroutine rb_energy_q4

  subroutine rb_add_edge_convection(edge,hc,tamb,x,y,e,f)
    integer,intent(in)::edge
    real(rk),intent(in)::hc,tamb,x(4),y(4)
    real(rk),intent(inout)::e(4,4),f(4)
    real(rk),parameter::gg=.57735026918962576451_rk
    real(rk)::r,s,nv(4),fr(4),fs(4),j00,j01,j10,j11,dl,h
    integer::gp,i,j

    ! Mirror ROSS 6320eab9 thermal._temp_line_gauss_jit exactly.  The
    ! historical solver evaluates the boundary metric from the same Q4
    ! Jacobian used by the Python authority; using a textbook edge length here
    ! changes the thermal matrix enough to destabilize the THD fixed point.
    h=-hc
    do gp=1,2
      select case(edge)
      case(1) ! leading edge: r=-1, integrate over s
        r=-1._rk; s=merge(-gg,gg,gp==1)
      case(2) ! trailing edge: r=+1, integrate over s
        r= 1._rk; s=merge(-gg,gg,gp==1)
      case default ! pad back: s=-1, integrate over r
        r=merge(-gg,gg,gp==1); s=-1._rk
      end select

      nv=[(1._rk-r)*(1._rk-s)/4._rk,(1._rk+r)*(1._rk-s)/4._rk, &
          (1._rk+r)*(1._rk+s)/4._rk,(1._rk-r)*(1._rk+s)/4._rk]
      fr=[-(1._rk-s)/4._rk,(1._rk-s)/4._rk,(1._rk+s)/4._rk,-(1._rk+s)/4._rk]
      fs=[-(1._rk-r)/4._rk,-(1._rk+r)/4._rk,(1._rk+r)/4._rk,(1._rk-r)/4._rk]
      j00=sum(fr*x); j01=sum(fr*y); j10=sum(fs*x); j11=sum(fs*y)
      if(abs(r-1._rk)<1e-6_rk .or. abs(r+1._rk)<1e-6_rk)then
        dl=sqrt(j00*j00+j11*j11)
      else if(abs(s-1._rk)<1e-6_rk .or. abs(s+1._rk)<1e-6_rk)then
        dl=sqrt(j10*j10+j11*j11)
      else
        dl=0._rk
      end if
      do i=1,4
        do j=1,4
          e(i,j)=e(i,j)+h*nv(i)*nv(j)*dl
        end do
        f(i)=f(i)+h*tamb*nv(i)*dl
      end do
    end do
  end subroutine rb_add_edge_convection

end module rb_thermal
