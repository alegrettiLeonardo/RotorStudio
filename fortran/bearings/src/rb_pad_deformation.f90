module rb_pad_deformation
  use rb_kinds, only: rk, ik
  use rb_status, only: RB_OK, RB_ERR_INPUT
  use rb_reynolds_banded, only: rb_include_pressure_bc, rb_lu_factor_band, rb_lu_solve_band_signed
  implicit none(type, external)
  private

  integer(ik), parameter, public :: RB_DEFORM_NONE = 0_ik
  integer(ik), parameter, public :: RB_DEFORM_PAD_MECHANICAL = 1_ik
  integer(ik), parameter, public :: RB_DEFORM_PAD_MECHANICAL_THERMAL = 2_ik
  integer(ik), parameter, public :: RB_DEFORM_PAD_PIVOT_MECHANICAL = 5_ik

  public :: rb_pad_surface_deformation

contains

  subroutine rb_pad_surface_deformation(nx,ny,pad_length,pad_thickness,young,poisson,pad_expand,temp_ref, &
                                        temp_pad,pressure_x,tilting,pivot_fraction,deform_surface,status)
    integer(ik),intent(in)::nx,ny
    real(rk),intent(in)::pad_length,pad_thickness,young,poisson,pad_expand,temp_ref
    real(rk),intent(in)::temp_pad(:),pressure_x(:),pivot_fraction
    logical,intent(in)::tilting
    real(rk),intent(out)::deform_surface(:)
    integer(ik),intent(out)::status
    integer::nn,ndof,ix,iy,n1,n2,n3,n4,bw,ncol,nbc,i,j,li,lj,irow,icol,jcol,pivot_ix
    real(rk)::dx,dy,dt,px,detj,gp(2),em(8,8),ef(8),x4(4),y4(4),e3(3,3),alpha
    real(rk),allocatable::a(:,:),rhs(:),alow(:,:),pres(:)
    integer(ik),allocatable::ipiv(:),bcidx(:)
    integer::nodes(4),dofs(8)
    integer(ik)::st

    status=RB_OK
    nn=(int(nx)+1)*(int(ny)+1);ndof=2*nn
    if(nx<2 .or. ny<2 .or. pad_length<=0._rk .or. pad_thickness<=0._rk .or. young<=0._rk .or. &
       poisson<=-0.99_rk .or. poisson>=0.499_rk .or. size(temp_pad)<nn .or. size(pressure_x)<int(nx)+1 .or. &
       size(deform_surface)<int(nx)+1 .or. pivot_fraction<0._rk .or. pivot_fraction>1._rk)then
      status=RB_ERR_INPUT;return
    end if
    dx=pad_length/real(nx,rk);dy=pad_thickness/real(ny,rk)
    bw=2*(int(ny)+2)+1;ncol=2*bw-1
    allocate(a(ndof,ncol),rhs(ndof),alow(ndof,bw-1),ipiv(ndof),bcidx(ndof),pres(ndof))
    a=0._rk;rhs=0._rk;pres=0._rk
    alpha=young/((1._rk+poisson)*(1._rk-2._rk*poisson))
    e3=0._rk
    e3(1,1)=alpha*(1._rk-poisson);e3(1,2)=alpha*poisson
    e3(2,1)=alpha*poisson;e3(2,2)=alpha*(1._rk-poisson)
    e3(3,3)=alpha*(1._rk-2._rk*poisson)/2._rk
    gp=[-.57735026918962576451_rk,.57735026918962576451_rk]

    do ix=0,int(nx)-1
      do iy=0,int(ny)-1
        n1=ix*(int(ny)+1)+iy+1;n2=(ix+1)*(int(ny)+1)+iy+1;n3=n2+1;n4=n1+1
        nodes=[n1,n2,n3,n4]
        x4=[real(ix,rk)*dx,real(ix+1,rk)*dx,real(ix+1,rk)*dx,real(ix,rk)*dx]
        y4=[real(iy,rk)*dy,real(iy,rk)*dy,real(iy+1,rk)*dy,real(iy+1,rk)*dy]
        dt=.25_rk*(temp_pad(n1)+temp_pad(n2)+temp_pad(n3)+temp_pad(n4))-temp_ref
        call rb_deform_q4(x4,y4,e3,pad_expand*dt,gp,em,ef)
        do i=1,4
          dofs(2*i-1)=2*(nodes(i)-1)+1;dofs(2*i)=dofs(2*i-1)+1
        end do
        do i=1,8
          irow=dofs(i)
          do j=1,8
            icol=dofs(j);jcol=icol-irow+bw
            if(jcol<1 .or. jcol>ncol)then;status=RB_ERR_INPUT;return;end if
            a(irow,jcol)=a(irow,jcol)+em(i,j)
          end do
          rhs(irow)=rhs(irow)+ef(i)
        end do
      end do
    end do

    ! Pressure line load at the film surface. Positive pressure pushes the pad
    ! toward its back, hence the negative radial nodal force.
    do ix=0,int(nx)-1
      px=.5_rk*(pressure_x(ix+1)+pressure_x(ix+2))
      n1=ix*(int(ny)+1)+int(ny)+1;n2=(ix+1)*(int(ny)+1)+int(ny)+1
      rhs(2*(n1-1)+2)=rhs(2*(n1-1)+2)-px*dx/2._rk
      rhs(2*(n2-1)+2)=rhs(2*(n2-1)+2)-px*dx/2._rk
    end do

    nbc=0
    if(.not.tilting)then
      do ix=0,int(nx)
        n1=ix*(int(ny)+1)+1
        nbc=nbc+1;bcidx(nbc)=int(2*(n1-1)+1,ik);pres(nbc)=0._rk
      end do
    else
      pivot_ix=nint(pivot_fraction*real(nx,rk));pivot_ix=max(0,min(int(nx),pivot_ix))
      do iy=0,int(ny)
        n1=pivot_ix*(int(ny)+1)+iy+1
        nbc=nbc+1;bcidx(nbc)=int(2*(n1-1),ik);pres(nbc)=0._rk
        if(iy==0)then
          nbc=nbc+1;bcidx(nbc)=int(2*(n1-1)+1,ik);pres(nbc)=0._rk
        end if
      end do
    end if
    call rb_include_pressure_bc(a,rhs,int(bw,ik),int(nbc,ik),bcidx,pres,int(ndof,ik),st)
    if(st/=RB_OK)then;status=st;return;end if
    call rb_lu_factor_band(a,int(ndof,ik),int(bw,ik),alow,ipiv,st)
    if(st/=RB_OK)then;status=st;return;end if
    call rb_lu_solve_band_signed(a,int(ndof,ik),int(bw,ik),alow,ipiv,rhs,st)
    if(st/=RB_OK)then;status=st;return;end if

    do ix=0,int(nx)
      n1=ix*(int(ny)+1)+int(ny)+1
      ! Film-thickness convention: positive means the elastic surface moves
      ! away from the journal. Pressure produces negative displacement.
      deform_surface(ix+1)=rhs(2*(n1-1)+2)
    end do
  end subroutine rb_pad_surface_deformation

  subroutine rb_deform_q4(x,y,e3,eps_th,gp,em,ef)
    real(rk),intent(in)::x(4),y(4),e3(3,3),eps_th,gp(2)
    real(rk),intent(out)::em(8,8),ef(8)
    real(rk)::r,s,fr(4),fs(4),b0(4),b1(4),dn(3,8),sig0(3),j00,j01,j10,j11,det
    integer::ir,is,i,j,k
    em=0._rk;ef=0._rk;sig0=matmul(e3,[eps_th,eps_th,0._rk])
    do ir=1,2
      r=gp(ir)
      do is=1,2
        s=gp(is)
        fr=[-(1-s)/4._rk,(1-s)/4._rk,(1+s)/4._rk,-(1+s)/4._rk]
        fs=[-(1-r)/4._rk,-(1+r)/4._rk,(1+r)/4._rk,(1-r)/4._rk]
        j00=sum(fr*x);j01=sum(fr*y);j10=sum(fs*x);j11=sum(fs*y);det=j00*j11-j01*j10
        b0=( j11*fr-j01*fs)/det;b1=(-j10*fr+j00*fs)/det
        dn=0._rk
        do k=1,4
          dn(1,2*k-1)=b0(k);dn(2,2*k)=b1(k)
          dn(3,2*k-1)=b1(k);dn(3,2*k)=b0(k)
        end do
        em=em+matmul(transpose(dn),matmul(e3,dn))*det
        ef=ef+matmul(transpose(dn),sig0)*det
      end do
    end do
  end subroutine rb_deform_q4

end module rb_pad_deformation
