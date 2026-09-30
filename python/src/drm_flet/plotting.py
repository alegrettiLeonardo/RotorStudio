"""Engineering views of real Core data. No assembly or eigensolver lives here."""
from __future__ import annotations
from dataclasses import dataclass
from html import escape
from types import SimpleNamespace
import io
import math
import numpy as np
from matplotlib.figure import Figure
from drm_core.domain.model import ShaftElement, TaperedShaftElement
from drm_core.post.modes import _normalize_mode, _interpolate_centerline
from drm_core.units import m_to_mm, rad_s_to_rpm
from .theme import LIGHT, DARK
from .jobs import BearingSweep

@dataclass(frozen=True)
class HitBox:
    kind: str
    index: int
    x0: float
    y0: float
    x1: float
    y1: float
    def contains(self, x, y): return self.x0 <= x <= self.x1 and self.y0 <= y <= self.y1


def rotor_svg(model, selection=None, *, dark=False, width=1000, height=350,
              zoom=1.0, pan=0.0, nodes=True, elements=True, bearings=True, dimensions=True):
    """Source-driven stepped shaft geometry; same coordinates power hit testing."""
    p = DARK if dark else LIGHT
    width, height = max(320, width), max(180, height)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             f'<rect width="100%" height="100%" fill="{p.surface}"/>',
             f'<defs><pattern id="grid" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r=".6" fill="{p.line}"/></pattern></defs>',
             '<rect width="100%" height="100%" fill="url(#grid)"/>']
    hits = []
    def text(x,y,t,color=p.muted,size=11,anchor="middle"):
        parts.append(f'<text x="{x:.2f}" y="{y:.2f}" fill="{color}" font-family="Arial,sans-serif" font-size="{size}" text-anchor="{anchor}">{escape(str(t))}</text>')
    def line(x1,y1,x2,y2,color=p.muted,weight=1,extra=""):
        parts.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{color}" stroke-width="{weight}" {extra}/>')
    def rect(x,y,w,h,fill,stroke=p.muted,weight=1):
        parts.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{max(w,.5):.2f}" height="{max(h,.5):.2f}" rx="2" fill="{fill}" stroke="{stroke}" stroke-width="{weight}"/>')
    if not model.nodes:
        text(width/2,height/2,"Adicione nós e elementos para construir o rotor.",size=14)
        return ("".join(parts)+"</svg>").encode(), hits
    z = {n.number: n.z_m for n in model.nodes}
    left, right = min(z.values()), max(z.values())
    span = max(right-left, .001)
    sx = (width-100)/span*zoom
    center = height*.47
    def x(v): return width/2 + (v-(left+right)/2)*sx + pan
    diameters = [getattr(s,"outer_diameter_m",getattr(s,"outer_diameter_1_m",.05)) for s in model.shafts]
    diameters += [d.p5 for d in model.disks if d.disk_type in (1,3)]
    sy = min(sx, (height*.52)/max(diameters or [.05]))
    for i,s in enumerate(model.shafts):
        if s.node1 not in z or s.node2 not in z: continue
        x1,x2=x(z[s.node1]),x(z[s.node2])
        chosen=selection is not None and selection.kind=="shafts" and selection.index==i
        fill=p.selected if chosen else ("#41566C" if dark else "#CBDCEA")
        d=getattr(s,"outer_diameter_m",getattr(s,"outer_diameter_1_m",.035))
        hh=max(d*sy,5)
        if isinstance(s,TaperedShaftElement):
            h2=max(s.outer_diameter_2_m*sy,5)
            pts=f"{x1},{center-hh/2} {x2},{center-h2/2} {x2},{center+h2/2} {x1},{center+hh/2}"
            parts.append(f'<polygon points="{pts}" fill="{fill}" stroke="{p.primary if chosen else p.muted}" stroke-width="{2 if chosen else 1}"/>')
        else: rect(x1,center-hh/2,x2-x1,hh,fill,p.primary if chosen else p.muted,2 if chosen else 1)
        di=getattr(s,"inner_diameter_m",0)*sy
        if di>0: rect(x1,center-di/2,x2-x1,di,p.surface,p.muted,.5)
        hits.append(HitBox("shafts",i,min(x1,x2),center-max(hh/2,10),max(x1,x2),center+max(hh/2,10)))
        if elements and (chosen or x2-x1>30): text((x1+x2)/2,center+4,f"E{i+1:02d}",p.primary,10)
        if dimensions and chosen:
            yy=center-hh/2-22
            line(x1,yy,x2,yy,p.primary)
            for xx in (x1,x2): line(xx-3,yy-4,xx+3,yy+4,p.primary)
            text((x1+x2)/2,yy-8,f"{m_to_mm(z[s.node2]-z[s.node1]):g} mm",p.primary)
    for i,d in enumerate(model.disks):
        if d.node not in z: continue
        xx=x(z[d.node])
        h=(d.p5*sy if d.disk_type in (1,3) else height*.36)
        w=max(8,(d.p4*sx if d.disk_type in (1,3) else 8))
        rect(xx-w/2,center-h/2,w,h,p.cyan,"#58AABD")
        text(xx,center-h/2-10,f"D{i+1}","#389CB0")
        hits.append(HitBox("disks",i,xx-w/2,center-h/2,xx+w/2,center+h/2))
    if bearings:
        for group in ("bearings","advanced_bearings"):
            for i,b in enumerate(getattr(model,group)):
                if b.node not in z: continue
                xx=x(z[b.node]); bh=max(height*.17,48)
                rect(xx-13,center-bh/2,26,bh,p.subtle,p.primary)
                rect(xx-8,center-bh/2+5,16,bh-10,p.surface,p.primary,.8)
                y1=center+bh/2; y2=min(height-54,y1+27)
                parts.append(f'<path d="M {xx} {y1} L {xx-23} {y2} L {xx+23} {y2} Z" fill="{p.selected}" stroke="{p.primary}"/>')
                line(xx-29,y2+5,xx+29,y2+5)
                for dx in range(-27,29,6): line(xx+dx,y2+6,xx+dx-4,y2+12)
                text(xx,y2+28,getattr(b,"tag","") or f"M{i+1}",p.primary)
                hits.append(HitBox(group,i,xx-18,center-bh/2,xx+18,y2))
    line(25,center,width-20,center,p.muted,.8,'stroke-dasharray="8 5 2 5"')
    if nodes:
        for i,n in enumerate(model.nodes):
            xx=x(n.z_m)
            parts.append(f'<circle cx="{xx:.2f}" cy="{center:.2f}" r="2.4" fill="{p.primary}"/>')
            text(xx,center-height*.31,str(n.number))
    if dimensions:
        yy=height-23
        line(x(left),yy,x(right),yy)
        for v in (left,right):line(x(v),yy-9,x(v),yy+4)
        text(width/2,height-6,f"Comprimento axial: {m_to_mm(right-left):g} mm · geometria do projeto")
    if any(not isinstance(s,(ShaftElement,TaperedShaftElement)) for s in model.shafts) or any(d.disk_type not in (1,3) for d in model.disks):
        text(14,height-42,"Entidades sem geometria explícita: símbolos esquemáticos sem escala",size=9,anchor="start")
    text(14,18,"Z →  |  Y ↑",size=10,anchor="start")
    if abs(sx-sy)>1e-8:text(width-12,18,"Escala radial ajustada",size=9,anchor="end")
    return ("".join(parts)+"</svg>").encode(), hits


def positive_modes(result, count=8):
    ev=np.asarray(result.eigenvalues)
    indices=np.flatnonzero(ev.imag>max(1e-8,float(np.max(np.abs(ev),initial=0))*1e-12))
    return indices[np.argsort(result.natural_frequency_hz[indices])][:count]


def whirl_label(result, index):
    if result.kappa is None: return "—"
    k=np.asarray(result.kappa)[0::4,index]
    k=k[np.abs(k)>.005]
    if not k.size:return "Linear"
    if np.all(k>0):return "FW"
    if np.all(k<0):return "BW"
    return "Misto"


def base_figure(dark=False, projection=None):
    p=DARK if dark else LIGHT
    fig=Figure(figsize=(10.5,4.4),dpi=120,facecolor=p.surface)
    ax=fig.add_subplot(111,projection=projection)
    ax.set_facecolor(p.surface)
    ax.tick_params(colors=p.muted,labelsize=9)
    for spine in ax.spines.values():spine.set_color(p.line)
    ax.xaxis.label.set_color(p.muted);ax.yaxis.label.set_color(p.muted)
    ax.title.set_color(p.text)
    if projection is None:ax.grid(True,color=p.line,linewidth=.7)
    return fig,ax


def png_bytes(fig):
    out = io.BytesIO()
    axes_3d = [ax for ax in fig.axes if ax.name == "3d"]
    extra = [label for ax in axes_3d for label in (ax.xaxis.label, ax.yaxis.label, ax.zaxis.label)]
    fig.savefig(out, format="png", dpi=120, facecolor=fig.get_facecolor(),
                bbox_inches="tight" if axes_3d else None,
                bbox_extra_artists=extra or None, pad_inches=.15)
    return out.getvalue()


def campbell_figure(points, *, dark=False, count=6, cursor=0, forward=True, backward=True, excitation=True, damped=False):
    fig,ax=base_figure(dark)
    if not points:return fig
    p=DARK if dark else LIGHT
    speeds=np.asarray([rad_s_to_rpm(r.speed_rad_s) for r in points])
    colors=[p.primary,"#9363CF","#269C9B","#B584CE","#548FBF","#CA9261"]
    indices=positive_modes(points[0],count)
    for j,k in enumerate(indices):
        label=whirl_label(points[min(cursor,len(points)-1)],k)
        if label=="FW" and not forward:continue
        if label=="BW" and not backward:continue
        freq=[abs(r.eigenvalues[k].imag)/(2*np.pi) if damped else r.natural_frequency_hz[k] for r in points]
        ax.plot(speeds,freq,color=colors[j%len(colors)],linestyle="--" if label=="BW" else "-",lw=1.7,label=f"Ramo {j+1} · {label}")
    ymax=ax.get_ylim()[1]
    if excitation:
        ax.plot(speeds,speeds/60,color=p.muted,ls="--",lw=.9,label="1×")
        ax.plot(speeds,2*speeds/60,color=p.muted,ls=":",lw=.9,label="2×")
        ymax=max(ymax,float(speeds[-1]/60)*1.1)
    ax.axvline(speeds[cursor],color="#CC963F",ls="--",lw=1)
    ax.set_ylim(0,ymax)
    ax.set_xlabel("Rotação [rpm]");ax.set_ylabel("Frequência amortecida fd [Hz]" if damped else "Frequência natural fn [Hz]")
    leg=ax.legend(loc="upper left",ncol=4,fontsize=8,frameon=False)
    for text in leg.get_texts():text.set_color(p.muted)
    fig.subplots_adjust(left=.08,right=.98,top=.92,bottom=.15)
    return fig


def modal_figure(model, result, index, *, dark=False, phase=0.0, scale=1.0, elev=20, azim=-62,
                 orbits=True, reference=True, markers=True):
    """Reuse Core Hermite interpolation; phase/scale are visualization only.

    Elements are rendered by actual connectivity, never by blindly joining
    adjacent list entries (important for nonsequential/coaxial node IDs).
    """
    fig,ax=base_figure(dark,"3d");p=DARK if dark else LIGHT
    v=_normalize_mode(result.eigenvectors[:,index])
    nodes={n.number:i for i,n in enumerate(model.nodes)}
    pieces=[]
    for s in model.shafts:
        i,j=nodes[s.node1],nodes[s.node2]
        local=np.r_[v[4*i:4*i+4],v[4*j:4*j+4]]
        sub=SimpleNamespace(nodes=[model.nodes[i],model.nodes[j]])
        _,z,x,y=_interpolate_centerline(sub,local,16)
        pieces.append((z,x,y))
    if not pieces:raise ValueError("Modo 3D requer elementos de eixo conectados.")
    norm=max(max(np.max(np.abs(x)),np.max(np.abs(y))) for _,x,y in pieces)
    norm=max(float(norm),np.finfo(float).eps)
    phase_factor=np.exp(1j*np.deg2rad(phase))
    theta=np.exp(1j*np.linspace(0,2*np.pi,80))
    for z,x,y in pieces:
        zz=m_to_mm(z)
        ax.plot(zz,np.real(x*phase_factor)/norm*scale,np.real(y*phase_factor)/norm*scale,color="#F27278",lw=1.8)
        if reference:ax.plot(zz,np.zeros(len(z)),np.zeros(len(z)),color=p.muted,ls="--",lw=.7)
        if orbits:
            k=len(z)//2
            ax.plot(np.full(theta.size,zz[k]),np.real(x[k]*theta)/norm*scale,np.real(y[k]*theta)/norm*scale,color="#D295EE",lw=.7)
    z=np.asarray([n.z_m for n in model.nodes])
    if markers:ax.scatter(m_to_mm(z),np.real(v[0::4]*phase_factor)/norm*scale,np.real(v[1::4]*phase_factor)/norm*scale,color="#F27278",s=10)
    ax.set_xlabel("Z axial [mm]");ax.set_ylabel("X normalizado");ax.set_zlabel("Y normalizado",color=p.muted)
    limit=max(1.5,scale*1.15)
    ax.set_ylim(-limit,limit);ax.set_zlim(-limit,limit)
    ax.set_box_aspect((3.5,1,1), zoom=1.35);ax.view_init(elev=elev,azim=azim)
    for axis in (ax.xaxis,ax.yaxis,ax.zaxis):
        axis.pane.fill=False;axis.pane.set_edgecolor(p.line)
        axis._axinfo["grid"]["color"]=p.line
        axis.label.set_color(p.muted)
    ax.tick_params(colors=p.muted,labelsize=7)
    fig.subplots_adjust(left=0,right=1,bottom=.03,top=1)
    return fig


def bearing_figure(result: BearingSweep, *, dark=False, damping=False, cursor=0):
    fig,ax=base_figure(dark);p=DARK if dark else LIGHT
    values=result.C if damping else result.K
    prefix="C" if damping else "K"
    for (i,j),color,ls in zip([(0,0),(1,1),(0,1),(1,0)], [p.primary,"#269C9B","#C79B47","#9363CF"],["-","-","--","--"]):
        ax.plot(rad_s_to_rpm(result.speeds_rad_s),values[:,i,j],color=color,ls=ls,label=f"{prefix}{'xy'[i]}{'xy'[j]}",lw=1.8)
    ax.axvline(rad_s_to_rpm(result.speeds_rad_s[cursor]),color="#CC963F",lw=.8,ls="--")
    ax.set_xlabel("Rotação [rpm]");ax.set_ylabel("Amortecimento [N·s/m]" if damping else "Rigidez [N/m]")
    leg=ax.legend(ncol=4,frameon=False,fontsize=9)
    for t in leg.get_texts():t.set_color(p.muted)
    ax.ticklabel_format(axis="y",style="sci",scilimits=(-3,4))
    ax.yaxis.get_offset_text().set_color(p.muted)
    fig.subplots_adjust(left=.12,right=.98,bottom=.16,top=.91)
    return fig


def generic_figure(record, *, dark=False, node_index=0, component=0):
    """A single selected DOF, with the Core's independent variable preserved."""
    fig,ax=base_figure(dark);r=record.execution.result
    if (hasattr(r,"response") and hasattr(r,"speeds_rad_s") and
        record.execution.case.kind in {"frequency_response", "coaxial_frequency_response",
            "asymmetric_frequency_response", "auxiliary_frequency_response", "foundation_frequency_response"}):
        is_frf=record.execution.case.kind in {"auxiliary_frequency_response", "foundation_frequency_response"}
        x=np.asarray(r.speeds_rad_s)/(2*np.pi) if is_frf else rad_s_to_rpm(r.speeds_rad_s)
        y=m_to_mm(np.abs(r.response[4*node_index+component,:]))
        ax.plot(x,y,lw=1.6,color=(DARK if dark else LIGHT).primary)
        ax.set_xlabel("Frequência de excitação [Hz]" if is_frf else "Rotação [rpm]")
        ax.set_ylabel("Amplitude de pico [mm]")
    elif hasattr(r,"critical_speeds_rad_s"):
        y=rad_s_to_rpm(r.critical_speeds_rad_s)
        ax.scatter(np.arange(1,len(y)+1),y)
        ax.set_xlabel("Índice da velocidade crítica");ax.set_ylabel("Rotação [rpm]")
    else:
        ax.text(.5,.5,"Resultado disponível na tabela e na exportação numérica",ha="center",va="center",transform=ax.transAxes,color=(DARK if dark else LIGHT).text)
        ax.set_axis_off()
    fig.subplots_adjust(left=.10,right=.97,top=.93,bottom=.17)
    return fig
