from collections import defaultdict
import os
import pickle
from typing import Dict, Optional, Union
import chromadb
from chromadb.config import Settings
# from database import Tasks
import regex
import json

from autogen.agentchat.assistant_agent import ConversableAgent
from autogen.agentchat.contrib.capabilities.agent_capability import AgentCapability
from autogen.agentchat.contrib.text_analyzer_agent import TextAnalyzerAgent
from autogen import Agent
from termcolor import colored

from models.agent_context import AgentContext, PlanContext
from models.agent_memory import Event, Memory
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Type, TypeVar, Union
import json

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
        #reset_db: Optional[bool] = False,
        #path_to_db_dir: Optional[str] = "./tmp/state_aware_agent_db",
        recall_threshold: Optional[float] = 1.5,
        max_num_retrievals: Optional[int] = 10,
        llm_config: Optional[Union[Dict, bool]] = None
        # task_db = Tasks()
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
        #self.path_to_db_dir = path_to_db_dir
        self.recall_threshold = recall_threshold
        self.max_num_retrievals = max_num_retrievals
        self.llm_config = llm_config
        self.message_count = 0
        # self.task_db = task_db

        self.analyzer = None
        self.state_aware_agent = None
        self.memory = Memory(context.planContext.planId, context.taskName, context.taskId)
        self.agent_context = context
        # Print the list
        # task_db.print_tasks()

    def retrieve_steps(self, text: Union[Dict, str])->str:
        """Tries to retrieve the steps needed to complete a task."""
        
        return """
            1. Get name of company
            2. Get how long the company's been in business
            3. Get how many months are profitable
            """

    def add_to_agent(self, agent: ConversableAgent):
        """Adds state_aware capability to the given agent."""
        self.state_aware_agent = agent

        # # Save this task (the agents name is the task) to the db if it doesn't already exist
        # if (not self.task_db.task_exists(agent.name)):
        #     self.task_db.add_task(agent.name, agent.description)
        #task = self.memo_store.get_task_str(agent.name)
        #if task.rfind(f"{agent.name}") == -1:
        #    self.memo_store.save_task_to_db(f"{agent.name}: Not Done")

        # Enable resuming by recollecting what we've done so far BEFORE registering hooks
        self.recollect()
        
        # Register hooks for processing the last message and one for before the message is sent in order to
        # determine if the task was completed.
        # For each incoming message we handle it accordingly
        agent.register_hook(hookable_method="process_last_received_message", hook=self.process_last_received_message)
        # For each outgoing message we store it in memory
        agent.register_hook(hookable_method="process_message_before_send", hook=self.process_message_before_send)
        

        # TODO: Check if this task was already done. If so, tell the agent the work was already done (probably need
        # to also get the outcome - so might need to save that when the agent finishes the task so it can be passed
        # to the next agent)

        # Append extra info to the system message.
        # agent.update_system_message(
        #     # Instruct the agent to state explicitly that when this task is done, respond with "<task>: Done."
        #     # This may be something a user will need to supply though / check?
        #     agent.system_message + f"\nWhen you complete the ask, respond with: {agent.name}: Done"
        # )

    def recollect(self)->list[Dict]: #Dict[Agent, List[Dict]]:
        """
        Hydrates the agent with the necessary information to recollect previous runs.
        """
        events = self.memory.retrieve_memory(lookback=50)
        
        #messages = defaultdict(list)
        for event in events:
            if event.message_type == self.MESSAGE_TYPE:
                self.state_aware_agent.send({"content": event.message, "role": event.role}, self.state_aware_agent, silent=True)
                #messages[Agent].append({"content": event.message, "role": event.role})
        
        #return messages
        
    def process_last_received_message(self, text: Union[Dict, str]):
        """
        If this is the first message recieved then get the list of steps needed to complete the task and appends it with instructions
        so we can keep track of completed items.
        """
        
        response_format = """
        At the end of your response, use a single = as a delimeter followed by a JSON string of step or steps you performed as well as a status for each step. 
        The format should be a single line with a JSON formatted string in the format: {"Steps": [{ "STEP": "your first task here", "STATUS": "status of the step", "DETAIL": "additional detail" }, { "STEP": "your second task here", "STATUS": "status of the step", "DETAIL": "additional detail" }]}
        Valid statuses are: IN_PROGRESS, BLOCKED, TODO. Do not use any other status outside of these three.
        The "Detail" property will include any additional detail such as error messages or asking for additional information or documents needed to complete the step.
        Do not include additional detail at the end of your response. 
        """
        
        response_instructions =  f"""{response_format}   
        If you need additional detail or feedback ASK the {self.agent_context.parent_agent_name} for it. Do not assume the {self.agent_context.parent_agent_name} knows what you need.  
        """
        # response_instructions = """
        # At the end of your response ensure to include the exact verbiage of the step or steps you performed as well as a status for that step. 
        # The format should be two lines with the first line being: "STEP: {your task here}"
        # and the second line: "STATUS: {status of the step}"
        # Valid statuses are: IN_PROGRESS, BLOCKED, TODO.
        # Do not include additional detail at the end of your response.       
        # """
        if self.message_count == 0:
            # hardcoded for now; will update json to showcase if needed, but this will ideally come from a
            # data store that contains all agents and their tasks
            required_steps = self.retrieve_steps(text)
            pattern = r'\d+\.\s+(.*)'  # Matches the number followed by a dot and space, then captures the text
            steps = regex.findall(pattern, required_steps)

            for step in steps:
                continue #self.task_db.add_task(self.state_aware_agent.name + "-subtask", step)

            text = f"""
            This is your task: 
            
            {text}
            
            -----
            To complete this task, follow these steps and DO NOT repeat any step that has already been completed:
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
            
        for step in response_json['Steps']:
            continue
            # self.task_db.update_task(self.state_aware_agent.name + "-subtask", step["STEP"], step["DETAIL"], step["STATUS"])

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

class MemoStore:
    """
    Provides memory storage and retrieval for a teachable agent, using a vector database.
    Each DB entry (called a memo) is a pair of strings: an input text and an output text.
    The input text might be a question, or a task to perform.
    The output text might be an answer to the question, or advice on how to perform the task.
    Vector embeddings are currently supplied by Chroma's default Sentence Transformers.
    """

    def __init__(
        self,
        verbosity: Optional[int] = 0,
        reset: Optional[bool] = False,
        path_to_db_dir: Optional[str] = "./tmp/state_aware_agent_db",
    ):
        """
        Args:
            - verbosity (Optional, int): 1 to print memory operations, 0 to omit them. 3+ to print memo lists.
            - reset (Optional, bool): True to clear the DB before starting. Default False.
            - path_to_db_dir (Optional, str): path to the directory where the DB is stored.
        """
        self.verbosity = verbosity
        self.path_to_db_dir = path_to_db_dir

        # Load or create the vector DB on disk.
        settings = Settings(
            anonymized_telemetry=False, allow_reset=True, is_persistent=True, persist_directory=path_to_db_dir
        )
        self.db_client = chromadb.Client(settings)
        self.vec_db = self.db_client.create_collection("memos", get_or_create=True)  # The collection is the DB.

        # Load or create the associated memo dict on disk.
        self.path_to_dict = os.path.join(path_to_db_dir, "uid_text_dict.pkl")
        self.uid_text_dict = {}
        self.last_memo_id = 0
        if (not reset) and os.path.exists(self.path_to_dict):
            print(colored("\nLOADING MEMORY FROM DISK", "light_green"))
            print(colored("    Location = {}".format(self.path_to_dict), "light_green"))
            with open(self.path_to_dict, "rb") as f:
                self.uid_text_dict = pickle.load(f)
                self.last_memo_id = len(self.uid_text_dict)
                if self.verbosity >= 3:
                    self.list_memos()

        # Clear the DB if requested.
        if reset:
            self.reset_db()

    def list_memos(self):
        """Prints the contents of MemoStore."""
        print(colored("LIST OF TASKS", "light_green"))
        for uid, text in self.uid_text_dict.items():
            task, status = text
            print(
                colored(
                    "  ID: {}\n    TASK: {}\n    STATUS: {}".format(uid, task, status),
                    "light_green",
                )
            )

    def _save_memos(self):
        """Saves self.uid_text_dict to disk."""
        with open(self.path_to_dict, "wb") as file:
            pickle.dump(self.uid_text_dict, file)

    def reset_db(self):
        """Forces immediate deletion of the DB's contents, in memory and on disk."""
        print(colored("\nCLEARING MEMORY", "light_green"))
        self.db_client.delete_collection("tasks")
        self.vec_db = self.db_client.create_collection("tasks")
        self.uid_text_dict = {}
        self._save_memos()

    def save_task_to_db(self, task: str):
        print(self.vec_db.count()+1)
        self.vec_db.add(documents=[task], ids=[str(self.vec_db.count()+1)])
        print(colored(f"SAVING TASK TO DB: {task}", "light_green"))

    def update_task(self, task: str):
        # get the task's id
        result = self.get_task(task)
        self.vec_db.update(ids=[str(result["ids"][0][0])], documents=[task])

    def get_task_str(self, task: str):
        result = self.vec_db.query(query_texts=[task], n_results=1)

        return str(result["documents"][0][0])
    
    def get_task(self, task: str):
        result = self.vec_db.query(query_texts=[task], n_results=1)

        return result
    
    def list_tasks(self):
        results = self.vec_db.get()

        print(results["documents"])

    def get_related_memos(self, query_text: str, n_results: int, threshold: Union[int, float]):
        """Retrieves memos that are related to the given query text within the specified distance threshold."""
        if n_results > len(self.uid_text_dict):
            n_results = len(self.uid_text_dict)
        results = self.vec_db.query(query_texts=[query_text], n_results=n_results)
        memos = []
        num_results = len(results["ids"][0])
        for i in range(num_results):
            uid, input_text, distance = results["ids"][0][i], results["documents"][0][i], results["distances"][0][i]
            if distance < threshold:
                input_text_2, output_text = self.uid_text_dict[uid]
                assert input_text == input_text_2
                if self.verbosity >= 1:
                    print(
                        colored(
                            "\nINPUT-OUTPUT PAIR RETRIEVED FROM VECTOR DATABASE:\n  INPUT1\n    {}\n  OUTPUT\n    {}\n  DISTANCE\n    {}".format(
                                input_text, output_text, distance
                            ),
                            "light_yellow",
                        )
                    )
                memos.append((input_text, output_text, distance))
        return memos
