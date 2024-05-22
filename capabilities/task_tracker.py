import json
import os
import pickle
from typing import Dict, Optional, Union

import chromadb
from chromadb.config import Settings

from autogen.agentchat.assistant_agent import ConversableAgent
from autogen.agentchat.contrib.capabilities.agent_capability import AgentCapability
from autogen.agentchat.contrib.text_analyzer_agent import TextAnalyzerAgent
from autogen import Agent
from domain_knowledge.direct_aoai import retrieve_llm_response_on_question
from datastore.sql_db_manager import SqlManager

from termcolor import colored

class TaskTrackingbility(AgentCapability):
    """
    TaskTrackingbility uses a vector database to give an agent the ability to remember user teachings,
    where the user is any caller (human or not) sending messages to the teachable agent.
    TaskTrackingbility is designed to be composable with other agent capabilities.
    To make any conversable agent teachable, instantiate both the agent and the TaskTrackingbility class,
    then pass the agent to TaskTrackingbility.add_to_agent(agent).
    Note that teachable agents in a group chat must be given unique path_to_db_dir values.

    When adding TaskTrackingbility to an agent, the following are modified:
    - The agent's system message is appended with a note about the agent's new ability.
    - A hook is added to the agent's `process_last_received_message` hookable method,
    and the hook potentially modifies the last of the received messages to include earlier teachings related to the message.
    Added teachings do not propagate into the stored message history.
    If new user teachings are detected, they are added to new memos in the vector database.
    """

    def __init__(
        self,
        verbosity: Optional[int] = 0,
        reset_db: Optional[bool] = False,
        path_to_db_dir: Optional[str] = "./tmp/tracker_agent_db",
        recall_threshold: Optional[float] = 1.5,
        max_num_retrievals: Optional[int] = 10,
        llm_config: Optional[Union[Dict, bool]] = None,
    ):
        """
        Args:
            verbosity (Optional, int): # 0 (default) for basic info, 1 to add memory operations, 2 for analyzer messages, 3 for memo lists.
            reset_db (Optional, bool): True to clear the DB before starting. Default False.
            path_to_db_dir (Optional, str): path to the directory where this particular agent's DB is stored. Default "./tmp/tracker_agent_db"
            recall_threshold (Optional, float): The maximum distance for retrieved memos, where 0.0 is exact match. Default 1.5. Larger values allow more (but less relevant) memos to be recalled.
            max_num_retrievals (Optional, int): The maximum number of memos to retrieve from the DB. Default 10.
            llm_config (dict or False): llm inference configuration passed to TextAnalyzerAgent.
                If None, TextAnalyzerAgent uses llm_config from the teachable agent.
        """
        self.verbosity = verbosity
        self.path_to_db_dir = path_to_db_dir
        self.recall_threshold = recall_threshold
        self.max_num_retrievals = max_num_retrievals
        self.llm_config = llm_config

        self.analyzer = None
        self.tracker_agent = None
        self.message_count = 0

        # Create the memo store.
        # self.memo_store = MemoStore(self.verbosity, reset_db, self.path_to_db_dir)

    def add_to_agent(self, agent: ConversableAgent):
        """Adds TaskTrackingbility to the given agent."""
        self.tracker_agent = agent

        # Register a hook for processing the last message.
        agent.register_hook(hookable_method="process_last_received_message", hook=self.process_last_received_message)
        # Register a hook for processing the message before it is sent to determine if the task was completed.
        agent.register_hook(hookable_method="process_message_before_send", hook=self.process_message_before_send)

        # Was an llm_config passed to the constructor?
        if self.llm_config is None:
            # No. Use the agent's llm_config.
            self.llm_config = agent.llm_config
        assert self.llm_config, "TaskTrackingbility requires a valid llm_config."

        # Create the analyzer agent.
        self.analyzer = TextAnalyzerAgent(llm_config=self.llm_config)

        # Append extra info to the system message.
        agent.update_system_message(
            agent.system_message
            + "\nYou've been given the special ability to confirm the steps needed to complete the recieved task and persist the status of those steps to a datastore."
        )

    def retrieve_steps(self, text: Union[Dict, str])->str:
        """Tries to retrieve the steps needed to complete a task."""
        
        return """
    1. Get name of company
    2. Get how long the company's been in business
    3. Get how many months are profitable
    """
        memo_added = False

        # Check for a problem or task request.
        response = self._analyze(
            text,
            "Does any part of the TEXT ask the agent to perform a task or solve a problem? Answer with just one word, yes or no.",
        )
        if "yes" in response.lower():
            # Can we extract the task or problem?
            advice = self._analyze(
                text,
                "Summarize very briefly the actual task or problem being asked from the TEXT. But if no task or problem is present, just respond with 'none'.",
            )
            if "none" not in advice.lower():
                # Yes. Extract the task.
                task = self._analyze(
                    text,
                    "Briefly copy just the task or problem from the TEXT, then stop. Don't solve it, and don't include any advice.",
                )
        
        question = f"Respond with only the steps needed to perform this task with no additional detail or advice: {task}."

        return retrieve_llm_response_on_question(question)

    def process_message_before_send(self, sender: Agent, message: Union[Dict, str], recipient: Agent, silent: bool):
        """
        Checks the message before sending to confirm if a task was completed or not.
        Uses TextAnalyzerAgent to make decisions about whether to persist that step .
        """
        
        self.update_tasks(message)
        
        return message

    def process_last_received_message(self, text: Union[Dict, str]):
        """
        If this is the first message recieved then get the list of steps needed to complete the task and appends it with instructions
        so we can keep track of completed items.
        Uses TextAnalyzerAgent to make decisions about actual ask from the sender.
        """
        
        response_instructions = """
        At the end of your response ensure to include the exact verbiage of the step or steps you performed as well as a status for that step. 
        The format should be a single line with a JSON formatted string in the format: { "STEP": "your task here", "STATUS": "status of the step", "DETAIL": "additional detail" }
        Valid statuses are: IN_PROGRESS, BLOCKED, TODO
        The "Detail" property will include any additional detail such as error messages or asking for additional information or documents needed to complete the step
        Do not include additional detail at the end of your response.       
        """
        # response_instructions = """
        # At the end of your response ensure to include the exact verbiage of the step or steps you performed as well as a status for that step. 
        # The format should be two lines with the first line being: "STEP: {your task here}"
        # and the second line: "STATUS: {status of the step}"
        # Valid statuses are: IN_PROGRESS, BLOCKED, TODO
        # Do not include additional detail at the end of your response.       
        # """
        if self.message_count == 0:
            required_steps = self.retrieve_steps(text)
            
            text = f"""
            This is your task: 
            
            {text}
            
            -----
            To complete this task:
            {required_steps}
            
            ----
            {response_instructions}
            """
            
        if self.verbosity >= 1:
            print(colored(f"\nUsing text:\n\n{text}", "light_yellow"))
        
        self.message_count = self.message_count + 1
        return text
    
    def update_tasks(self, text_with_steps: Union[Dict, str]):
        try:
            sqlManager = SqlManager(os.environ["SQL_CONNECTIONSTRING"])
            sqlManager.executeSql(f"""
                                    INSERT INTO dbo.TaskTracker (Task, Status, Detail)
                                    VALUES ('Get name of company', 'IN_PROGRESS', 'Some detail')
                                  """)
        except Exception as e:
            print(f"Error: {str(e)}")
        
        # for line in text_with_steps.reversed:
        #     # read the json from this line, eg { "STEP": "Get name of company", "STATUS": "IN_PROGRESS", "DETAIL": "" }
        #     stepResult = json.loads(line)
        #     status = stepResult["STATUS"]
        #     if status in ["IN_PROGRESS", "BLOCKED", "TODO"]:
        #         step = text_with_steps[text_with_steps.index(line) - 1].split(":")[1].strip()
        #         # self.save_task(step, status)   
        #     if self.verbosity >= 1:
        #         print(colored(f"\nSaving task:\n\nTask: {stepResult["STEP"]} \nStatus: {stepResult["STATUS"]}", "light_yellow"))

    def _analyze(self, text_to_analyze: Union[Dict, str], analysis_instructions: Union[Dict, str]):
        """Asks TextAnalyzerAgent to analyze the given text according to specific instructions."""
        self.analyzer.reset()  # Clear the analyzer's list of messages.
        self.tracker_agent.send(
            recipient=self.analyzer, message=text_to_analyze, request_reply=False, silent=(self.verbosity < 2)
        )  # Put the message in the analyzer's list.
        self.tracker_agent.send(
            recipient=self.analyzer, message=analysis_instructions, request_reply=True, silent=(self.verbosity < 2)
        )  # Request the reply.
        return self.tracker_agent.last_message(self.analyzer)["content"]
