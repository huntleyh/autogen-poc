from typing import Dict, Optional, Union
import regex
import json

from autogen.agentchat.assistant_agent import ConversableAgent
from autogen.agentchat.contrib.capabilities.agent_capability import AgentCapability
from autogen import Agent
from termcolor import colored
from string import digits

from models.agent_context import AgentContext, PlanContext
from models.agent_memory import Event, Memory
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Type, TypeVar, Union
import json
from models.agent_tasks import Tasks

class StateAwareNonLlm(AgentCapability):
    """
    state_aware capability uses a vector database to give an agent the ability to remember user teachings,
    where the user is any caller (human or not) sending messages to the teachable agent.
    state_aware capability is designed to be composable with other agent capabilities.
    To make any conversable agent teachable, instantiate both the agent and the state_aware capability class,
    then pass the agent to state_aware capability.add_to_agent(agent).
    Note that teachable agents in a group chat must be given unique path_to_db_dir values.

    When adding state_aware capability to an agent, the following are modified:
    - The agent's system message is appended with a note about the agent's new ability.
    - A hook is added to the agent's `process_last_received_message` hookable method,
    and the hook potentially modifies the last of the received messages to include earlier teachings related to the message.
    Added teachings do not propagate into the stored message history.
    If new user teachings are detected, they are added to new memos in the vector database.
    """
    
    MESSAGE_TYPE = "MESSAGE"
    EXCEPTION_TYPE = "EXCEPTION"
    AGENT_ROLE = "Agent"

    def __init__(
        self,
        context: AgentContext,
        verbosity: Optional[int] = 0,
        recall_threshold: Optional[float] = 1.5,
        max_num_retrievals: Optional[int] = 10,
        llm_config: Optional[Union[Dict, bool]] = None,
        is_group_manager: Optional[bool] = False
    ):
        """
        Args:
            verbosity (Optional, int): # 0 (default) for basic info, 1 to add memory operations, 2 for analyzer messages, 3 for memo lists.
            reset_db (Optional, bool): True to clear the DB before starting. Default False.
            path_to_db_dir (Optional, str): path to the directory where this particular agent's DB is stored. Default "./tmp/state_aware_agent_db"
            recall_threshold (Optional, float): The maximum distance for retrieved memos, where 0.0 is exact match. Default 1.5. Larger values allow more (but less relevant) memos to be recalled.
            max_num_retrievals (Optional, int): The maximum number of memos to retrieve from the DB. Default 10.
            llm_config (dict or False): llm inference configuration passed to TextAnalyzerAgent.
                If None, TextAnalyzerAgent uses llm_config from the teachable agent.
        """
        self.verbosity = verbosity
        self.recall_threshold = recall_threshold
        self.max_num_retrievals = max_num_retrievals
        self.llm_config = llm_config
        self.message_count = 0

        self.analyzer = None
        self.state_aware_agent = None
        self.memory = Memory(context.planContext.planId, context.taskName, context.taskId)
        self.tasks = Tasks(context.planContext.planId, context.taskName, context.taskId)

        self.agent_context = context
        self.is_group_manager = is_group_manager
        self.is_recollecting = False

    def retrieve_steps(self, text: Union[Dict, str])->str:
        """Tries to retrieve the steps needed to complete a task."""

        if self.state_aware_agent.name == "Assistant":
            return """
                1. Generate a random dollar amount in USD
                2. Calculate how much this is in EUR
                3. Determine how much this would have equated to 100 years ago
                """
        elif self.state_aware_agent.name == "Executor":
            return """
                1. You are responsible of executing custom functions, you don't write your code
                """
        elif self.state_aware_agent.name == "Admin":
            return """
                1. Perform the currency conversion.
                """

    def add_to_agent(self, agent: ConversableAgent):
        """Adds state_aware capability to the given agent."""
        self.state_aware_agent = agent

        # Save this task to the db if it doesn't already exist
        if (not self.tasks.task_exists(self.tasks.taskId, agent.name, agent.description)):
            self.tasks.add_task(self.tasks.taskId, agent.name, agent.description)

        # Enable resuming by recollecting what we've done so far BEFORE registering hooks
        #self.recollect()
        
        # Register hooks for processing the last message and one for before the message is sent in order to
        # determine if the task was completed.
        # For each incoming message we handle it accordingly
        agent.register_hook(hookable_method="process_last_received_message", hook=self.process_last_received_message)
        # For each outgoing message we store it in memory
        agent.register_hook(hookable_method="process_message_before_send", hook=self.process_message_before_send)
        

    def recollect(self)->List:
        """
        Hydrates the agent with the necessary information to recollect previous runs.
        """
        
        messages: List = []
        
        try:
            self.is_recollecting = True
        
            events = self.memory.retrieve_memory(lookback=50)
            
            if len(events) > 0:
                for event in events:
                    if event.message_type == self.MESSAGE_TYPE:
                        self.message_count += 1
                        messages.append({"content": event.message, "role": event.role, "name": self.state_aware_agent.name})
                        
            if self.is_group_manager == False:
                tasks = self.tasks.retrieve_tasks()

                for task in tasks:
                    self.state_aware_agent.send({"content": task.task + ': ' + task.status, "role": 'assistant'}, self.state_aware_agent, request_reply=False, silent=True)
                    
        except Exception as e:
            print(f"Error: {e}")
            
        self.is_recollecting = False
        
        return messages
        
    def process_last_received_message(self, text: Union[Dict, str]):
        """
        If this is the first message recieved then get the list of steps needed to complete the task and appends it with instructions
        so we can keep track of completed items.
        """
        
        if self.is_recollecting:
            return text
        
        response_format = """
        At the end of your response, use a single = as a delimeter followed by a JSON string of step or steps you performed as well as a status for each step. 
        The format should be a single line with a JSON formatted string in the format: {"Steps": [{ "STEP": "your first task here", "STATUS": "status of the step", "DETAIL": "additional detail" }, { "STEP": "your second task here", "STATUS": "status of the step", "DETAIL": "additional detail" }]}
        Valid statuses are: DONE, IN_PROGRESS, BLOCKED, TODO. Do not use any other status outside of these three.
        The "Detail" property MUST ALWAYS BE PRESENT and will include any additional detail such as error messages or asking for additional information or documents needed to complete the step.
        Do not include additional detail at the end of your response. 
        """
        
        response_instructions =  f"""{response_format}   
        Check to make sure you have not already completed this step! If you need additional detail or feedback ASK the {self.agent_context.parent_agent_name} for it. Do not assume the {self.agent_context.parent_agent_name} knows what you need.  
        """

        if self.message_count == 0 and self.is_group_manager == False:
            # hardcoded for now; will update json to showcase if needed, but this will ideally come from a
            # data store that contains all agents and their tasks
            required_steps = self.retrieve_steps(text)
            pattern = r'\d+\.\s+(.*)'  # Matches the number followed by a dot and space, then captures the text
            steps = regex.findall(pattern, required_steps)

            for step in steps:
                # Save this task to the db if it doesn't already exist
                if not self.tasks.task_exists(self.tasks.taskId, self.state_aware_agent.name + "-subtask", step):
                    self.tasks.add_task(self.tasks.taskId, self.state_aware_agent.name + "-subtask", step)

            text = f"""
            This is your task: 
            
            {text}
            
            -----
            To complete this task, follow ALL these steps for the ENTIRE conversation and DO NOT repeat any step that has already been completed:
            {required_steps}
            
            ----
            {response_instructions}
            """
            
        if self.verbosity >= 1:
            print(colored(f"\nUsing text:\n\n{text}", "light_yellow"))
        
        self.message_count = self.message_count + 1        
        
        message = ConversableAgent._message_to_dict(text)
        
        self.memory.save_to_memory(
            event = Event(message_type=self.MESSAGE_TYPE, message=message.get("content"), role=self.__get_role__(message))
        )
        
        return text    
    
    def isValidJson(self, json_str: str)->bool:
        try:
            json.loads(json_str)
        except ValueError as e:
            return False
        return True
    
    def process_message_before_send(self, message: Union[Dict, str], sender: Agent, recipient: Agent, silent: bool):
        """
        Appends any relevant memos to the message text, and stores any apparent teachings in new memos.
        Uses TextAnalyzerAgent to make decisions about memo storage and retrieval.
        """
        
        if self.is_recollecting or silent == True:
            return message
        
        message = ConversableAgent._message_to_dict(message)
        # If the agent is conversing, update the state to in progress. If the message the agent is about to send
        # contains the Done message, update the db to indicate the task is done
        # extract the json from the message and use that to update the tasks
        message_parts = message.get('content').split("=")
        response_json = {}
        
        if(len(message_parts) > 1) and self.isValidJson(message_parts[1]):
            json_str = message_parts[1]
            response_json = json.loads(json_str)
            
        elif len(message_parts) > 0 and self.isValidJson(message_parts[0]):
            json_str = message_parts[0]
            response_json = json.loads(json_str)

        if isinstance(response_json, str) and response_json.__len__() > 0:
            if self.is_group_manager == False:
                for step in response_json['Steps']:
                    # strip the number out of the step (i.e., it may come in as '3. Get how many months are profitable')
                    strStep = (str)(step["STEP"])
                    strStep = strStep[strStep.find('.') + 1:]
                    self.tasks.update_task(self.state_aware_agent.name + "-subtask", strStep.strip(), step["DETAIL"], step["STATUS"], message.get("content"))

        self.memory.save_to_memory(
        event = Event(message_type=self.MESSAGE_TYPE, message=message.get("content"), role=self.__get_role__(message))
        )
        
        return message
    
    def __get_role__(self, message: Dict)->str:
        """
        Returns the role of the message sender.
        """
        if message.get("role") is not None:
            return message.get("role")
        
        return "assistant"
