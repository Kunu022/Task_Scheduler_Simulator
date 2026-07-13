
"""
Task Scheduler Simulator.

The task_scheduler module provides classes and functions for
creating tasks, managing dependencies, simulating execution,
and analyzing scheduling behavior.

Tasks can be loaded from an Excel file and executed according
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

#================
# Task queue
#================
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

    def find_all_dependents(self, taskID, visited=None):
        """
        Return all tasks that directly or indirectly depend
        on the specified task.
        """
        if visited is None:
            visited = set()
        if taskID in visited:
            return visited
        visited.add(taskID)

        for temp in self.tasks.values():
            if taskID in temp.deps:
                self.find_all_dependents(temp.taskID, visited)
        return visited

    def fail_failed_tasks(self, taskID, current_time):
        """
        Mark a task as failed and block all dependent tasks.
        """
        proxy_fail = self.find_all_dependents(taskID)

        blocked = []
        for effected in proxy_fail:
            task = self.tasks.get(effected)
            if task and task.Mode not in [TaskMode.BLOCKED, TaskMode.FAILED]:
                if effected == taskID:
                    task.Mode = TaskMode.FAILED          # fixed: was task.mode
                    task.add_history(TaskMode.FAILED, current_time)  # removed raw append
                else:
                    task.Mode = TaskMode.BLOCKED         # fixed: was task.mode
                    task.add_history(TaskMode.BLOCKED, current_time) # removed raw append
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
        for tid,task in self.tasks.items():
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

            # Double-check deadline right before execution
            if task.expDate_miss(current_time):
                cascade = self.fail_failed_tasks(task.taskID, current_time)
                aborted.extend(cascade)
                continue

            # Execute the task
            task.Mode = TaskMode.EXECUTING
            task.add_history(TaskMode.EXECUTING, current_time)   # removed raw append
            task.start_time = current_time
            current_time += task.time
            task.end_time = current_time
            task.Mode = TaskMode.COMPLETE
            task.add_history(TaskMode.COMPLETE, current_time)    # removed raw append
            order.append(task.taskID)

            # Check deadlines after time passes
            self.check_expDates(current_time)

            # Update dependents
            for dep_tid in dependents[task.taskID]:
                # Skip blocked/failed dependents
                if self.tasks[dep_tid].Mode in [TaskMode.BLOCKED, TaskMode.FAILED]:
                    continue

                in_degree[dep_tid] -= 1
                if in_degree[dep_tid] == 0:
                    t = self.tasks[dep_tid]

                    # Check if this newly-ready task will miss its deadline
                    if t.expDate_miss(current_time):            # fixed: was will_miss_deadline
                        cascade = self.fail_failed_tasks(t.taskID, current_time)
                        aborted.extend(cascade)
                    else:
                        t.Mode = TaskMode.READY
                        t.add_history(TaskMode.READY, current_time)  # added missing history
                        heapq.heappush(ready, (t.effective_priority(), -t.depsScore,
                                               next(self.counter), t))

        # Report results
        print(f"\nExecution Results")
        print(f"Completed: {len(order)} tasks")
        print(f"Failed/Blocked: {len(aborted)} tasks")

        if aborted:
            print("\nFailed tasks:")
            for tid in aborted:
                task = self.tasks[tid]
                print(f"  {task.name} (ID {tid})")

        return order, aborted, current_time


    def show_history(self, taskID):
        """
        Display the history of a task.
        """
        task = self.tasks.get(taskID)
        if task is None:
            print("Task not found.")
            return

        print("\n------------------------")
        print("History of:", task.name)
        print("------------------------")
        for event in task.history:
            print("Time:", event["time"], "| Event:", event["event"])


#========================
# Simulation interface
#Class for presentation of data to the gui
#========================
class TaskGui:
    
    def __init__(self):
        self.tasks_table = []   # list of dicts: {priority, name, deps_list, time, expDate}
        self.queue = None     # the TaskQueue used in the last run
        self.results = None   # (order, aborted, total_time) from last run

    
    # Read tasks from Excel file.
    def load_from_excel(self, filepath):
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

    # Create tasks and resolve dependencies.
    def add_task(self, priority, name, deps_list, time, expDate):
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

        # this is for making the tasks :
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

    def get_info_of_tasks(self):
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
        return info

    def show_history(self, task_name):
        if self.queue is None:
            return None
        for task in self.queue.tasks.values():
            if task.name == task_name:
                return task.history
        return None

    def find_task_by_name(self, name):
        for task in self.queue.tasks.values():
            if task.name == name:
                return task
        return None

    def total_time(self):
        if self.results:
            return self.results[2]
        return None

    def reset(self):
        self.queue = None
        self.results = None

# For testing
gui = TaskGui()

gui.load_from_excel("tasks.xlsx")

print(gui.tasks_table)
print(len(gui.tasks_table))

order, aborted, total_time = gui.run_simulation()


