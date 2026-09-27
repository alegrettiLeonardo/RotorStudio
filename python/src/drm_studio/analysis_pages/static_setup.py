from PySide6.QtWidgets import QDialog,QDialogButtonBox,QFormLayout,QLineEdit,QLabel
from drm_core import AnalysisCase

class StaticSetupDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowTitle('Static Analysis')
        form=QFormLayout(self)
        self.name_field=QLineEdit('Static — Gravity')
        form.addRow('Case name:',self.name_field)
        text=QLabel('Gravity: −9.8065 m/s² (vertical y).\nCircular shaft with at least two radial supports.\nSupports are treated as rigid radial restraints; seals are excluded.\nTapered shafts, linked supports and advanced bearings are unavailable.')
        text.setWordWrap(True);form.addRow(text)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);form.addRow(buttons)
    def analysis_case(self):
        return AnalysisCase('static',name=self.name_field.text().strip() or 'Static')
