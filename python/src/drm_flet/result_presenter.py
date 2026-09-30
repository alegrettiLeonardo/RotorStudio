"""Presentation-only plotting/table adapters for all native result contracts.

No inverse, eigensolve, response solve or time integration is performed here.
Axes always distinguish rotor rotation from independent forcing frequency.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from drm_core.units import rad_s_to_rpm
from drm_core.analysis.modal import ModalResult
from drm_core.analysis.static import StaticResult
from drm_core.analysis.general_frf import FrequencyResponseMatrixResult
from drm_core.analysis.forced_response import ForcedResponseResult
from drm_core.analysis.general_time_response import GeneralTimeResponseResult
from drm_core.analysis.critical_speed import CriticalSpeedResult
from drm_core.analysis.transient import TransientResult
from drm_core.analysis.frequency_response import FrequencyResponseResult
from drm_core.analysis.coaxial import CoaxialModalResult,CoaxialFrequencyResponseResult
from drm_core.analysis.asymmetric import AsymmetricModalResult,AsymmetricFrequencyResponseResult
from drm_core.analysis.ucs import UCSResult
from drm_core.analysis.level1 import Level1Result
from drm_core.analysis.api617_unbalance import API617UnbalanceResult
from .plotting import base_figure,modal_figure
from .clearance_view import ClearanceResult,CLEARANCE_TABS,present_clearance

HARMONIC = (FrequencyResponseResult,CoaxialFrequencyResponseResult,AsymmetricFrequencyResponseResult)
SPECIAL_MODAL = (CoaxialModalResult,AsymmetricModalResult)
SUPPORTED_TYPES=(StaticResult,FrequencyResponseMatrixResult,ForcedResponseResult,GeneralTimeResponseResult,CriticalSpeedResult,TransientResult,*HARMONIC,*SPECIAL_MODAL,UCSResult,Level1Result,API617UnbalanceResult,ClearanceResult,tuple)

@dataclass
class Presented:
    figure: object
    headers: list[str]
    rows: list[list]
    note: str = ''


def tabs_for(r):
    if isinstance(r,ClearanceResult):return CLEARANCE_TABS
    if isinstance(r,StaticResult):return [('deflection','Deflexão'),('shear','Cortante'),('moment','Momento'),('reactions','Reações'),('weights','Massas / pesos')]
    if isinstance(r,FrequencyResponseMatrixResult):return [('magnitude','Módulo'),('phase','Fase'),('polar','Polar'),('matrix','Matriz'),('residual','Resíduo')]
    if isinstance(r,ForcedResponseResult):return [('magnitude','Amplitude'),('phase','Fase'),('polar','Polar'),('orbit','Órbita'),('force','Força'),('residual','Resíduo'),('condition','Condicionamento')]
    if isinstance(r,AsymmetricFrequencyResponseResult):return [('magnitude','Módulo no referencial girante'),('phase','Fase / sinal')]
    if isinstance(r,CoaxialFrequencyResponseResult):return [('magnitude','Amplitude'),('phase','Fase')]
    if isinstance(r,HARMONIC):return [('magnitude','Amplitude'),('phase','Fase'),('orbit','Órbita'),('ods','Deformada ODS')]
    if isinstance(r,GeneralTimeResponseResult):return [('response','Resposta'),('orbit','Órbita'),('spectrum','DFFT'),('speed','Rotação'),('force','Força'),('residual','Resíduo'),('iterations','Iterações')]
    if isinstance(r,TransientResult):return [('response','Resposta'),('orbit','Órbita'),('spectrum','DFFT'),('speed','Rotação'),('force','Excitação')]
    if isinstance(r,SPECIAL_MODAL):return [('eigenvalues','Autovalores'),('modes','Modos 3D'),('orbits','Órbitas')]
    if isinstance(r,CriticalSpeedResult):return [('criticals','Velocidades'),('convergence','Convergência'),('modes','Formas modais')]
    if isinstance(r,UCSResult):return [('map','Mapa UCS'),('intersections','Interseções'),('critical_modes','Modos nas interseções')]
    if isinstance(r,Level1Result):return [('log_dec','Decremento'),('eigenvalues','Autovalores'),('frequencies','Frequências')]
    if isinstance(r,API617UnbalanceResult):return [('placement','Posicionamento'),('major_axis','Eixo maior'),('sign','Sinal modal')]
    if isinstance(r,tuple) and len(r)==5:return [('K','Rigidez K'),('C','Amortecimento C'),('M','Massa M'),('constraints','Restrições'),('eccentricity','Excentricidade')]
    raise TypeError(f'Sem apresentador tipado para {type(r).__name__}; resultado não substituído por gráfico fictício.')


def time_spectrum(t,values):
    """Same unwindowed one-sided DFFT convention as the existing Qt view."""
    t=np.asarray(t);v=np.asarray(values);dt=np.diff(t)
    if len(t)<2 or np.any(dt<=0) or not np.allclose(dt,dt[0],rtol=1e-9,atol=0):return None
    a=np.abs(np.fft.rfft(v))/len(v);a[1:]*=2
    if len(v)%2==0:a[-1]/=2
    return np.fft.rfftfreq(len(v),dt[0]),a


def dof_label(model,index):
    return f'Nó {model.nodes[index//4].number} · {("x","y","α","β")[index%4]}'


def output_unit(dof,quantity):
    return ('m' if dof%4<2 else 'rad')+{'displacement':'','velocity':'/s','acceleration':'/s²'}[quantity]


def modal_proxy(r):
    e=np.asarray(r.eigenvalues);a=np.abs(e)
    return ModalResult(r.speed_rad_s,e,a/(2*np.pi),np.divide(-e.real,a,out=np.zeros_like(a),where=a>0),r.eigenvectors,metadata=r.metadata)


def orbit_plot(ax,x,y,*,normalized=False,label=''):
    scale=max(float(max(np.abs(x),np.abs(y))),1e-30) if normalized else 1.
    theta=np.linspace(0,2*np.pi,181)
    xx=np.real(x*np.exp(1j*theta))/scale;yy=np.real(y*np.exp(1j*theta))/scale
    ax.plot(xx,yy,label=label or None);ax.annotate('',xy=(xx[4],yy[4]),xytext=(xx[0],yy[0]),arrowprops={'arrowstyle':'->'})
    ax.set_aspect('equal',adjustable='datalim');ax.set_xlabel('X normalizado' if normalized else 'X [m]');ax.set_ylabel('Y normalizado' if normalized else 'Y [m]')
    return xx,yy


def present(record,selection,*,dark=False):
    r=record.execution.result;m=record.model;case=record.execution.case
    opts={**case.options,**selection}
    if isinstance(r,ClearanceResult):return present_clearance(r,opts,dark)
    tabs=tabs_for(r);view=opts.get('view',tabs[0][0])
    if view not in dict(tabs):view=tabs[0][0]
    dof=int(opts.get('output_dof',0));inp=int(opts.get('input_dof',0));ndof=4*len(m.nodes)
    if not (0<=dof<ndof and 0<=inp<ndof):raise ValueError('GL selecionado fora do modelo de origem do resultado.')
    quantity=opts.get('response','displacement');quantity=quantity if quantity in ('displacement','velocity','acceleration') else 'displacement'
    point=max(0,int(opts.get('point_index',0)));mode=max(0,int(opts.get('mode_index',0)));note=''
    fig,ax=base_figure(dark);headers=[];rows=[]
    def message(text):
        nonlocal note
        note=text;ax.text(.5,.5,text,ha='center',va='center',wrap=True,transform=ax.transAxes)
    def series(x,y,xlabel,ylabel,label=None):
        ax.plot(x,y,label=label);ax.set_xlabel(xlabel);ax.set_ylabel(ylabel)
    def table(x,y,xname,yname):
        nonlocal headers,rows
        headers=[xname,yname];rows=[[float(a),float(b)] for a,b in zip(np.ravel(x),np.ravel(y))]
    if isinstance(r,StaticResult):
        if view=='deflection':
            series(r.node_positions,r.displacement_y,'Posição axial [m]','Deflexão Y [m]');table(r.node_positions,r.displacement_y,'Z [m]','Y [m]')
        elif view in ('shear','moment'):
            y=r.shear if view=='shear' else r.bending_moment;u='N' if view=='shear' else 'N·m'
            series(r.station_positions,y,'Posição axial [m]',u);table(r.station_positions,y,'Z [m]',u)
        elif view=='reactions':
            y=np.asarray(r.reactions).ravel();x=np.arange(len(y));ax.bar(x,y);ax.set_xlabel('Índice do vetor de reações');ax.set_ylabel('Força de reação [N]')
            headers=['Índice Core','Reação [N]'];rows=[[int(i),float(v)] for i,v in enumerate(y)]
            # Core static response returns one vertical reaction per physical support.
            if len(y)==len(m.nodes):
                headers=['Nó','Reação Y [N]'];rows=[[n.number,float(v)] for n,v in zip(m.nodes,y)];ax.set_xticks(x,[str(n.number) for n in m.nodes]);ax.set_xlabel('Nó')
            elif len(y)==len(r.support_nodes):
                headers=['Nó do apoio','Reação Y [N]'];rows=[[int(n),float(v)] for n,v in zip(r.support_nodes,y)];ax.set_xticks(x,[str(n) for n in r.support_nodes]);ax.set_xlabel('Nó do apoio')
        else:
            y=np.concatenate([np.ravel(r.shaft_weights),np.ravel(r.disk_loads)]);ax.bar(np.arange(len(y)),y);ax.set_ylabel('Peso / carga [N]');ax.set_xlabel('Elementos de eixo, depois discos')
            headers=['Origem','Índice / nó','Carga [N]'];rows=[['Eixo',i+1,float(v)] for i,v in enumerate(r.shaft_weights)]+[['Disco',int(n),float(v)] for n,v in zip(r.disk_nodes,r.disk_loads)]
        note='Gravidade calculada pelo Core; não inclui carregamentos adicionais não suportados pelo caso estático.'
    elif isinstance(r,(FrequencyResponseMatrixResult,ForcedResponseResult,*HARMONIC)):
        matrix=isinstance(r,FrequencyResponseMatrixResult);forced=isinstance(r,ForcedResponseResult)
        independent=matrix or forced or case.kind in ('auxiliary_frequency_response','foundation_frequency_response')
        omega=np.asarray(r.frequency_rad_s if (matrix or forced) else r.speeds_rad_s)
        x=omega/(2*np.pi) if independent else np.asarray(rad_s_to_rpm(omega));xlabel='Frequência de excitação [Hz]' if independent else 'Rotação [rpm]'
        point=min(point,len(x)-1)
        if matrix:
            data=getattr(r,{'displacement':'H_disp','velocity':'H_vel','acceleration':'H_acc'}[quantity]);values=data[dof,inp,:]
            unit=output_unit(dof,quantity)+' / '+('N' if inp%4<2 else 'N·m')
        elif forced:
            data=getattr(r,quantity);values=data[dof,:];unit=output_unit(dof,quantity)
        else:data=r.response;values=data[dof,:];unit=output_unit(dof,'displacement')
        if view=='phase':series(x,np.angle(values,deg=True),xlabel,'Fase [°]')
        elif view=='polar':
            series(values.real,values.imag,f'Re [{unit}]',f'Im [{unit}]');ax.scatter([values.real[point]],[values.imag[point]],marker='x');ax.set_aspect('equal',adjustable='datalim')
        elif view=='orbit':
            data=r.displacement if forced else r.response
            orbit_plot(ax,data[(dof//4)*4,point],data[(dof//4)*4+1,point]);note='Órbita de deslocamento físico; não normalizada.'
        elif view=='ods':
            proxy=ModalResult(float(omega[point]),np.array([1j*omega[point]]),np.array([omega[point]/(2*np.pi)]),np.array([0.]),np.asarray(data[:,point:point+1]))
            # Physical ODS scale is retained in the table; 3D rendering normalizes
            # the geometry and explicitly labels the visual amplification.
            fig=modal_figure(m,proxy,0,dark=dark,phase=float(opts.get('phase',0)),scale=1.,elev=20,azim=-62)
            note='ODS calculada: desenho 3D normalizado para visualização. Tabela e exportação mantêm amplitudes físicas.'
        elif view=='matrix':
            image=ax.imshow(np.abs(data[:,:,point]),aspect='auto',origin='lower');fig.colorbar(image,ax=ax,label='Módulo · unidades dependem do par de GL')
            ax.set_xlabel('GL de entrada (zero-based)');ax.set_ylabel('GL de saída (zero-based)')
            headers=['GL saída','GL entrada','Real [SI]','Imag [SI]'];rows=[[i,j,float(data[i,j,point].real),float(data[i,j,point].imag)] for i in range(ndof) for j in range(ndof)]
        elif view in ('residual','condition'):
            val=r.residual if view=='residual' else r.condition_estimate
            val=np.asarray(val)
            if val.ndim>1:
                if val.shape[-1]==len(x):val=np.max(val.reshape((-1,len(x))),axis=0)
                else:raise ValueError(f'Forma de diagnóstico não reconhecida: {val.shape}')
            series(x,val,xlabel,'Resíduo relativo máximo' if view=='residual' else 'Estimativa de condicionamento');table(x,val,xlabel,view)
        elif view=='force':
            fv=r.force_complex[dof,:];series(x,np.abs(fv),xlabel,'N' if dof%4<2 else 'N·m');table(x,np.abs(fv),xlabel,'Módulo da força')
        else:series(x,np.abs(values),xlabel,unit);ax.scatter([x[point]],[abs(values[point])],marker='x')
        if not rows:
            headers=[xlabel,f'Re [{unit}]',f'Im [{unit}]',f'Módulo [{unit}]','Fase [°]']
            rows=[[float(xv),float(v.real),float(v.imag),float(abs(v)),float(np.angle(v,deg=True))] for xv,v in zip(x,values)]
        if isinstance(r,AsymmetricFrequencyResponseResult):note+=' Desbalanceamento estático no referencial GIRANTE. Não representa uma órbita harmônica nesse referencial; valores não transformados em resposta estacionária.'
    elif isinstance(r,(GeneralTimeResponseResult,TransientResult)):
        general=isinstance(r,GeneralTimeResponseResult);t=np.asarray(r.time_s);data=getattr(r,quantity) if general else r.response
        values=np.asarray(data[dof]);unit=output_unit(dof,quantity if general else 'displacement')
        if view=='orbit':
            q=r.displacement if general else r.response;ax.plot(q[(dof//4)*4],q[(dof//4)*4+1]);ax.set_xlabel('X [m]');ax.set_ylabel('Y [m]');ax.set_aspect('equal',adjustable='datalim')
            headers=['t [s]','X [m]','Y [m]'];rows=[[float(v),float(a),float(b)] for v,a,b in zip(t,q[(dof//4)*4],q[(dof//4)*4+1])]
        elif view=='spectrum':
            spectrum=time_spectrum(t,values)
            if spectrum is None:message('DFFT indisponível: a grade temporal não é uniforme. Nenhuma reamostragem automática.')
            else:series(*spectrum,'Frequência [Hz]',unit);table(*spectrum,'Frequência [Hz]',unit)
        elif view=='speed':
            v=r.rotor_speed_rad_s if general else r.speed_rad_s
            if v is None:
                v=case.parameters.get('rotor_speed_rad_s')
                if v is None:message('Este resultado não contém histórico de rotação.')
            if v is not None:
                v=np.broadcast_to(np.asarray(v),t.shape);series(t,rad_s_to_rpm(v),'Tempo [s]','Rotação [rpm]');table(t,rad_s_to_rpm(v),'t [s]','rpm')
        elif view=='force':
            v=r.force[dof] if general else r.forcing
            if v is None:message('Este contrato não retorna histórico de força. Consulte a definição de excitação do caso.')
            else:
                v=np.asarray(v);v=v[dof] if v.ndim==2 and v.shape[0]==ndof else v.ravel()
                if len(v)!=len(t):raise ValueError('Eixo temporal e vetor de excitação têm dimensões diferentes.')
                fu=('N' if dof%4<2 else 'N·m') if general else 'Excitação de base (SI; contrato do Core)'
                series(t,v,'Tempo [s]',fu);table(t,v,'t [s]',fu)
        elif view in ('residual','iterations'):
            v=r.absolute_residual if view=='residual' else r.iterations
            series(t[1:],v[1:],'Tempo [s]','Norma do resíduo absoluto' if view=='residual' else 'Iterações de Newton');table(t,v,'t [s]',view)
            note='O instante inicial é prescrito pelo Core; não representa uma iteração convergida.'
        else:series(t,values,'Tempo [s]',unit);table(t,values,'t [s]',unit)
    elif isinstance(r,SPECIAL_MODAL):
        proxy=modal_proxy(r);ev=proxy.eigenvalues;ids=np.where(ev.imag>0)[0];k=int(ids[min(mode,len(ids)-1)]) if len(ids) else min(mode,len(ev)-1)
        if view=='eigenvalues':
            ax.scatter(ev.real,ev.imag/(2*np.pi));ax.axvline(0,linestyle='--');ax.set_xlabel('Re(λ) [s⁻¹]');ax.set_ylabel('Im(λ) / 2π [Hz]')
        elif proxy.eigenvectors is None:message('Autovetores não calculados. Reexecute com a opção ativada.')
        elif view=='orbits':
            vec=proxy.eigenvectors[:,k];orbit_plot(ax,vec[(dof//4)*4],vec[(dof//4)*4+1],normalized=True)
        else:fig=modal_figure(m,proxy,k,dark=dark,phase=float(opts.get('phase',0)),scale=float(opts.get('amplitude',1)),elev=20,azim=-62)
        headers=['Índice Core','Re(λ) [s⁻¹]','Im(λ) [rad/s]','fn [Hz]','fd [Hz]','ζ','Estabilidade']
        rows=[[i+1,float(e.real),float(e.imag),float(proxy.natural_frequency_hz[i]),float(abs(e.imag)/(2*np.pi)),float(proxy.damping_ratio[i]),'Instável' if e.real>0 else 'Estável / neutro'] for i,e in enumerate(ev)]
        note='Referencial GIRANTE; frequências não transformadas em pseudo-frequências estacionárias.' if isinstance(r,AsymmetricModalResult) else 'Rotor coaxial: fatores de velocidade preservados; linhas dos rotores desenhadas separadamente.'
    elif isinstance(r,CriticalSpeedResult):
        c=np.asarray(r.critical_speeds_rad_s);point=min(point,max(0,len(c)-1));headers=['Crítica','Velocidade [rpm]','Iterações','Convergiu']
        rows=[[i+1,float(rad_s_to_rpm(w)),int(r.iterations[i]) if r.iterations is not None else 'não retornado',bool(r.converged[i]) if r.converged is not None else 'não retornado'] for i,w in enumerate(c)]
        if view=='modes':
            if r.mode_shapes is None or not len(c):message('Formas modais não solicitadas ou indisponíveis para o método. Reconfigure o caso.')
            else:
                proxy=ModalResult(float(c[point]),np.asarray([1j*c[point]]),np.asarray([c[point]/(2*np.pi)]),np.zeros(1),r.mode_shapes[:,point:point+1])
                fig=modal_figure(m,proxy,0,dark=dark,phase=float(opts.get('phase',0)),scale=1.,elev=20,azim=-62)
        elif view=='convergence':
            if r.iterations is None:message('O método escolhido não retornou diagnóstico iterativo.')
            else:ax.bar(np.arange(len(c))+1,r.iterations);ax.set_xlabel('Crítica');ax.set_ylabel('Iterações')
        else:ax.scatter(np.arange(len(c))+1,rad_s_to_rpm(c));ax.set_xlabel('Crítica');ax.set_ylabel('Velocidade [rpm]')
        note='Raízes não convergidas permanecem identificadas, não são promovidas a resultados convergidos.'
    elif isinstance(r,UCSResult):
        n=len(r.intersection_speed_rad_s);point=min(point,max(0,n-1));fac=1. if opts.get('speed_units','RPM')=='rad/s' else 60/(2*np.pi);unit='rad/s' if fac==1 else 'rpm'
        if view=='map':
            k=np.asarray(r.stiffness_log_n_m)
            for i,line in enumerate(r.natural_frequency_rad_s):ax.plot(k,np.asarray(line)*fac,label=f'Ramo {i+1}')
            for key in r.coefficient_families:
                val=r.bearing_kxx_n_m if key.lower()=='kxx' else r.bearing_kyy_n_m
                ax.plot(val,r.bearing_speed_rad_s*fac,linestyle='--',label=key.upper())
            if n:
                ax.scatter(r.intersection_stiffness_n_m,r.intersection_speed_rad_s*fac,label='Interseções nativas');ax.scatter([r.intersection_stiffness_n_m[point]],[r.intersection_speed_rad_s[point]*fac],marker='x',s=80)
            ax.set_xscale('log');ax.set_yscale('log');ax.set_xlabel('Rigidez do apoio [N/m]');ax.set_ylabel('Frequência / velocidade ['+unit+']');ax.legend(fontsize=8)
        elif view=='intersections':
            if not n:message('O Core não encontrou interseções neste intervalo.')
            else:series(r.intersection_stiffness_n_m,r.intersection_speed_rad_s*fac,'Rigidez [N/m]',unit)
        elif not n:message('Não há pontos críticos para inspeção modal.')
        else:
            w=np.asarray(r.critical_wn_rad_s)[:,point];ax.scatter(np.arange(len(w))+1,w*fac);ax.set_xlabel('Índice modal');ax.set_ylabel('Frequência natural ['+unit+']')
        if view=='critical_modes' and n:
            headers=['Modo','fn ['+unit+']','fd ['+unit+']','ζ','δ'];rows=[[i+1,float(r.critical_wn_rad_s[i,point]*fac),float(r.critical_wd_rad_s[i,point]*fac),float(r.critical_damping_ratio[i,point]),float(r.critical_log_dec[i,point])] for i in range(r.critical_wn_rad_s.shape[0])]
        else:
            headers=['Interseção','Ramo','Coeficiente','Rigidez [N/m]','Velocidade ['+unit+']'];rows=[[i+1,int(r.intersection_mode_index[i])+1,str(r.intersection_coefficient[i]),float(r.intersection_stiffness_n_m[i]),float(r.intersection_speed_rad_s[i]*fac)] for i in range(n)]
        note=f'UCS nativo · Rouch síncrono: {r.synchronous} · política do mancal: {r.bearing_speed_policy}. Não é análise de resposta amortecida.'
    elif isinstance(r,Level1Result):
        q=np.asarray(r.cross_coupled_stiffness_n_m);point=min(point,len(q)-1)
        if view=='log_dec':series(q,r.log_dec,'Rigidez cruzada Q [N/m]','Decremento logarítmico δ');ax.axhline(0,linestyle='--')
        elif view=='eigenvalues':
            ax.scatter(np.asarray(r.eigenvalue_real)[:,point],np.asarray(r.eigenvalue_imag)[:,point]/(2*np.pi));ax.axvline(0,linestyle='--');ax.set_xlabel('Re(λ) [s⁻¹]');ax.set_ylabel('Im(λ)/2π [Hz]')
        else:
            for i in range(np.asarray(r.natural_frequency_rad_s).shape[0]):ax.plot(q,r.natural_frequency_rad_s[i,:]/(2*np.pi))
            ax.set_xlabel('Q [N/m]');ax.set_ylabel('Frequência natural [Hz]')
        headers=['Q [N/m]','δ selecionado','Modo Core (1-based)'];rows=[[float(a),float(b),int(c)+1] for a,b,c in zip(q,r.log_dec,r.selected_mode_index)]
        note='A seleção modal e as classificações de precessão vêm do Core. δ<0 indica crescimento modal para este modelo.'
    elif isinstance(r,API617UnbalanceResult):
        if view=='placement':
            ax.bar(r.nodes,r.unbalance_magnitude_kg_m);ax.set_xlabel('Nó');ax.set_ylabel('Desbalanceamento [kg·m]')
            headers=['Nó','Magnitude [kg·m]','Fase [rad]','Carga estática [kg]'];rows=[[int(n),float(u),float(p),float(w)] for n,u,p,w in zip(r.nodes,r.unbalance_magnitude_kg_m,r.unbalance_phase_rad,r.static_load_kg)]
        else:
            values=r.mode_major_axis if view=='major_axis' else r.mode_sign
            values=np.asarray(values).ravel();x=np.arange(1,len(values)+1)
            series(x,values,'Índice nodal do vetor modal','Eixo maior normalizado' if view=='major_axis' else 'Sinal modal');table(x,values,'Índice nodal',view)
        note=f'Posicionamento A7 nativo, modo direto solicitado {r.requested_forward_mode+1}. Não certifica conformidade integral da máquina com API 617.'
    elif isinstance(r,tuple) and len(r)==5:
        M,C,K,mask,ecc=r
        if view in ('M','C','K'):
            mat=np.asarray({'M':M,'C':C,'K':K}[view]);im=ax.imshow(mat,origin='lower',aspect='auto');fig.colorbar(im,ax=ax,label='SI por par de GL');ax.set_xlabel('GL coluna');ax.set_ylabel('GL linha')
            headers=['Linha','Coluna',view+' [SI por GL]'];rows=[[i,j,float(mat[i,j])] for i in range(mat.shape[0]) for j in range(mat.shape[1])]
        elif view=='constraints':
            val=np.asarray(mask).ravel();ax.step(np.arange(len(val)),val);ax.set_xlabel('GL (zero-based)');ax.set_ylabel('Restrito');table(np.arange(len(val)),val,'GL','Máscara nativa')
        else:
            val=np.asarray(ecc).ravel();ax.bar(np.arange(len(val)),val);ax.set_xlabel('Mancal (ordem do modelo, zero-based)');ax.set_ylabel('Excentricidade relativa');table(np.arange(len(val)),val,'Mancal','Excentricidade')
        note='Matrizes globais dos mancais: forças e momentos versus translações e rotações. Valores nulos em GL rígidos não significam apoio livre.'
    else:raise TypeError(type(r).__name__)
    if fig.axes and fig.axes[0] is ax:
        ax.set_title(dict(tabs)[view],fontsize=12,pad=14);fig.subplots_adjust(left=.12,right=.93,bottom=.18,top=.89)
    return Presented(fig,headers,rows,note)
