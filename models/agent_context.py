class PlanContext:
    def __init__(self, planId: str, planName: str, deliverableName: str):
        self.planId = planId
        self.planName = planName
        self.deliverableName = deliverableName
        
class AgentContext:
    def __init__(self, planContext: PlanContext, taskId: str, taskName: str, taskType: str):
        self.planContext = planContext
        self.taskId = taskId
        self.taskName = taskName
        self.taskType = taskType