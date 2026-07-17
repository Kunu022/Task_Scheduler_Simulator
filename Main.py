"""
Task Scheduler Simulator.

The task_scheduler module provides classes and functions for
creating tasks, managing dependencies, simulating execution,
and analyzing scheduling behavior.

Tasks can be loaded from an Excel file and done according
to their priorities, dependencies, and expiration dates.

The scheduler supports task history tracking, deadline checking,
priority boosting, and failure propagation.
"""

import pandas as fardin
import heapq
from itertools import count

ID_COUNTER = count()


def reset_counter():
    global ID_COUNTER
    ID_COUNTER = count()


# different states a task can be in
class TaskMode:
    DELETED = "DELETED"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    EXECUTING = "EXECUTING"
    WAITING = "WAITING"
    READY = "READY"


class Task:
    """
    Represents a task in the scheduler.
    A task stores its priority, dependencies, execution time,
    expiration date, current state, and execution history.
    """

    def __init__(self, priority, name, deps, time=0, expDate=-1):
        """
        Construct a new task.
        """
        self.taskID = next(ID_COUNTER)
        self.priority = priority
        self.name = name
        self.deps = deps
        self.time = time
        self.expDate = expDate
        self.depsScore = 0
        self.tempPriority = 0
        self.Mode = TaskMode.WAITING
        self.history = [{
            "time": 0,
            "event": "CREATED"
        }]
        self.start_time = None
        self.end_time = None

    def effective_priority(self):
        """
        Return the effective priority of the task.
        If a temporary priority boost exists, use it.
        Otherwise return the original priority.
        """
        if self.tempPriority > 0:
            return min(self.priority, self.tempPriority)
        return self.priority

    def expDate_miss(self, current_time):
        """
        Return True if the task cannot meet its deadline,
        even if execution starts immediately.
        """
        if self.expDate < 0:
            return False
        if current_time + self.time > self.expDate:
            return True
        return False

    def add_history(self, event, current_time):
        """
        Add an event to the task history.
        """
        self.history.append({
            "time": current_time,
            "event": event
        })

# ================
# Task queue
# ================
class TaskQueue:
    """
    Represents the scheduler queue.

    Responsible for storing tasks, maintaining priorities,
    resolving dependencies, and executing simulations.
    """
    def __init__(self):
        self.tasks = {}
        self.find = {}
        self.counter = count()
        self.heap = []
        self.failed = []

    def find_all_dependents(self, taskID, visited=None, stack=None):
        """
                Return all tasks that directly or indirectly depend
                on the specified task.
                """
        if visited is None:
            visited = set()
        if stack is None:
            stack = set()
        if taskID in stack:
            return visited
        if taskID in visited:
            return visited
        visited.add(taskID)
        stack.add(taskID)
        for temp in self.tasks.values():
            if taskID in temp.deps:
                self.find_all_dependents(temp.taskID, visited, stack)
        stack.discard(taskID)
        return visited


    def fail_failed_tasks(self, taskID, current_time):
        """
        Mark a task as failed and block all dependent tasks.
        """
        proxy_fail = self.find_all_dependents(taskID)
        blocked = []
        failed = self.tasks.get(taskID)
        for effected in proxy_fail:
            task = self.tasks.get(effected)
            if task and task.Mode not in [TaskMode.BLOCKED, TaskMode.FAILED]:
                if effected == taskID:
                    task.Mode = TaskMode.FAILED
                    task.add_history(TaskMode.FAILED, current_time)
                else:
                    task.Mode = TaskMode.BLOCKED
                    grouped = (TaskMode.BLOCKED,f" blocked due to \"{failed.name}\" failing")
                    task.add_history(grouped, current_time)
                blocked.append(effected)

                if effected in self.find:
                    temp = self.find.pop(effected)
                    temp[-1] = "DELETED"

        self.failed.append(blocked)
        return blocked

    def check_expDates(self, current_time):
        """
        Check all tasks and fail those that miss their
        expiration date.
        """
        failed = []
        for task in self.tasks.values():
            if task.Mode in [TaskMode.WAITING, TaskMode.EXECUTING]:
                if task.expDate_miss(current_time):
                    print(task.name, "MISSED DEADLINE!")
                    blocked = self.fail_failed_tasks(task.taskID, current_time)
                    failed.append(blocked)
        return failed

    def add(self, task):
        """
        Add a task to the priority queue.
        """
        self.tasks[task.taskID] = task
        entry = [task.effective_priority(), task.depsScore, next(self.counter), task.taskID, task]
        self.find[task.taskID] = entry
        heapq.heappush(self.heap, entry)

    def update_task(self, taskID, priorityNew=None, depsScoreNew=None):
        """
        Update a task entry inside the heap.
        """
        if taskID not in self.tasks:
            return

        task = self.tasks[taskID]
        old = self.find.pop(taskID, None)
        if old:
            old[-1] = "Deleted"

        priority = priorityNew if priorityNew is not None else task.effective_priority()
        deps = depsScoreNew if depsScoreNew is not None else task.depsScore

        tempTask = [priority, deps, next(self.counter), taskID, task]
        self.find[taskID] = tempTask
        heapq.heappush(self.heap, tempTask)

    def remove(self, taskID):
        """
        Remove and return a task from the queue.
        """
        while self.heap:
            poppedTask = heapq.heappop(self.heap)
            if poppedTask[-1] != "DELETED":
                task = poppedTask[-1]
                del self.find[taskID]
                return task

    def deps_score(self):
        """
        Compute the dependency score of all tasks.
        Tasks with more dependents receive a higher score.
        """
        for task in self.tasks.values():
            task.depsScore = 0
        for task in self.tasks.values():
            for d in task.deps:
                if d in self.tasks:
                    self.tasks[d].depsScore += 1

        for taskID in list(self.find.keys()):
            self.update_task(taskID, depsScoreNew=self.tasks[taskID].depsScore)

    def priority_boost(self):
        """
        Temporarily boost the priority of tasks whose
        dependents have higher priority.
        """
        changed = True
        for task in self.tasks.values():
            task.tempPriority = 0
        while changed:
            changed = False
            for task in self.tasks.values():
                best_boost = task.tempPriority
                for other in self.tasks.values():
                    if task.taskID in other.deps:
                        eff_other = other.effective_priority()
                        if eff_other < best_boost or best_boost == 0:
                            best_boost = eff_other
                            changed = True
                if best_boost != task.tempPriority:
                    task.tempPriority = best_boost
        for taskID in list(self.tasks.keys()):
            self.update_task(taskID, priorityNew=self.tasks[taskID].effective_priority())

    def execution_order(self, start_time=0):
        """
        Simulate task execution.

        Execute tasks according to priority and dependency
        constraints while checking deadlines.

        Return the execution order, failed tasks,
        and total execution time.
        """
        current_time = start_time
        order = []
        aborted = []

        in_degree = {
            tid: len(task.deps)
            for tid, task in self.tasks.items()
        }

        dependents = {
            tid: []
            for tid in self.tasks
        }
        for tid, task in self.tasks.items():
            for dep_id in task.deps:
                if dep_id in dependents:
                    dependents[dep_id].append(tid)

        failed_now = self.check_expDates(current_time)
        for group in failed_now:
            aborted.extend(group)

        ready = []
        for tid, task in self.tasks.items():
            if in_degree[tid] == 0 and task.Mode == TaskMode.WAITING:
                task.Mode = TaskMode.READY
                task.add_history(TaskMode.READY, current_time)
                heapq.heappush(ready, (task.effective_priority(), -task.depsScore,
                                       next(self.counter), task))

        order = []

        while ready:
            _, _, _, task = heapq.heappop(ready)

            # Double check deadline right before execution
            if task.expDate_miss(current_time):
                cascade = self.fail_failed_tasks(task.taskID, current_time)
                aborted.extend(cascade)
                continue

            # Execute the task
            task.Mode = TaskMode.EXECUTING
            task.add_history(TaskMode.EXECUTING, current_time)
            task.start_time = current_time
            current_time += task.time
            task.end_time = current_time
            task.Mode = TaskMode.COMPLETE
            task.add_history(TaskMode.COMPLETE, current_time)
            order.append(task.taskID)
            #Check deadlines after time passes
            self.check_expDates(current_time)

            #Update dependents
            for dep_tid in dependents[task.taskID]:
                #skip blocked/failed dependents
                if self.tasks[dep_tid].Mode in [TaskMode.BLOCKED, TaskMode.FAILED]:
                    continue
                in_degree[dep_tid] -= 1
                if in_degree[dep_tid] == 0:
                    t = self.tasks[dep_tid]
                    # Check if this task will miss its deadline
                    if t.expDate_miss(current_time):
                        cascade = self.fail_failed_tasks(t.taskID, current_time)
                        aborted.extend(cascade)
                    else:
                        t.Mode = TaskMode.READY
                        t.add_history(TaskMode.READY, current_time)
                        heapq.heappush(ready, (t.effective_priority(), -t.depsScore,
                                               next(self.counter), t))


        return order, aborted, current_time


# ========================
# Simulation interface
# Class for presentation of data to the gui
# ========================
class TaskGui:

    def __init__(self):
        self.tasks_table = []  # list of dicts: {priority, name, deps_list, time, expDate}
        self.queue = None
        self.results = None

    #read tasks from Excel file.
    def load_from_excel(self, filepath):
        """
        Load tasks from excel file
        """
        data = fardin.read_excel(filepath)
        self.tasks_table.clear()
        for _, row in data.iterrows():
            deps_name = row["deps"] if str(row["deps"]) != "nan" else ""
            self.tasks_table.append({
                "priority": row["priority"],
                "name": row["name"],
                "deps_list": [deps_name] if deps_name else [],
                "time": row["time"],
                "expDate": row["expDate"]
            })

    #create tasks and resolve dependencies.
    def add_task(self, priority, name, deps_list, time, expDate):
        """
        Manually add a task
        """
        self.tasks_table.append({
            "priority": priority, "name": name,
            "deps_list": deps_list, "time": time,
            "expDate": expDate
        })

    def run_simulation(self):
        """
        Build a fresh queue and execute a simulation.
        """
        reset_counter()
        self.queue = TaskQueue()
        task_objects = {}
        # this is foor making the tasks :
        for row in self.tasks_table:
            task = Task(
                priority=row["priority"],
                name=row["name"],
                deps=[],
                time=row["time"],
                expDate=row["expDate"]
            )

            task_objects[row["name"]] = task
            self.queue.add(task)

        # now for merging the dependences :
        for row in self.tasks_table:
            current_task = task_objects[row["name"]]
            for dep_name in row["deps_list"]:
                if dep_name in task_objects:
                    current_task.deps.append(
                        task_objects[dep_name].taskID
                    )

        # calculations before runnig the program :
        self.queue.deps_score()
        self.queue.priority_boost()
        # running the simulator :
        self.results = self.queue.execution_order()
        return self.results

    def sort_done_tasks(self,tasks):
        """
        Sorts the tasks based on start time to show execution order
        """
        start_times = tasks['start_time']
        if start_times is None:
            return 1, float('inf'), tasks['id']
        else:
            return 0, start_times, tasks['id']

    def get_info_of_tasks(self):
        """
        Gets information about the tasks
        """
        if self.queue is None:
            return []
        info = []
        for task in self.queue.tasks.values():
            info.append({
                "id": task.taskID, "name": task.name,
                "priority": task.priority, "deps": [dep_id for dep_id in task.deps],
                "time": task.time, "expDate": task.expDate,
                "status": task.Mode, "start_time": task.start_time,
                "end_time": task.end_time
            })
        # sort the tasks based on start time to show the execution order
        done = []
        failed = []
        for temp in info:
            if temp['start_time'] is not None:
                done.append(temp)
            else:
                failed.append(temp)

        done.sort(key = self.sort_done_tasks)
        info[:] = done + failed
        return info

    def show_history(self, task_name):
        """
        Return the history of a task
        """
        if self.queue is None:
            return None
        for task in self.queue.tasks.values():
            if task.name == task_name:
                return task.history
        return None

    def find_task_by_name(self, name):
        """
        Finds a task object by its name value
        """
        for task in self.queue.tasks.values():
            if task.name == name:
                return task
        return None

    def total_time(self):
        """
        Returns the total execution time
        """
        if self.results:
            return self.results[2]
        return None

    def reset(self):
        """
        resets the queue and the results
        """
        self.queue = None
        self.results = None


# ------------------------------------------------------------------------
# GUI front code

import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QFileDialog,
    QDialog, QFormLayout, QLineEdit, QSpinBox, QDoubleSpinBox,
    QDialogButtonBox, QMessageBox, QSplitter, QLabel, QPlainTextEdit, QHeaderView,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush


class AddTask(QDialog):
    """
    an instance of a task in the gui
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Task")
        layout = QFormLayout(self)

        self.name = QLineEdit()
        self.prio = QSpinBox()
        self.prio.setRange(1, 99)
        self.deps = QLineEdit()
        self.deps.setPlaceholderText("separate with comma")
        self.time = QDoubleSpinBox()
        self.time.setRange(1, 9999)
        self.exp = QDoubleSpinBox()
        self.exp.setRange(-1, 9999)
        self.exp.setValue(-1)
        self.exp.setSpecialValueText("None")

        layout.addRow("Name:", self.name)
        layout.addRow("Priority:", self.prio)
        layout.addRow("Dependencies:", self.deps)
        layout.addRow("Execution time:", self.time)
        layout.addRow("Deadline:", self.exp)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self):
        """
        Gets the data of a task
        """
        deps_text = self.deps.text().strip()
        deps_list = [d.strip() for d in deps_text.split(",") if d.strip()] if deps_text else []
        return {
            "name": self.name.text().strip(),
            "priority": self.prio.value(),
            "deps_list": deps_list,
            "time": self.time.value(),
            "expDate": self.exp.value()
        }

# main gui class and configuration
class GUI(QMainWindow):
    STATUS_COLORS = {
        "COMPLETE": QColor(144, 238, 144),
        "FAILED": QColor(255, 99, 71),
        "BLOCKED": QColor(255, 165, 0),
        "EXECUTING": QColor(255, 255, 102),
        "READY": QColor(173, 216, 230),
        "WAITING": QColor(200, 200, 200),
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Task Scheduler Simulator")
        self.setFixedSize(1200, 650)
        self.backend = TaskGui()
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        #main table
        self.table = QTableWidget()
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Name", "Priority", "Dependencies", "Time", "Deadline",
             "Status", "Start", "End"]
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.table.cellDoubleClicked.connect(self.display_history)
        splitter.addWidget(self.table)

        # layout of history
        history_widget = QWidget()
        history_layout = QVBoxLayout(history_widget)
        history_layout.setContentsMargins(5, 5, 5, 5)

        self.history_label = QLabel("Task History")
        self.history_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.history_text = QPlainTextEdit()
        self.history_text.setReadOnly(True)
        self.history_text.setPlaceholderText("Double click a task to see its history")

        history_layout.addWidget(self.history_label)
        history_layout.addWidget(self.history_text)
        splitter.addWidget(history_widget)

        # vertical splitters
        splitter.setStretchFactor(0, 8)
        splitter.setStretchFactor(1, 2)

        #bottom buttons
        btn_layout = QHBoxLayout()
        self.load_btn = QPushButton("Load Excel")
        self.add_btn = QPushButton("Add Task")
        self.run_btn = QPushButton("Run Simulation")
        self.reset_btn = QPushButton("Reset")
        self.load_btn.clicked.connect(self.load_excel)
        self.add_btn.clicked.connect(self.add_task)
        self.run_btn.clicked.connect(self.run_simulation)
        self.reset_btn.clicked.connect(self.reset_all)
        btn_layout.addWidget(self.load_btn)
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.run_btn)
        btn_layout.addWidget(self.reset_btn)

        #add it all up
        main_layout.addWidget(splitter, 1)
        main_layout.addLayout(btn_layout)

        self.statusBar().showMessage("Ready")

    def refresh(self):
        """
        updates the contents of the table
        """
        self.table.setRowCount(0)
        tasks_info = self.backend.get_info_of_tasks()
        if not tasks_info:
            definitions = self.backend.tasks_table
            for i, d in enumerate(definitions):
                self.table.insertRow(i)
                self.table.setItem(i, 1, QTableWidgetItem(d["name"]))
                self.table.setItem(i, 2, QTableWidgetItem(str(d["priority"])))
                self.table.setItem(i, 3, QTableWidgetItem(", ".join(d["deps_list"])))
                self.table.setItem(i, 4, QTableWidgetItem(str(d["time"])))
                deadline_str = str(d["expDate"]) if d["expDate"] != -1 else "None"
                self.table.setItem(i, 5, QTableWidgetItem(deadline_str))
                self.table.setItem(i, 6, QTableWidgetItem("WAITING"))
                for col in [0, 7, 8]:
                    self.table.setItem(i, col, QTableWidgetItem(""))
            return

        self.table.setRowCount(len(tasks_info))
        for i, t in enumerate(tasks_info):
            self.table.setItem(i, 0, QTableWidgetItem(str(t["id"])))
            self.table.setItem(i, 1, QTableWidgetItem(t["name"]))
            self.table.setItem(i, 2, QTableWidgetItem(str(t["priority"])))
            dep_names = []
            if self.backend.queue:
                for did in t["deps"]:
                    dep_task = self.backend.queue.tasks.get(did)
                    dep_names.append(dep_task.name if dep_task else str(did))
            else:
                dep_names = [str(d) for d in t["deps"]]
            self.table.setItem(i, 3, QTableWidgetItem(", ".join(dep_names)))
            self.table.setItem(i, 4, QTableWidgetItem(str(t["time"])))
            deadline_str = str(t["expDate"]) if t["expDate"] != -1 else "None"
            self.table.setItem(i, 5, QTableWidgetItem(deadline_str))
            status_item = QTableWidgetItem(t["status"])
            color = self.STATUS_COLORS.get(t["status"], QColor("white"))
            status_item.setBackground(QBrush(color))
            self.table.setItem(i, 6, status_item)
            start = str(t["start_time"]) if t["start_time"] is not None else ""
            end = str(t["end_time"]) if t["end_time"] is not None else ""
            self.table.setItem(i, 7, QTableWidgetItem(start))
            self.table.setItem(i, 8, QTableWidgetItem(end))

    def display_history(self, row, col):
        """
        displays the history of the chosen task
        """
        name_item = self.table.item(row, 1)
        if not name_item:
            return
        name = name_item.text()
        history = self.backend.show_history(name)
        if history is None:
            self.history_text.setPlainText("No history available run the simulation first.")
            return
        lines = [f"History of: {name}"]
        for event in history:
            lines.append(f"Time: {event['time']} | Event: {event['event']}")
        self.history_text.setPlainText("\n".join(lines))


    def load_excel(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open Excel File", "", "Excel Files (*.xlsx *.xls)"
        )
        if filepath:
            try:
                self.backend.load_from_excel(filepath)
                self.backend.reset()
                self.refresh()
                self.history_text.clear()
                self.statusBar().showMessage(f"Loaded {len(self.backend.tasks_table)} tasks from {filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open Excel file:\n{str(e)}")

    def add_task(self):
        """
        add an instance of a task to the table
        """
        dialog = AddTask(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if not data["name"]:
                QMessageBox.warning(self, "Warning", "Task name cannot be empty")
                return
            self.backend.add_task(**data)
            self.backend.reset()
            self.refresh()
            self.history_text.clear()
            self.statusBar().showMessage("Task added. Press 'Run Simulation' to execute.")

    def run_simulation(self):
        """
        runs the simulation of the task execution
        """
        if not self.backend.tasks_table:
            QMessageBox.information(self, "Info", "No tasks to simulate.")
            return
        try:
            self.backend.run_simulation()
            self.refresh()
            total = self.backend.total_time()
            self.statusBar().showMessage(f"Simulation complete. Total time: {total}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Simulation failed:\n{str(e)}")

    def reset_all(self):
        self.backend.reset()
        self.refresh()
        self.history_text.clear()
        self.history_text.setPlaceholderText("Double click a task to see its history")
        self.statusBar().showMessage("Reset")

if __name__ == "__main__":
    app = QApplication(sys.argv)

#dark mode colors
    app.setStyle("Fusion")
    dark_palette = app.palette()
    dark_palette.setColor(dark_palette.ColorRole.Window, QColor(53, 53, 53))
    dark_palette.setColor(dark_palette.ColorRole.WindowText, Qt.GlobalColor.white)
    dark_palette.setColor(dark_palette.ColorRole.Base, QColor(25, 25, 25))
    dark_palette.setColor(dark_palette.ColorRole.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(dark_palette.ColorRole.ToolTipBase, Qt.GlobalColor.black)
    dark_palette.setColor(dark_palette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    dark_palette.setColor(dark_palette.ColorRole.Text, Qt.GlobalColor.white)
    dark_palette.setColor(dark_palette.ColorRole.Button, QColor(53, 53, 53))
    dark_palette.setColor(dark_palette.ColorRole.ButtonText, Qt.GlobalColor.white)
    dark_palette.setColor(dark_palette.ColorRole.BrightText, Qt.GlobalColor.red)
    dark_palette.setColor(dark_palette.ColorRole.Link, QColor(42, 130, 218))
    dark_palette.setColor(dark_palette.ColorRole.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(dark_palette.ColorRole.HighlightedText, Qt.GlobalColor.black)
    app.setPalette(dark_palette)
    #additional QCC for theme
    app.setStyleSheet("""
        QTableWidget { gridline-color: #555; }
        QHeaderView::section {
            background-color: #2b2b2b;
            color: white;
            padding: 4px;
            border: 1px solid #555;
        }
        QPlainTextEdit {
            background-color: #1e1e1e;
            color: #ddd;
        }
        QLabel {
            color: white;
        }
        QPushButton {
            background-color: #3c3c3c;
            color: white;
            border: 1px solid #555;
            padding: 5px;
        }
        QPushButton:hover {
            background-color: #505050;
        }
        QPushButton:pressed {
            background-color: #2a2a2a;
        }
    """)

    window = GUI()
    window.show()
    sys.exit(app.exec())