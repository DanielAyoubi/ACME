import math
import time
from datetime import datetime, timedelta

from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.devices import DEVICE_TYPES
from src.experiment import humidity_cycle
from src.worker import data_units, rh_columns

CURRENT_STEP_COLOR = QColor(222, 235, 250)
FIRST_CONTROL_COLUMN = 3  # after Hold, Condition and Value


def spin_box(minimum, maximum, value, suffix, step=1.0):
    box = QDoubleSpinBox()
    box.setRange(minimum, maximum)
    box.setValue(value)
    box.setSuffix(suffix)
    box.setSingleStep(step)
    return box


def hours_minutes(minutes):
    hours, minutes = divmod(round(minutes), 60)
    return f"{hours} h {minutes} min" if hours else f"{minutes} min"


# Edits a step table cell with a drop-down of fixed choices, like the valve positions.
class ChoiceDelegate(QStyledItemDelegate):
    def __init__(self, choices, parent):
        super().__init__(parent)
        self.choices = choices

    def createEditor(self, parent, option, index):
        box = QComboBox(parent)
        box.addItems(self.choices)
        return box

    def setEditorData(self, editor, index):
        editor.setCurrentText(index.data())

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText())


class ExperimentPanel(QWidget):
    def __init__(self, send):
        super().__init__()
        self.send = send
        self.controls = []  # (device name, control, unit), one table column each
        self.running = False
        self.steps = []  # the steps last sent to the worker, so edits to the table mid-run change nothing
        self.settle_minutes = 0  # from the setup's "conditions", for the progress line
        self.highlighted_row = (
            None  # the row currently colored as the running step, or None
        )

        self.humid_mfc = QComboBox()
        self.dry_mfc = QComboBox()
        self.total_flow = spin_box(0, 100, 2.0, " L/min", step=0.1)
        self.low = spin_box(0, 100, 0, " %")
        self.high = spin_box(0, 100, 100, " %")
        self.step = spin_box(0.1, 100, 5, " %")
        self.hold = spin_box(0.1, 10000, 3, " min")
        self.start_at = QComboBox()
        self.start_at.addItems(["Lowest (ramp up)", "Highest (ramp down)"])
        self.cycles = QSpinBox()
        self.cycles.setRange(1, 1000)
        self.cycles.setValue(1)
        fill_button = QPushButton("Fill table")
        fill_button.clicked.connect(self.fill_humidity_cycle)

        cycle_form = QFormLayout()
        cycle_form.addRow("Humid air MFC", self.humid_mfc)
        cycle_form.addRow("Dry air MFC", self.dry_mfc)
        cycle_form.addRow("Total flow", self.total_flow)
        cycle_form.addRow("Lowest humid share", self.low)
        cycle_form.addRow("Highest humid share", self.high)
        cycle_form.addRow("Step", self.step)
        cycle_form.addRow("Hold per step", self.hold)
        cycle_form.addRow("Start at", self.start_at)
        cycle_form.addRow("Cycles", self.cycles)
        cycle_form.addRow(fill_button)
        cycle_form.addRow(
            QLabel("Humid share = % of the total flow sent\nthrough the humid MFC.")
        )
        cycle_group = QGroupBox("Humidity cycle")
        cycle_group.setLayout(cycle_form)
        cycle_group.setMaximumWidth(330)

        self.name = QLineEdit()
        self.name.setPlaceholderText("optional, added to the CSV and PNG file names")
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Experiment name"))
        name_row.addWidget(self.name)

        self.table = QTableWidget()
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.itemChanged.connect(self.update_summary)
        add_button = QPushButton("Add step")
        add_button.clicked.connect(lambda: self.add_step())
        duplicate_button = QPushButton("Duplicate selected")
        duplicate_button.clicked.connect(self.duplicate_steps)
        remove_button = QPushButton("Remove selected")
        remove_button.clicked.connect(self.remove_step)
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.clear_steps)
        self.summary = QLabel()
        self.start_button = QPushButton("Start experiment")
        self.start_button.clicked.connect(self.start_or_stop)
        self.start_button.setEnabled(False)

        table_buttons = QHBoxLayout()
        table_buttons.addWidget(add_button)
        table_buttons.addWidget(duplicate_button)
        table_buttons.addWidget(remove_button)
        table_buttons.addWidget(clear_button)
        table_buttons.addStretch()
        table_buttons.addWidget(self.summary)
        table_buttons.addWidget(self.start_button)

        steps_layout = QVBoxLayout()
        steps_layout.addLayout(name_row)
        steps_layout.addWidget(
            QLabel("Steps: each holds for its time, or until its condition has settled at the value, "
                   "whichever comes first.\nAn RH condition runs the RH control loop on its MFCs. "
                   "An empty cell leaves that setpoint unchanged.")
        )
        steps_layout.addWidget(self.table)
        steps_layout.addLayout(table_buttons)

        layout = QHBoxLayout(self)
        layout.addWidget(cycle_group)
        layout.addLayout(steps_layout)

    def configure(self, setup):
        self.settle_minutes = setup["conditions"]["settle_minutes"]
        self.controls = []
        choices = {}  # (device name, control) -> drop-down items, like ["", "1 closed", "2 nitrogen", "3 oxygen"]
        self.humid_mfc.clear()
        self.dry_mfc.clear()
        for device in setup["devices"]:
            device_class = DEVICE_TYPES[device["type"]]
            for control, unit in device_class.controls.items():
                self.controls.append((device["name"], control, unit))
                if isinstance(unit, list):
                    # Names from the setup are added after the numbers; "" leaves the setpoint unchanged.
                    names = device.get(f"{control}_names", "").split(",") + [""] * len(unit)
                    choices[(device["name"], control)] = [""] + [
                        f"{choice} {name.strip()}".strip() for choice, name in zip(unit, names)]
            if "flow" in device_class.controls:
                self.humid_mfc.addItem(device["name"])
                self.dry_mfc.addItem(device["name"])
        if self.dry_mfc.count() > 1:
            self.dry_mfc.setCurrentIndex(1)

        # A condition can be any RH or temperature reading.
        conditions = rh_columns(setup) + [column for column in data_units(setup)
                                          if column.endswith(" temperature")]

        self.table.setRowCount(0)
        self.table.setColumnCount(FIRST_CONTROL_COLUMN + len(self.controls))
        self.table.setItemDelegateForColumn(1, ChoiceDelegate([""] + conditions, self.table))
        headers = ["Hold (min)", "Condition", "Value"]
        for column, (name, control, unit) in enumerate(self.controls, start=FIRST_CONTROL_COLUMN):
            delegate = None  # a plain text cell
            if isinstance(unit, list):  # choices instead of a unit, like the valve positions
                delegate = ChoiceDelegate(choices[(name, control)], self.table)
                unit = "/".join(str(choice) for choice in unit)
            self.table.setItemDelegateForColumn(column, delegate)
            headers.append(f"{name} {control} ({unit})")
        self.table.setHorizontalHeaderLabels(headers)
        self.table.resizeColumnsToContents()  # the header names are the widest thing in a column
        self.update_summary()

    def add_step(self, step=None):
        # Signals stay blocked until the row is complete, so update_summary never sees half a row.
        self.table.blockSignals(True)
        row = self.table.rowCount()
        self.table.insertRow(row)
        texts = [""] * (FIRST_CONTROL_COLUMN + len(self.controls))
        if step:
            texts[0] = f"{step['minutes']:g}"
            for column, (name, control, unit) in enumerate(self.controls, start=FIRST_CONTROL_COLUMN):
                if (name, control) in step["setpoints"]:
                    texts[column] = f"{step['setpoints'][(name, control)]:g}"
        for column, text in enumerate(texts):
            self.table.setItem(row, column, QTableWidgetItem(text))
        self.table.blockSignals(False)
        self.update_summary()

    def duplicate_steps(self):
        rows = sorted({index.row() for index in self.table.selectedIndexes()})
        if not rows:
            return
        copies = [[self.table.item(row, column).text() for column in range(self.table.columnCount())]
                  for row in rows]
        # The copies go right below the selection, so a selected block repeats in order.
        self.table.blockSignals(True)
        for offset, texts in enumerate(copies, start=rows[-1] + 1):
            self.table.insertRow(offset)
            for column, text in enumerate(texts):
                self.table.setItem(offset, column, QTableWidgetItem(text))
        self.table.blockSignals(False)
        self.update_summary()

    def remove_step(self):
        rows = {index.row() for index in self.table.selectedIndexes()}
        # From the bottom up, so removing a row does not shift the ones still to remove.
        for row in sorted(rows, reverse=True):
            self.table.removeRow(row)
        self.update_summary()

    def clear_steps(self):
        self.table.setRowCount(0)
        self.update_summary()

    def fill_humidity_cycle(self):
        if (
            self.humid_mfc.currentText() == ""
            or self.humid_mfc.currentText() == self.dry_mfc.currentText()
        ):
            QMessageBox.warning(
                self,
                "Humidity cycle",
                "Choose two different MFCs for humid and dry air.",
            )
            return
        if self.low.value() >= self.high.value():
            QMessageBox.warning(
                self,
                "Humidity cycle",
                "The lowest humid share must be below the highest.",
            )
            return
        steps = humidity_cycle(
            self.humid_mfc.currentText(),
            self.dry_mfc.currentText(),
            self.total_flow.value(),
            self.low.value(),
            self.high.value(),
            self.step.value(),
            self.hold.value(),
            self.cycles.value(),
            self.start_at.currentIndex() == 1,
        )
        self.table.setRowCount(0)
        for step in steps:
            self.add_step(step)

    def steps_from_table(self):
        steps = []
        for row in range(self.table.rowCount()):
            hold = self.table.item(row, 0).text().strip()
            condition = self.table.item(row, 1).text()
            value = self.table.item(row, 2).text().strip()
            if not hold and not condition:
                raise ValueError(f"Step {row + 1} needs a hold time, a condition, or both.")
            if condition and not value:
                raise ValueError(f"Step {row + 1}: give the value {condition} should settle at.")
            if value and not condition:
                raise ValueError(f"Step {row + 1} has a value but no condition.")
            try:
                setpoints = {}
                for column, (name, control, unit) in enumerate(self.controls, start=FIRST_CONTROL_COLUMN):
                    text = self.table.item(row, column).text().strip()
                    if text:
                        setpoints[(name, control)] = float(text.split()[0])  # "2 nitrogen" is 2
                steps.append(
                    {
                        "minutes": float(hold) if hold else None,
                        "condition": (condition, float(value)) if condition else None,
                        "setpoints": setpoints,
                    }
                )
            except ValueError:
                raise ValueError(
                    f"Step {row + 1} has a hold time, value or setpoint that is not a number."
                )
            # Catch a mistyped valve position now, not hours into the experiment.
            for name, control, unit in self.controls:
                value = setpoints.get((name, control))
                if isinstance(unit, list) and value is not None and value not in unit:
                    choices = "/".join(str(choice) for choice in unit)
                    raise ValueError(f"Step {row + 1}: {name} {control} must be {choices}.")
        return steps

    def update_summary(self):
        minutes = 0
        conditions = 0
        for row in range(self.table.rowCount()):
            # How long a step with a condition takes is only known once it has settled.
            if self.table.item(row, 1).text():
                conditions += 1
                continue
            try:
                minutes += float(self.table.item(row, 0).text())
            except ValueError:
                pass
        text = f"{self.table.rowCount()} steps, {hours_minutes(minutes)}"
        if conditions:
            text += f" + {conditions} condition{'s' if conditions > 1 else ''}"
        self.summary.setText(text)

    def start_or_stop(self):
        if self.running:
            self.send(("stop",))
            return
        try:
            steps = self.steps_from_table()
        except ValueError as error:
            QMessageBox.warning(self, "Experiment", str(error))
            return
        if not steps:
            QMessageBox.warning(self, "Experiment", "The step table is empty.")
            return
        self.steps = steps
        self.send(("start", steps, self.name.text()))
        self.show_step(1)

    def set_connected(self, connected):
        self.start_button.setEnabled(connected)
        if not connected:
            self.show_step("")

    def show_step(self, step):
        """Called with the step number from each new data row ("" when no experiment runs)."""
        self.running = step != ""
        # The name is read when the log file opens, so editing it mid-run would change nothing.
        self.name.setEnabled(not self.running)
        if self.running:
            self.start_button.setText(
                f"Stop experiment (step {step}/{len(self.steps)})"
            )
            self.highlight_row(step - 1)
            self.table.scrollToItem(self.table.item(step - 1, 0))
        else:
            self.start_button.setText("Start experiment")
            self.highlight_row(None)

    def highlight_row(self, row):
        if self.highlighted_row is not None:
            for column in range(self.table.columnCount()):
                item = self.table.item(self.highlighted_row, column)
                if item:
                    # No brush, so the item falls back to its default colors.
                    item.setBackground(QBrush())
                    item.setForeground(QBrush())
        if row is not None:
            for column in range(self.table.columnCount()):
                item = self.table.item(row, column)
                if item:
                    item.setBackground(CURRENT_STEP_COLOR)
                    # Dark text, because in dark mode the default text is white on this light color.
                    item.setForeground(QColor("black"))
        self.highlighted_row = row

    def describe(self, step):
        units = {}
        for name, control, unit in self.controls:
            units[(name, control)] = "" if isinstance(unit, list) else unit
        parts = [
            f"{name} {control} {value:g} {units.get((name, control), '')}".strip()
            for (name, control), value in step["setpoints"].items()
        ]
        if step["condition"] is not None:
            column, target = step["condition"]
            parts.append(f"{column} to {target:g}")
        return ", ".join(parts) or "no changes"

    def progress(self, row):
        step = row["step"]
        if step == "":
            return ""
        current = self.steps[step - 1]
        later = self.steps[step:]  # the steps after the current one
        parts = [f"Step {step}/{len(self.steps)}" + ("" if later else " (last)")]

        if current["condition"] is not None:
            column, target = current["condition"]
            text = f"waiting for {column} to settle at {target:g}"
            if row[column] is not None:
                text += f" (now {row[column]:.1f})"
            if row["settled since"] is not None:
                settled = (time.time() - row["settled since"]) / 60
                text += f", settled {hours_minutes(settled)} of {hours_minutes(self.settle_minutes)}"
            parts.append(text)

        step_left = None  # stays None for a step that only waits for its condition
        if row["step end"] is not None:
            step_left = max(0.0, row["step end"] - time.time())
        if later:
            if step_left is None:
                when = "once settled"
            elif current["condition"] is not None:
                when = f"at the latest in {hours_minutes(math.ceil(step_left / 60))}"
            else:
                when = f"in {hours_minutes(math.ceil(step_left / 60))}"
            parts.append(f"next {when}: step {step + 1}, {self.describe(later[0])}")

        # The end time is only known when no step from here on waits for a condition.
        if step_left is not None and all(later_step["condition"] is None for later_step in [current] + later):
            total_left = step_left + 60 * sum(later_step["minutes"] for later_step in later)
            ends = datetime.now() + timedelta(seconds=total_left)
            parts.append(f"experiment ends in {hours_minutes(math.ceil(total_left / 60))} (at {ends:%H:%M})")
        return " · ".join(parts)
