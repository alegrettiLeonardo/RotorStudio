"""I15 experimental lateral correlation for the qualified iRdin path.

No experimental data are fabricated. A dataset must be supplied explicitly,
with channel-to-probe mapping and project-defined acceptance limits before the
status can become MODEL_CORRELATED_FOR_LATERAL_SCOPE.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass,replace
import math
from pathlib import Path
from typing import Iterable,Mapping,Sequence

import numpy as np

from drm_core.analysis.irdin_lateral import run_irdin_synchronous_sweep

RPM_TO_RAD_S=2.0*math.pi/60.0


@dataclass(frozen=True)
class ExperimentalLateralDataset:
    speed_rpm:np.ndarray
    channel_names:tuple[str,...]
    response_m:np.ndarray
    measured_critical_speeds_rpm:tuple[float,...]=()
    metadata:dict=None

    def __post_init__(self):
        speed=np.asarray(self.speed_rpm,dtype=np.float64)
        response=np.asarray(self.response_m,dtype=np.complex128)
        if speed.ndim!=1 or speed.size<1 or not np.isfinite(speed).all():
            raise ValueError("I15 experimental speed_rpm must be a nonempty finite vector")
        if np.any(speed<0.0) or (speed.size>1 and np.any(np.diff(speed)<=0.0)):
            raise ValueError("I15 experimental speed_rpm must be strictly increasing and nonnegative")
        if response.shape!=(len(self.channel_names),speed.size):
            raise ValueError(
                f"I15 response shape {response.shape} does not match "
                f"{len(self.channel_names)} channels x {speed.size} speeds"
            )
        if not np.isfinite(response.real).all() or not np.isfinite(response.imag).all():
            raise ValueError("I15 experimental responses must be finite")
        if len(set(self.channel_names))!=len(self.channel_names) or any(not str(x).strip() for x in self.channel_names):
            raise ValueError("I15 channel names must be unique and nonempty")
        critical=tuple(float(x) for x in self.measured_critical_speeds_rpm)
        if any(not math.isfinite(x) or x<=0.0 for x in critical):
            raise ValueError("I15 measured critical speeds must be finite and > 0")
        object.__setattr__(self,"speed_rpm",speed.copy())
        object.__setattr__(self,"response_m",response.copy())
        object.__setattr__(self,"channel_names",tuple(str(x) for x in self.channel_names))
        object.__setattr__(self,"measured_critical_speeds_rpm",critical)
        object.__setattr__(self,"metadata",dict(self.metadata or {}))


@dataclass(frozen=True)
class ChannelCorrelation:
    channel:str
    probe_index:int
    predicted_m:np.ndarray
    measured_m:np.ndarray
    amplitude_delta_m:np.ndarray
    amplitude_relative_error:np.ndarray
    phase_delta_rad:np.ndarray


@dataclass(frozen=True)
class CriticalSpeedCorrelation:
    predicted_index:int
    measured_index:int
    predicted_rpm:float
    measured_rpm:float
    delta_rpm:float
    relative_error:float


@dataclass(frozen=True)
class LateralCorrelationResult:
    speed_rpm:np.ndarray
    channels:tuple[ChannelCorrelation,...]
    critical_speeds:tuple[CriticalSpeedCorrelation,...]
    metadata:dict


def load_experimental_lateral_csv(
    path:str|Path,
    *,
    measured_critical_speeds_rpm:Sequence[float]=(),
)->ExperimentalLateralDataset:
    """Read canonical I15 CSV.

    Required first column: speed_rpm.
    Each channel is represented by:
      <channel>_amplitude_um
      <channel>_phase_deg
    """
    source=Path(path)
    with source.open("r",encoding="utf-8-sig",newline="") as handle:
        reader=csv.DictReader(handle)
        fields=list(reader.fieldnames or [])
        if not fields or fields[0]!="speed_rpm":
            raise ValueError("I15 CSV first column must be speed_rpm")
        amp_fields=[x for x in fields[1:] if x.endswith("_amplitude_um")]
        if not amp_fields:
            raise ValueError("I15 CSV requires at least one *_amplitude_um channel")
        channels=[x[:-len("_amplitude_um")] for x in amp_fields]
        expected={"speed_rpm"}
        for channel in channels:
            expected.add(f"{channel}_amplitude_um")
            expected.add(f"{channel}_phase_deg")
        extras=set(fields)-expected
        missing=expected-set(fields)
        if missing or extras:
            raise ValueError(
                f"I15 CSV channel columns mismatch; missing={sorted(missing)}, extras={sorted(extras)}"
            )
        speeds=[];values=[[] for _ in channels]
        for row_no,row in enumerate(reader,start=2):
            try:
                rpm=float(row["speed_rpm"])
                speeds.append(rpm)
                for i,channel in enumerate(channels):
                    amplitude_um=float(row[f"{channel}_amplitude_um"])
                    phase_deg=float(row[f"{channel}_phase_deg"])
                    values[i].append(amplitude_um*1.0e-6*np.exp(1j*np.deg2rad(phase_deg)))
            except (TypeError,ValueError) as exc:
                raise ValueError(f"I15 CSV row {row_no} contains invalid numeric data") from exc
    return ExperimentalLateralDataset(
        np.asarray(speeds,float),
        tuple(channels),
        np.asarray(values,dtype=np.complex128),
        tuple(measured_critical_speeds_rpm),
        {"source_file":source.name,"amplitude_unit":"um","phase_unit":"deg"},
    )


def _wrapped_phase_delta(predicted,measured):
    return np.angle(np.exp(1j*(np.angle(predicted)-np.angle(measured))))


def _relative_amplitude_error(predicted,measured):
    pa=np.abs(predicted);ma=np.abs(measured)
    out=np.full(ma.shape,np.inf,dtype=float)
    positive=ma>0.0
    out[positive]=np.abs(pa[positive]-ma[positive])/ma[positive]
    both_zero=(ma==0.0)&(pa==0.0)
    out[both_zero]=0.0
    return out


def correlate_lateral_dataset(
    project,
    dataset:ExperimentalLateralDataset,
    *,
    channel_to_probe:Mapping[str,int],
    predicted_critical_speeds_rpm:Sequence[float]=(),
    critical_pairs:Sequence[tuple[int,int]]=(),
    library_path:str|Path|None=None,
)->LateralCorrelationResult:
    mapping={str(k):int(v) for k,v in channel_to_probe.items()}
    if set(mapping)!=set(dataset.channel_names):
        raise ValueError("I15 channel_to_probe must map every experimental channel exactly once")
    probe_count=len(project.model.probes)
    if any(v<1 or v>probe_count for v in mapping.values()):
        raise ValueError(f"I15 probe indices must be in 1..{probe_count}")
    if len(set(mapping.values()))!=len(mapping.values()):
        raise ValueError("I15 initial scope requires one experimental channel per distinct probe")

    sweep=run_irdin_synchronous_sweep(
        project,
        dataset.speed_rpm*RPM_TO_RAD_S,
        library_path=library_path,
    )
    channels=[]
    for row,channel in enumerate(dataset.channel_names):
        probe_index=mapping[channel]
        predicted=np.asarray(sweep.probe_response[probe_index-1],dtype=np.complex128)
        measured=np.asarray(dataset.response_m[row],dtype=np.complex128)
        channels.append(ChannelCorrelation(
            channel,
            probe_index,
            predicted.copy(),
            measured.copy(),
            np.abs(predicted)-np.abs(measured),
            _relative_amplitude_error(predicted,measured),
            _wrapped_phase_delta(predicted,measured),
        ))

    predicted_critical=tuple(float(x) for x in predicted_critical_speeds_rpm)
    measured_critical=dataset.measured_critical_speeds_rpm
    critical=[]
    for pi,mi in critical_pairs:
        pi=int(pi);mi=int(mi)
        if pi<0 or pi>=len(predicted_critical) or mi<0 or mi>=len(measured_critical):
            raise ValueError("I15 critical-speed pair index is out of range")
        p=predicted_critical[pi];m=measured_critical[mi]
        if not math.isfinite(p) or p<=0.0:
            raise ValueError("I15 predicted critical speeds must be finite and > 0")
        critical.append(CriticalSpeedCorrelation(
            pi,mi,p,m,p-m,abs(p-m)/m
        ))

    return LateralCorrelationResult(
        dataset.speed_rpm.copy(),
        tuple(channels),
        tuple(critical),
        {
            "status":"MODEL_NOT_CORRELATED",
            "acceptance_evaluated":False,
            "source":"EXPERIMENTAL_DATASET",
            "native_prediction":"I9_EXPANDED_SYNCHRONOUS_RESPONSE",
            "channel_to_probe":mapping,
        },
    )


def assess_lateral_correlation(
    result:LateralCorrelationResult,
    *,
    amplitude_relative_limit:float,
    phase_deg_limit:float,
    critical_speed_relative_limit:float|None=None,
    minimum_measured_amplitude_m:float=0.0,
)->LateralCorrelationResult:
    amp_limit=float(amplitude_relative_limit)
    phase_limit=math.radians(float(phase_deg_limit))
    floor=float(minimum_measured_amplitude_m)
    if not math.isfinite(amp_limit) or amp_limit<0.0:
        raise ValueError("I15 amplitude_relative_limit must be finite and >= 0")
    if not math.isfinite(phase_limit) or phase_limit<0.0 or phase_limit>math.pi:
        raise ValueError("I15 phase_deg_limit must be finite in [0,180]")
    if not math.isfinite(floor) or floor<0.0:
        raise ValueError("I15 minimum_measured_amplitude_m must be finite and >= 0")

    channel_pass=True
    maxima={}
    for channel in result.channels:
        measured_amp=np.abs(channel.measured_m)
        mask=measured_amp>=floor
        if not np.any(mask):
            raise ValueError(f"I15 channel {channel.channel!r} has no points above amplitude floor")
        amp=float(np.max(channel.amplitude_relative_error[mask]))
        phase=float(np.max(np.abs(channel.phase_delta_rad[mask])))
        maxima[channel.channel]={
            "max_amplitude_relative_error":amp,
            "max_abs_phase_delta_deg":math.degrees(phase),
            "points_assessed":int(np.count_nonzero(mask)),
        }
        channel_pass=channel_pass and amp<=amp_limit and phase<=phase_limit

    critical_pass=True
    if critical_speed_relative_limit is not None:
        limit=float(critical_speed_relative_limit)
        if not math.isfinite(limit) or limit<0.0:
            raise ValueError("I15 critical_speed_relative_limit must be finite and >= 0")
        if not result.critical_speeds:
            raise ValueError("I15 critical-speed acceptance requested without explicit critical pairs")
        critical_pass=all(x.relative_error<=limit for x in result.critical_speeds)
    else:
        limit=None

    passed=bool(channel_pass and critical_pass)
    metadata=dict(result.metadata)
    metadata.update({
        "status":"MODEL_CORRELATED_FOR_LATERAL_SCOPE" if passed else "MODEL_NOT_CORRELATED",
        "acceptance_evaluated":True,
        "amplitude_relative_limit":amp_limit,
        "phase_deg_limit":float(phase_deg_limit),
        "minimum_measured_amplitude_m":floor,
        "critical_speed_relative_limit":limit,
        "channel_maxima":maxima,
        "passed":passed,
    })
    return replace(result,metadata=metadata)


def modal_assurance_criterion(predicted,measured)->float:
    a=np.asarray(predicted,dtype=np.complex128).reshape(-1)
    b=np.asarray(measured,dtype=np.complex128).reshape(-1)
    if a.shape!=b.shape or a.size<1:
        raise ValueError("I15 MAC vectors must be nonempty and equal sized")
    if not np.isfinite(a.real).all() or not np.isfinite(a.imag).all():
        raise ValueError("I15 predicted modal vector is nonfinite")
    if not np.isfinite(b.real).all() or not np.isfinite(b.imag).all():
        raise ValueError("I15 measured modal vector is nonfinite")
    den=float(np.vdot(a,a).real*np.vdot(b,b).real)
    if den<=0.0:
        raise ValueError("I15 MAC vectors must have nonzero norm")
    return float(abs(np.vdot(a,b))**2/den)


__all__=[
    "ExperimentalLateralDataset","ChannelCorrelation","CriticalSpeedCorrelation",
    "LateralCorrelationResult","load_experimental_lateral_csv",
    "correlate_lateral_dataset","assess_lateral_correlation",
    "modal_assurance_criterion",
]
