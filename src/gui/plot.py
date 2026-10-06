import pyqtgraph as pg
from PyQt6.QtCore import Qt

MAX_POINTS = 5000  # about 3 hours at a 2 s poll interval


class LivePlot(pg.GraphicsLayoutWidget):
    """Stacked live plots, one panel per unit, sharing the time axis."""

    def __init__(self):
        super().__init__()
        self.setBackground("w")
        self.times = []
        self.values = {}
        self.curves = {}

    def configure(self, units):
        self.clear()
        self.times = []
        self.values = {}
        self.curves = {}
        panels = {}
        for column, unit in units.items():
            if unit == "":
                continue  # a reading without a unit, like a valve position, is not plotted
            if unit not in panels:
                panel = self.addPlot(row=len(panels), col=0, axisItems={"bottom": pg.DateAxisItem()})
                panel.setLabel("left", unit)
                panel.showGrid(x=True, y=True, alpha=0.3)
                panel.addLegend()
                if panels:
                    panel.setXLink(list(panels.values())[0])
                panels[unit] = panel
            panel = panels[unit]
            color = pg.intColor(len(panel.listDataItems()), hues=8)
            style = Qt.PenStyle.DashLine if column.endswith("setpoint") else Qt.PenStyle.SolidLine
            pen = pg.mkPen(color, width=2, style=style)
            self.curves[column] = panel.plot(name=column, pen=pen, connect="finite")
            self.values[column] = []

    def add(self, row):
        self.times.append(row["time"].timestamp())
        for column, values in self.values.items():
            if row[column] is None:
                values.append(float("nan"))  # leaves a gap in the line
            else:
                values.append(row[column])
        if len(self.times) > MAX_POINTS:
            del self.times[0]
            for values in self.values.values():
                del values[0]
        for column, curve in self.curves.items():
            curve.setData(self.times, self.values[column])

    def clear_data(self):
        self.times = []
        for column, curve in self.curves.items():
            self.values[column] = []
            curve.setData([], [])
