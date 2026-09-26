from drm_core.analysis.modal import FIXED_WHIRL, MATCHED_WHIRL
from drm_studio.analysis_pages.modal_setup import ModalSetupDialog
from drm_studio.analysis_pages.campbell_setup import CampbellSetupDialog


def test_b17_modal_dialog_serializes_fixed_and_matched_whirl(qtbot):
    dialog=ModalSetupDialog()
    qtbot.addWidget(dialog)
    dialog.speed_field.setValue(3600.0)
    dialog.policy_combo.setCurrentIndex(dialog.policy_combo.findData(FIXED_WHIRL))
    dialog.whirl_field.setValue(1800.0)
    case=dialog.analysis_case()
    assert case.parameters["coefficient_policy"]==FIXED_WHIRL
    assert case.parameters["whirl_frequency_rad_s"]>0.0

    dialog.policy_combo.setCurrentIndex(dialog.policy_combo.findData(MATCHED_WHIRL))
    dialog.whirl_rtol.setValue(0.0002)
    dialog.whirl_max_iter.setValue(25)
    case=dialog.analysis_case()
    assert case.parameters["coefficient_policy"]==MATCHED_WHIRL
    assert case.parameters["whirl_rtol"]==0.0002
    assert case.parameters["whirl_max_iter"]==25


def test_b17_campbell_dialog_serializes_matched_whirl_policy(qtbot):
    dialog=CampbellSetupDialog()
    qtbot.addWidget(dialog)
    dialog.start_field.setValue(1000.0)
    dialog.end_field.setValue(2000.0)
    dialog.step_field.setValue(500.0)
    dialog.policy_combo.setCurrentIndex(dialog.policy_combo.findData(MATCHED_WHIRL))
    case=dialog.analysis_case()
    assert case.parameters["coefficient_policy"]==MATCHED_WHIRL
    assert len(case.parameters["speeds_rad_s"])==3
    assert case.parameters["with_eigenvectors"] is True
