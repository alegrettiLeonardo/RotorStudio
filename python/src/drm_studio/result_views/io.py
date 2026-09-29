from __future__ import annotations

import numpy as np
import json
from drm_core.analysis.static import StaticResult
from drm_core.analysis.general_frf import FrequencyResponseMatrixResult
from drm_core.analysis.forced_response import ForcedResponseResult
from drm_core.analysis.general_time_response import GeneralTimeResponseResult

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
    if isinstance(result, GeneralTimeResponseResult):
        dof=getattr(record,'time_selection',record.execution.case.options).get('output_dof',0)
        u='m' if dof%4<2 else 'rad';fu='N' if dof%4<2 else 'Nm'
        return ['time_s','rotor_speed_rad_s','angular_acceleration_rad_s2','response_dof_zero_based','force_'+fu,'q_'+u,'v_'+u+'_per_s','a_'+u+'_per_s2','scaled_residual','absolute_residual','iterations'],np.column_stack([result.time_s,result.rotor_speed_rad_s,result.angular_acceleration_rad_s2,np.full(len(result.time_s),dof),result.force[dof],result.displacement[dof],result.velocity[dof],result.acceleration[dof],result.residual,result.absolute_residual,result.iterations])
    if isinstance(result, ForcedResponseResult):
        selection=getattr(record,'forced_selection',record.execution.case.options);dof=selection.get('output_dof',0);kind=selection.get('response','displacement')
        force=result.force_complex[dof];value=getattr(result,kind)[dof];q=result.displacement[dof];v=result.velocity[dof];a=result.acceleration[dof]
        fu='N' if dof%4<2 else 'Nm';u='m' if dof%4<2 else 'rad';selected=u+{'displacement':'','velocity':'_per_s','acceleration':'_per_s2'}[kind]
        return ['frequency_rad_s','rotor_speed_rad_s','response_dof_zero_based','force_at_response_dof_real_'+fu,'force_at_response_dof_imag_'+fu,'response_magnitude_'+selected,'response_phase_rad','q_real_'+u,'q_imag_'+u,'velocity_real_'+u+'_per_s','velocity_imag_'+u+'_per_s','acceleration_real_'+u+'_per_s2','acceleration_imag_'+u+'_per_s2'],np.column_stack([result.frequency_rad_s,result.rotor_speed_rad_s,np.full(len(value),dof),force.real,force.imag,abs(value),np.angle(value),q.real,q.imag,v.real,v.imag,a.real,a.imag])
    if isinstance(result, FrequencyResponseMatrixResult):
        selection=getattr(record,'frf_selection',record.execution.case.options)
        inp=selection.get('input_dof',0);out=selection.get('output_dof',0);kind=selection.get('response','displacement')
        h=getattr(result,{'displacement':'H_disp','velocity':'H_vel','acceleration':'H_acc'}[kind])[out,inp,:]
        return ['excitation_rad_s','rotor_speed_rad_s','input_dof_zero_based','output_dof_zero_based',kind+'_real',kind+'_imag','magnitude','phase_rad'],np.column_stack([result.frequency_rad_s,result.rotor_speed_rad_s,np.full(len(h),inp),np.full(len(h),out),h.real,h.imag,abs(h),np.angle(h)])
    if isinstance(result, StaticResult):
        rows=[];r=result;nan=float('nan')
        for i,x in enumerate(r.node_positions):rows.append([1,i+1,x,r.displacement_y[i],r.reactions[i],nan,nan,nan])
        for i,x in enumerate(r.station_positions):rows.append([2,i+1,x,nan,nan,r.shear[i],r.bending_moment[i],nan])
        for i,w in enumerate(r.shaft_weights):rows.append([3,i+1,(r.node_positions[i]+r.node_positions[i+1])/2,nan,nan,nan,nan,w])
        for i,w in enumerate(r.disk_loads):rows.append([4,i+1,r.node_positions[r.disk_nodes[i]-1],nan,nan,nan,nan,w])
        return ['entity','index','position_m','displacement_y_m','reaction_N','shear_N','bending_Nm','weight_N'],np.asarray(rows)
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
    if isinstance(record.execution.result, GeneralTimeResponseResult):
        r=record.execution.result;arrays={k:v for k,v in vars(r).items() if isinstance(v,np.ndarray)}
        return export_npz(path,**arrays,metadata_json=np.asarray(json.dumps(r.metadata,sort_keys=True)),selection_json=np.asarray(json.dumps(getattr(record,'time_selection',record.execution.case.options),sort_keys=True)),analysis_hash=np.asarray(record.execution.analysis_hash),build_metadata_json=np.asarray(json.dumps(record.execution.build_metadata,sort_keys=True)))
    if isinstance(record.execution.result, ForcedResponseResult):
        r=record.execution.result
        arrays={k:v for k,v in vars(r).items() if isinstance(v,np.ndarray)}
        for name,value in [('F',r.force_complex),('q',r.displacement),('v',r.velocity),('a',r.acceleration)]:arrays.update({name+'_real':value.real,name+'_imag':value.imag})
        return export_npz(path,**arrays,metadata_json=np.asarray(json.dumps(r.metadata,sort_keys=True)),selection_json=np.asarray(json.dumps(getattr(record,'forced_selection',record.execution.case.options),sort_keys=True)),analysis_hash=np.asarray(record.execution.analysis_hash),build_metadata_json=np.asarray(json.dumps(record.execution.build_metadata,sort_keys=True)))
    if isinstance(record.execution.result, FrequencyResponseMatrixResult):
        r=record.execution.result
        arrays={k:v for k,v in vars(r).items() if isinstance(v,np.ndarray)}
        return export_npz(path,**arrays,metadata_json=np.asarray(json.dumps(r.metadata,sort_keys=True)),selection_json=np.asarray(json.dumps(getattr(record,'frf_selection',record.execution.case.options),sort_keys=True)),analysis_hash=np.asarray(record.execution.analysis_hash),build_metadata_json=np.asarray(json.dumps(record.execution.build_metadata,sort_keys=True)))
    if isinstance(record.execution.result, StaticResult):
        r=record.execution.result
        arrays={key:value for key,value in vars(r).items() if isinstance(value,np.ndarray)}
        return export_npz(path,**arrays,metadata_json=np.asarray(json.dumps(r.metadata,sort_keys=True)),analysis_hash=np.asarray(record.execution.analysis_hash),build_metadata_json=np.asarray(json.dumps(record.execution.build_metadata,sort_keys=True)))
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
