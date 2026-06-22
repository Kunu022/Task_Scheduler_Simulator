import heapq
from itertools import count

ID_COUNTER = count()
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

    # finding the correct priority for a task
    def effective_priority(self):
        if self.tempPriority > 0:
            return min(self.priority, self.tempPriority)
        return self.priority

class TaskQueue:
    def __init__(self):
        self.tasks = {}
        self.find = {}
        self.counter = count()
        self.heap = []



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



    def execution_order(self):
        in_degree = {tid: len(task.deps) for tid, task in self.tasks.items()}
        dependents = {tid: [] for tid in self.tasks}
        for tid, task in self.tasks.items():
            for dep_id in task.deps:
                if dep_id in dependents:
                    dependents[dep_id].append(tid)

        ready = []
        for tid, task in self.tasks.items():
            if in_degree[tid] == 0:
                eff = task.effective_priority()
                heapq.heappush(ready, (eff, -task.depsScore, next(self.counter), task))

        order = []
        while ready:
            _, _, _, task = heapq.heappop(ready)
            order.append(task.taskID)
            for dep_tid in dependents[task.taskID]:
                in_degree[dep_tid] -= 1
                if in_degree[dep_tid] == 0:
                    t = self.tasks[dep_tid]
                    heapq.heappush(ready, (t.effective_priority(), -t.depsScore, next(self.counter), t))

        if len(order) != len(self.tasks):
            raise ValueError("Loop detected")

        return order




q = TaskQueue()
a = Task(1, "A", [1])
b = Task(5, "B", [])
c = Task(3, "C", [b.taskID])
for t in [a, b, c]:
    q.add(t)

q.deps_score()
q.priority_boost()
print("Execution order:", [q.tasks[tid].name for tid in q.execution_order()])