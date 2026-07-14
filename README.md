# Task Scheduler Simulator

A task scheduling simulator implemented in Python.

This project simulates the execution of tasks based on priorities,
dependencies, and deadlines. Tasks are loaded dynamically from an
Excel file and executed using a priority queue.

---

## Features :

- Task scheduling using a priority queue
- Dependency management between tasks
- Deadline and expiration date checking
- Priority boosting mechanism
- Failure propagation
- Task history tracking
- Excel-based task input
- Simulation of task execution

---

## Project Structure

```text
Task_Scheduler_Simulator/

├── Main.py
├── tasks.xlsx
├── README.md
└── ...
```

---

## Input Format

Tasks are loaded from an Excel file.

Example:

| priority | name         | deps_list      | time | expDate |
|----------|--------------|---------------|------|----------|
| 1        | UrgentReport |               | 5    | 3        |
| 3        | BackupDB     | UrgentReport  | 2    | -1       |
| 2        | CleanLogs    |               | 1    | -1       |
| 3        | SendEmail    | BackupDB      | 1    | -1       |

---

## Task States

A task can be in one of the following states:

- WAITING
- READY
- EXECUTING
- COMPLETE
- FAILED
- BLOCKED
- DELETED

---

## How to Run

Install the required package:

```bash
pip install pandas openpyxl
```

Run the simulator:

```bash
python Main.py
```

---

## Example Output

```text
Execution Results

Completed: 1 tasks
Failed/Blocked: 3 tasks

Failed tasks:

UrgentReport
BackupDB
SendEmail
```

---

## Future Improvements

- Timeline visualization
- Export simulation results
- Log file generation

---

## Authors :
├──  Fardin Aghaei
├──  Soheil Pirani
└──  Sheyda Ghavamifard

$ Thank you for your interest in this project !
