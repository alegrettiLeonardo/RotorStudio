from __future__ import annotations

import numpy as np

from drm_core import (
    ModalResult, CriticalSpeedResult, FrequencyResponseResult, TransientResult,
    CoaxialModalResult, CoaxialFrequencyResponseResult,
    AsymmetricModalResult, AsymmetricFrequencyResponseResult,
    export_csv, export_npz, export_figure, write_analysis_report,
)
from drm_core.units import rad_s_to_rpm


def _complex_response_rows(axis, response):
    axis = np.asarray(axis, dtype=float)
    response = np.asarray(response)
    rows = []
    for dof in range(response.shape[0]):
        for j, value_axis in enumerate(axis):
            value = response[dof, j]
            rows.append((
                float(value_axis), float(rad_s_to_rpm(value_axis)), dof + 1,
                float(np.real(value)), float(np.imag(value)),
                float(np.abs(value)), float(np.angle(value)),
            ))
    return [
        "axis_rad_s", "axis_rpm_equivalent", "dof_index",
        "real", "imag", "magnitude", "phase_rad",
    ], np.asarray(rows, dtype=float)


def record_data_table(record):
    """Map qualified result objects to explicit numeric columns without recalculating physics."""
    result = record.execution.result
    if isinstance(result, ModalResult):
        eig = np.asarray(result.eigenvalues)
        data = np.column_stack([
            np.arange(1, eig.size + 1, dtype=float),
            eig.real, eig.imag,
            np.asarray(result.natural_frequency_hz, dtype=float),
            np.asarray(result.damping_ratio, dtype=float),
        ])
        return [
            "root", "eigenvalue_real_rad_s", "eigenvalue_imag_rad_s",
            "natural_frequency_hz", "damping_ratio",
        ], data

    if isinstance(result, list) and result and all(isinstance(x, ModalResult) for x in result):
        rows = []
        for item in result:
            eig = np.asarray(item.eigenvalues)
            for i, value in enumerate(eig):
                rows.append((
                    item.speed_rad_s, rad_s_to_rpm(item.speed_rad_s), i + 1,
                    value.real, value.imag,
                    item.natural_frequency_hz[i], item.damping_ratio[i],
                ))
        return [
            "speed_rad_s", "speed_rpm", "root",
            "eigenvalue_real_rad_s", "eigenvalue_imag_rad_s",
            "natural_frequency_hz", "damping_ratio",
        ], np.asarray(rows, dtype=float)

    if isinstance(result, CriticalSpeedResult):
        critical = np.asarray(result.critical_speeds_rad_s, dtype=float)
        iterations = (
            np.full(critical.shape, np.nan)
            if result.iterations is None else np.asarray(result.iterations, dtype=float)
        )
        converged = (
            np.full(critical.shape, np.nan)
            if result.converged is None else np.asarray(result.converged, dtype=float)
        )
        return [
            "critical_speed_rad_s", "critical_speed_rpm", "iterations", "converged"
        ], np.column_stack([critical, rad_s_to_rpm(critical), iterations, converged])

    if isinstance(result, (FrequencyResponseResult, CoaxialFrequencyResponseResult, AsymmetricFrequencyResponseResult)):
        return _complex_response_rows(result.speeds_rad_s, result.response)

    if isinstance(result, TransientResult):
        time = np.asarray(result.time_s, dtype=float)
        response = np.asarray(result.response)
        rows = []
        for dof in range(response.shape[0]):
            for j, time_s in enumerate(time):
                value = response[dof, j]
                speed = np.nan if result.speed_rad_s is None else float(np.asarray(result.speed_rad_s)[j])
                forcing = np.nan
                if result.forcing is not None:
                    f = np.asarray(result.forcing)
                    forcing = float(f[j] if f.ndim == 1 else f.reshape(-1, f.shape[-1])[0, j])
                rows.append((
                    time_s, dof + 1,
                    float(np.real(value)), float(np.imag(value)), float(np.abs(value)),
                    speed, np.nan if not np.isfinite(speed) else float(rad_s_to_rpm(speed)),
                    forcing,
                ))
        return [
            "time_s", "dof_index", "response_real", "response_imag",
            "response_magnitude", "speed_rad_s", "speed_rpm", "forcing",
        ], np.asarray(rows, dtype=float)

    if isinstance(result, (CoaxialModalResult, AsymmetricModalResult)):
        eig = np.asarray(result.eigenvalues)
        return [
            "root", "eigenvalue_real_rad_s", "eigenvalue_imag_rad_s", "frequency_abs_hz"
        ], np.column_stack([
            np.arange(1, eig.size + 1, dtype=float),
            eig.real, eig.imag, np.abs(eig.imag) / (2.0 * np.pi),
        ])

    raise TypeError(f"no qualified CSV mapping for {type(result).__name__}")


def export_record_csv(record, path):
    header, data = record_data_table(record)
    # drm_core's public Stage 1 CSV API is keyword-column based and preserves
    # explicit column names.  Keep the UI adapter on that API rather than
    # reaching into an alternate export implementation.
    return export_csv(
        path,
        **{name: data[:, i] for i, name in enumerate(header)},
    )


def export_record_native(record, path):
    header, data = record_data_table(record)
    return export_npz(
        path,
        data=data,
        columns=np.asarray(header, dtype="U64"),
        analysis_hash=np.asarray([record.execution.analysis_hash]),
    )


def export_record_report(record, outdir):
    return write_analysis_report(record.execution, outdir)


def view_figure(view):
    for name in ("campbell_figure", "figure", "time_figure", "mode_figure"):
        figure = getattr(view, name, None)
        if figure is not None:
            return figure
    return None


def export_view_plot_bundle(view, base_path):
    figure = view_figure(view)
    if figure is None:
        raise ValueError("the selected result view has no plot to export")
    return export_figure(figure, base_path, formats=("png", "svg", "pdf"))
