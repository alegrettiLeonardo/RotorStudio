import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QTableWidget,QTableWidgetItem,QAbstractItemView
from .io import record_data_table

class StaticResultView(QWidget):
    """Display native arrays only; no loads, reactions or diagrams are recomputed."""
    def __init__(self,record,parent=None):
        super().__init__(parent);self.record=record;self.result=record.execution.result
        layout=QVBoxLayout(self);self.stale_label=QLabel();layout.addWidget(self.stale_label)
        self.figure=Figure(figsize=(10,7),tight_layout=True)
        self.canvas=FigureCanvasQTAgg(self.figure);self.canvas.setMinimumHeight(340);layout.addWidget(self.canvas,1)
        r=self.result
        a,b,c,d=self.figure.subplots(2,2).flat
        a.plot(r.node_positions,r.displacement_y,'o-');a.set(title='Deflected shaft',ylabel='y (m)',xlabel='Position (m)')
        b.plot(r.station_positions,r.shear);b.set(title='Shearing force',ylabel='Force (N)',xlabel='Position (m)')
        c.plot(r.station_positions,r.bending_moment);c.set(title='Bending moment',ylabel='Moment (N m)',xlabel='Position (m)')
        d.axhline(0,color='gray');d.stem(r.node_positions,r.reactions,linefmt='g-',markerfmt='g^',basefmt=' ')
        if len(r.disk_nodes):d.stem(r.node_positions[r.disk_nodes-1],-r.disk_loads,linefmt='r-',markerfmt='rv',basefmt=' ')
        # Each shaft weight is displayed at its element centre, without integrating loads.
        d.stem((r.node_positions[:-1]+r.node_positions[1:])/2,-r.shaft_weights,linefmt='b-',markerfmt='bv',basefmt=' ')
        d.set(title='Reactions (green), disks (red), shaft (blue)',ylabel='Vertical force (N)',xlabel='Position (m)')
        columns,data=record_data_table(record)
        self.table=QTableWidget(len(data),len(columns));self.table.setHorizontalHeaderLabels(columns)
        for i,row in enumerate(data):
            for j,value in enumerate(row):self.table.setItem(i,j,QTableWidgetItem('' if np.isnan(value) else f'{value:.10g}'))
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.resizeColumnsToContents()
        self.table.setMaximumHeight(160);layout.addWidget(self.table)
        layout.addWidget(QLabel('Table entity: 1=node; 2=diagram station; 3=shaft element; 4=disk. Blank values are not applicable.'))
        self.refresh_stale()
    def refresh_stale(self):self.stale_label.setText('⚠ OUTDATED' if self.record.stale else 'CURRENT — Static gravity')
