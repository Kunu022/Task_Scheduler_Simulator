import heapq
from itertools import count

ID_COUNTER = count()
#different states a task can be in
class TaskMode:
    DELETED = "DELETED"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    EXECUTING = "EXECUTING"
    WAITING = "WAITING"
    READY = "READY"
class Task:
    def __init__(self, priority, name ,deps, time = 0, expDate = -1 ):

        self.taskID = next(ID_COUNTER)
        self.priority = priority
        self.name = name
        self.deps = deps
        self.time = time
        self.expDate = expDate
        self.depsScore = 0
        self.tempPriority = 0
        self.Mode = TaskMode.WAITING

    # finding the correct priority for a task
    def effective_priority(self):
        if self.tempPriority > 0:
            return min(self.priority, self.tempPriority)
        return self.priority

    #checks if the task will miss its expiration date even if it is executed right now
    def expDate_miss(self,current_time):
        if self.expDate < 0 :
            return False
        if current_time + self.time > self.expDate:
            return True

class TaskQueue:
    def __init__(self):
        self.tasks = {}
        self.find = {}
        self.counter = count()
        self.heap = []
        self.failed = []

    #find all the tasks that depend on a task
    def find_all_dependents(self, taskID, visited = None):
        if visited is None:
            visited = set()
        if taskID in visited:
            return visited
        visited.add(taskID)

        for temp in self.tasks.values():
            if taskID in temp.deps:
                self.find_all_dependents(temp.taskID, visited)

        return visited
    #will fail any task that failed along with the tasks that depend on it
    def fail_failed_tasks(self, taskID, current_time):
        proxy_fail = self.find_all_dependents(taskID)

        blocked = []
        for effected in proxy_fail:
            task = self.tasks.get(effected)
            if task and task.Mode not in [TaskMode.BLOCKED, TaskMode.FAILED]:
                if effected == taskID:
                    task.mode = TaskMode.FAILED
                else:
                    task.mode = TaskMode.BLOCKED
                blocked.append(effected)

                if effected in self.find:
                    temp = self.find.pop(effected)
                    temp[-1] = "DELETED"

        self.failed.append(blocked)
        return blocked
    #checks all the tasks in the queue and the one running to see if they will miss their deadline or not
    def check_expDates(self, current_time):
        failed = []
        for task in self.tasks.values():
            if task.Mode in [TaskMode.WAITING, TaskMode.EXECUTING]:
                if task.expDate_miss(current_time):
                    blocked = self.fail_failed_tasks(task.taskID,current_time)
                    failed.append(blocked)

        return failed

    # add a task to the queue
    def add(self, task):
        self.tasks[task.taskID] = task
        #making it a list to be able to change it later for deletion
        entry = [task.effective_priority(), task.depsScore, next(self.counter), task.taskID, task]
        self.find[task.taskID] = entry
        heapq.heappush(self.heap, entry)

    # update task info by marking the old task as "Deleted" and
    # putting a new ones in the heap with the updated values
    def update_task(self, taskID, priorityNew = None, depsScoreNew = None):
        if taskID not in self.tasks:
            return

        task = self.tasks[taskID]
        old = self.find.pop(taskID,None)
        if old:
            old[-1] = "Deleted"

        priority = priorityNew if priorityNew is not None else task.effective_priority()
        deps = depsScoreNew if depsScoreNew is not None else task.depsScore

        tempTask = [priority, deps, next(self.counter), taskID, task]
        self.find[taskID] = tempTask
        heapq.heappush(self.heap, tempTask)

    # remove a task from the queue
    def remove(self, taskID):
        while self.heap:
            poppedTask = heapq.heappop(self.heap)
            if poppedTask[-1] != "Deleted":
                task = poppedTask[-1]
                del self.find[taskID]
                return task

    def deps_score(self):
        for task in self.tasks.values():
            task.depsScore = 0
        for task in self.tasks.values():
            for d in task.deps:
                if d in self.tasks:
                    self.tasks[d].depsScore += 1

        for taskID in list(self.find.keys()):
            self.update_task(taskID, depsScoreNew = self.tasks[taskID].depsScore)


    """ The Functions Below are AI for now Because They Will Change Later """
    def priority_boost(self):
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
            self.update_task(taskID, priorityNew = self.tasks[taskID].effective_priority())

    def execution_order(self, start_time=0):
        current_time = start_time
        in_degree = {tid: len(task.deps) for tid, task in self.tasks.items()}
        dependents = {tid: [] for tid in self.tasks}

        for tid, task in self.tasks.items():
            for dep_id in task.deps:
                if dep_id in dependents:
                    dependents[dep_id].append(tid)

        # Check initial deadlines before starting
        self.check_expDates(current_time)

        ready = []
        for tid, task in self.tasks.items():
            if in_degree[tid] == 0 and task.Mode == TaskMode.WAITING:
                task.Mode = TaskMode.READY
                heapq.heappush(ready, (task.effective_priority(), -task.depsScore,
                                       next(self.counter), task))

        order = []
        aborted = []

        while ready:
            _, _, _, task = heapq.heappop(ready)

            # Double-check deadline right before execution
            if task.expDate_miss(current_time):
                cascade = self.fail_failed_tasks(
                    task.taskID,current_time)
                aborted.extend(cascade)
                continue

            # Execute the task
            task.state = TaskMode.EXECUTING
            task.start_time = current_time
            current_time += task.time
            task.end_time = current_time
            task.state = TaskMode.COMPLETE
            order.append(task.taskID)

            # Check deadlines after time passes
            self.check_expDates(current_time)

            # Update dependents
            for dep_tid in dependents[task.taskID]:
                # Skip blocked/failed dependents
                if self.tasks[dep_tid].state in [TaskMode.BLOCKED, TaskMode.FAILED]:
                    continue

                in_degree[dep_tid] -= 1
                if in_degree[dep_tid] == 0:
                    t = self.tasks[dep_tid]

                    # Check if this newly-ready task will miss its deadline
                    if t.will_miss_deadline(current_time):
                        cascade = self.fail_failed_tasks(
                            t.taskID,current_time)
                        aborted.extend(cascade)
                    else:
                        t.state = TaskMode.READY
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



q = TaskQueue()

# Task with tight deadline that can't be met
a = Task(1, "UrgentReport", [], time=5, expDate=3)  # Needs 5 time units, due in 3
b = Task(3, "BackupDB", [a.taskID], time=2)  # Depends on the failed task
c = Task(2, "CleanLogs", [], time=1)  # Independent, will run fine
d = Task(3, "SendEmail", [b.taskID], time=1)  # Depends on failed chain

for t in [a, b, c, d]:
    q.add(t)

q.deps_score()
q.priority_boost()

order, aborted, total_time = q.execution_order()

print(f"\nCompleted: {[q.tasks[tid].name for tid in order]}")
print(f"Aborted: {[q.tasks[tid].name for tid in aborted]}")
print(f"Total time: {total_time}")