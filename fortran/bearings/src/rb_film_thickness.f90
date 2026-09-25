module rb_film_thickness
  use rb_kinds, only: rk, ik
  use rb_status, only: RB_OK, RB_ERR_INPUT
  implicit none(type, external)
  private

  public :: rb_film_thickness_baseline

contains

  subroutine rb_film_thickness_baseline(total_e_z_film, leading_angle, cp, preload, x_pivot, &
                                        radius, tilt_angle, xj, yj, total_n, n_index0, x, x_rad, &
                                        dh_n, h_n, dhdx_n, h_min, x_hmin, full_cavitate, status)
    integer(ik), intent(in) :: total_e_z_film, total_n
    real(rk), intent(in) :: leading_angle, cp, preload, x_pivot, radius, tilt_angle, xj, yj
    integer(ik), intent(in) :: n_index0(total_n)
    real(rk), intent(in) :: x(:), x_rad(:), dh_n(:)
    real(rk), intent(out) :: h_n(:), dhdx_n(:), h_min, x_hmin
    logical, intent(out) :: full_cavitate
    integer(ik), intent(out) :: status
    integer :: i, node, step, np
    real(rk) :: h

    status = RB_OK
    h_min = 0._rk
    x_hmin = 0._rk
    full_cavitate = .false.
    np = size(x)

    if (total_n < 1 .or. total_e_z_film < 1 .or. cp <= 0._rk .or. &
        size(x_rad) < np .or. size(dh_n) < np .or. size(h_n) < np .or. size(dhdx_n) < np) then
      status = RB_ERR_INPUT
      return
    end if

    do i = 1, int(total_n)
      node = int(n_index0(i)) + 1
      if (node < 1 .or. node > np) then
        status = RB_ERR_INPUT
        return
      end if
      h = cp &
          - xj*cos(leading_angle + x_rad(node)) &
          - yj*sin(leading_angle + x_rad(node)) &
          - preload*cp*cos(x_rad(node) - x_pivot) &
          - radius*tilt_angle*sin(x_rad(node) - x_pivot) &
          + dh_n(node)
      h_n(node) = h
      if (i == 1 .or. h < h_min) then
        h_min = h
        x_hmin = x(node)
      end if
    end do

    step = int(total_e_z_film) + 1
    do i = 1, int(total_n)
      node = int(n_index0(i)) + 1
      if (abs(x(node)) < 1e-6_rk) then
        if (node + step > np .or. abs(x(node+step)-x(node)) <= tiny(1._rk)) then
          status = RB_ERR_INPUT
          return
        end if
        dhdx_n(node) = (-h_n(node) + h_n(node+step))/(x(node+step)-x(node))
      else if (abs(x(node)-maxval(x(1:np))) < 1e-6_rk) then
        if (node - step < 1 .or. abs(x(node)-x(node-step)) <= tiny(1._rk)) then
          status = RB_ERR_INPUT
          return
        end if
        dhdx_n(node) = (h_n(node)-h_n(node-step))/(x(node)-x(node-step))
      else
        if (node-step < 1 .or. node+step > np .or. abs(x(node+step)-x(node-step)) <= tiny(1._rk)) then
          status = RB_ERR_INPUT
          return
        end if
        dhdx_n(node) = (h_n(node+step)-h_n(node-step))/(x(node+step)-x(node-step))
      end if
    end do

    ! Matches the regular-flooded, non-pressure-dam ROSS baseline branch.
    full_cavitate = x_hmin < 1e-6_rk
  end subroutine rb_film_thickness_baseline

end module rb_film_thickness
