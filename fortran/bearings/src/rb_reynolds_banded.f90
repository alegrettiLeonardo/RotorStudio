module rb_reynolds_banded
  use rb_kinds, only: rk, ik
  use rb_status, only: RB_OK, RB_ERR_INPUT
  implicit none(type, external)
  private

  public :: rb_lu_factor_band, rb_lu_solve_band_cavitating
  public :: rb_assemble_q4_banded, rb_include_pressure_bc

contains

  subroutine rb_assemble_q4_banded(e_matrix, e_column, node_ids0, bandwidth, global_matrix, global_column, status)
    real(rk), intent(in) :: e_matrix(4,4), e_column(4)
    integer(ik), intent(in) :: node_ids0(4), bandwidth
    real(rk), intent(inout) :: global_matrix(:,:), global_column(:)
    integer(ik), intent(out) :: status
    integer :: i, j, irow, icol, jcol, nrow, ncol

    status = RB_OK
    nrow = size(global_matrix,1)
    ncol = size(global_matrix,2)
    if (bandwidth < 1 .or. ncol < 2*bandwidth-1 .or. size(global_column) < nrow) then
      status = RB_ERR_INPUT
      return
    end if

    do i = 1, 4
      irow = int(node_ids0(i)) + 1
      if (irow < 1 .or. irow > nrow) then
        status = RB_ERR_INPUT
        return
      end if
      do j = 1, 4
        icol = int(node_ids0(j)) + 1
        if (icol < 1 .or. icol > nrow) then
          status = RB_ERR_INPUT
          return
        end if
        jcol = icol - irow + int(bandwidth)
        if (jcol < 1 .or. jcol > ncol) then
          status = RB_ERR_INPUT
          return
        end if
        global_matrix(irow,jcol) = global_matrix(irow,jcol) + e_matrix(i,j)
      end do
      global_column(irow) = global_column(irow) + e_column(i)
    end do
  end subroutine rb_assemble_q4_banded

  subroutine rb_include_pressure_bc(global_matrix, global_column, bandwidth, total_bc, bc_index0, prescribed, total_n, status)
    real(rk), intent(inout) :: global_matrix(:,:), global_column(:)
    integer(ik), intent(in) :: bandwidth, total_bc, bc_index0(:), total_n
    real(rk), intent(in) :: prescribed(:)
    integer(ik), intent(out) :: status
    integer :: i, j, irow, jrow, jcol, twb, ncol

    status = RB_OK
    ncol = size(global_matrix,2)
    twb = 2*int(bandwidth)
    if (bandwidth < 1 .or. total_n < 1 .or. total_n > size(global_matrix,1) .or. &
        ncol < 2*bandwidth-1 .or. total_bc < 0 .or. total_bc > size(bc_index0) .or. &
        total_bc > size(prescribed)) then
      status = RB_ERR_INPUT
      return
    end if

    do i = 1, int(total_bc)
      irow = int(bc_index0(i)) + 1
      if (irow < 1 .or. irow > total_n) then
        status = RB_ERR_INPUT
        return
      end if

      do j = 2, twb
        ! ROSS jrow is 0-based: irow0 - bandwidth + j - 1.
        ! Converted to Fortran row index by adding one.
        jrow = irow - int(bandwidth) + j - 1
        jcol = twb - j + 1
        if (jrow >= 1 .and. jrow <= total_n) then
          global_column(jrow) = global_column(jrow) - global_matrix(jrow,jcol)*prescribed(i)
          if (jrow /= irow) global_matrix(jrow,jcol) = 0._rk
        end if
      end do

      do jcol = 1, twb-1
        if (jcol /= bandwidth) global_matrix(irow,jcol) = 0._rk
      end do
      global_column(irow) = global_matrix(irow,bandwidth)*prescribed(i)
    end do
  end subroutine rb_include_pressure_bc

  subroutine rb_lu_factor_band(a, total_n, bandwidth, a_lower, index1, status)
    real(rk), intent(inout) :: a(:,:)
    integer(ik), intent(in) :: total_n, bandwidth
    real(rk), intent(out) :: a_lower(:,:)
    integer(ik), intent(out) :: index1(:)
    integer(ik), intent(out) :: status
    integer :: m1, total_column, ll, i, j, k, ii, pivot
    real(rk) :: dum, tmp

    status = RB_OK
    m1 = int(bandwidth)-1
    total_column = 2*int(bandwidth)-1
    if (total_n < 1 .or. total_n > size(a,1) .or. bandwidth < 1 .or. &
        size(a,2) < total_column .or. size(a_lower,1) < total_n .or. &
        size(a_lower,2) < max(0,m1) .or. size(index1) < total_n) then
      status = RB_ERR_INPUT
      return
    end if

    a_lower = 0._rk
    index1 = 0_ik

    ll = m1
    do i = 1, m1
      do j = m1 + 2 - i, total_column
        a(i,j-ll) = a(i,j)
      end do
      ll = ll - 1
      do j = total_column - ll, total_column
        a(i,j) = 0._rk
      end do
    end do

    ll = m1
    do k = 1, int(total_n)
      dum = a(k,1)
      pivot = k
      if (ll < total_n) ll = ll + 1
      do j = k+1, ll
        if (abs(a(j,1)) > abs(dum)) then
          dum = a(j,1)
          pivot = j
        end if
      end do

      if (abs(a(pivot,1)) <= tiny(1._rk)) then
        status = RB_ERR_INPUT
        return
      end if

      index1(k) = int(pivot,ik)
      if (pivot /= k) then
        do j = 1, total_column
          tmp = a(k,j)
          a(k,j) = a(pivot,j)
          a(pivot,j) = tmp
        end do
      end if

      do ii = k+1, ll
        dum = a(ii,1)/a(k,1)
        if (m1 > 0) a_lower(k,ii-k) = dum
        do j = 2, total_column
          a(ii,j-1) = a(ii,j) - dum*a(k,j)
        end do
        a(ii,total_column) = 0._rk
      end do
    end do
  end subroutine rb_lu_factor_band

  subroutine rb_lu_solve_band_cavitating(a, total_n, bandwidth, a_lower, index1, b, press_cavitate, status)
    real(rk), intent(in) :: a(:,:), a_lower(:,:)
    integer(ik), intent(in) :: total_n, bandwidth, index1(:)
    real(rk), intent(inout) :: b(:)
    real(rk), intent(in) :: press_cavitate
    integer(ik), intent(out) :: status
    integer :: total_column, ll, k, i, ip
    real(rk) :: tmp, dum

    status = RB_OK
    total_column = 2*int(bandwidth)-1
    if (total_n < 1 .or. total_n > size(a,1) .or. bandwidth < 1 .or. &
        size(a,2) < total_column .or. size(a_lower,1) < total_n .or. &
        size(index1) < total_n .or. size(b) < total_n) then
      status = RB_ERR_INPUT
      return
    end if

    ll = int(bandwidth)-1
    do k = 1, int(total_n)
      ip = int(index1(k))
      if (ip < 1 .or. ip > total_n) then
        status = RB_ERR_INPUT
        return
      end if
      if (ip /= k) then
        tmp = b(k)
        b(k) = b(ip)
        b(ip) = tmp
      end if
      if (ll < total_n) ll = ll + 1
      do i = k+1, ll
        b(i) = b(i) - a_lower(k,i-k)*b(k)
      end do
    end do

    ll = 1
    do i = int(total_n), 1, -1
      dum = b(i)
      do k = 2, ll
        dum = dum - a(i,k)*b(k+i-1)
      end do
      if (abs(a(i,1)) <= tiny(1._rk)) then
        status = RB_ERR_INPUT
        return
      end if
      b(i) = dum/a(i,1)
      if (ll < total_column) ll = ll + 1
      b(i) = max(b(i),press_cavitate)
    end do
  end subroutine rb_lu_solve_band_cavitating

end module rb_reynolds_banded
