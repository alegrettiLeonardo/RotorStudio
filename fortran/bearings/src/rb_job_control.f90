module rb_job_control
  use rb_kinds, only: ik
  implicit none(type, external)
  private

  ! B14 job control is deliberately additive and contains no bearing physics.
  ! The GUI has one heavy native bearing job in flight, so this small volatile
  ! state is a single-job mailbox used for cooperative cancellation/progress.
  integer(ik), volatile, save :: cancel_requested = 0_ik
  integer(ik), volatile, save :: current_stage = 0_ik
  integer(ik), volatile, save :: current_iteration = 0_ik
  integer(ik), volatile, save :: maximum_iterations = 0_ik
  integer(ik), volatile, save :: completed_cases = 0_ik
  integer(ik), volatile, save :: total_cases = 0_ik

  public :: rb_job_reset, rb_job_request_cancel, rb_job_cancelled
  public :: rb_job_update, rb_job_snapshot

contains

  subroutine rb_job_reset()
    cancel_requested = 0_ik
    current_stage = 0_ik
    current_iteration = 0_ik
    maximum_iterations = 0_ik
    completed_cases = 0_ik
    total_cases = 0_ik
  end subroutine rb_job_reset

  subroutine rb_job_request_cancel()
    cancel_requested = 1_ik
  end subroutine rb_job_request_cancel

  logical function rb_job_cancelled()
    rb_job_cancelled = cancel_requested /= 0_ik
  end function rb_job_cancelled

  subroutine rb_job_update(stage, iteration, max_iterations, completed, total)
    integer(ik), intent(in) :: stage, iteration, max_iterations, completed, total
    current_stage = stage
    current_iteration = max(0_ik, iteration)
    maximum_iterations = max(0_ik, max_iterations)
    completed_cases = max(0_ik, completed)
    total_cases = max(0_ik, total)
  end subroutine rb_job_update

  subroutine rb_job_snapshot(stage, iteration, max_iterations, completed, total, cancelled)
    integer(ik), intent(out) :: stage, iteration, max_iterations, completed, total, cancelled
    stage = current_stage
    iteration = current_iteration
    max_iterations = maximum_iterations
    completed = completed_cases
    total = total_cases
    cancelled = cancel_requested
  end subroutine rb_job_snapshot

end module rb_job_control
