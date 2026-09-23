from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'reference'/'matlab_v2'
def txt(name):return (SRC/name).read_text(errors='replace')

def test_shftasym_axial_force_branch_static_evidence():
    s=txt('shftasym.m')
    assert 'if nargin < 8, AxialForce = 0; end' in s
    assert 'Kre([1 4 5 8],[1 4 5 8]) = Kre([1 4 5 8],[1 4 5 8]) + KFxe;' in s
    assert 'Kre([2 3 6 7],[2 3 6 7]) = Kre([2 3 6 7],[2 3 6 7]) + KFye;' in s

def test_shftasym_cs_uses_already_scaled_ms_static_evidence():
    s=txt('shftasym.m')
    assert 'Ms = rhoI*Ms/(30*L);' in s
    assert 'Cs = rhoI*Ms/(15*L);' in s

def test_bearasym_type4_index_static_evidence():
    s=txt('bearasym.m')
    assert 'K1b1(3,4) = -Bearing_Def(i,9); K1b1(2,1) = Bearing_Def(i,9);' in s
    assert 'K1b1(4,3)' not in s

def test_chr_asym_nargout_paths_differ_in_k1b_static_evidence():
    s=txt('chr_asym.m')
    assert 'K = K0 + Kb + Rotor_Spd(i)*(K1+K1b) + Rotor_Spd(i)^2*K2;' in s
    assert 'K = K0 + Kb + Rotor_Spd(i)*K1 + Rotor_Spd(i)^2*K2;' in s

def test_foundation_bearing_predicate_is_tautology_for_numeric_bearing_types():
    for name in ('time_fdn.m','freq_fdn.m'):
        s=txt(name);assert 'Bearing_Def(ibearing,1) > 2 | Bearing_Def(ibearing,1) < 9' in s
    assert all((x>2) or (x<9) for x in range(-100,101))

def test_runup_mixes_explicit_jot_with_matlab_j_symbol_static_evidence():
    s=txt('runup.m')
    assert 'jot = sqrt(-1);' in s
    assert 'exp(jot*unbal_phase)*[1; -j]' in s
    assert 'exp(jot*unbal_phase)*[j; 1]' in s
    assert 'real(B*(d_phi*d_phi-j*dd_phi)*exp(j*phi))' in s
