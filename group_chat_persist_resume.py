import json
import autogen
import asyncio
# from sqlalchemy import create_engine

import urllib
import os
from capabilities.stateaware import StateAware
from domain_knowledge.direct_aoai import retrieve_llm_response_on_question
from capabilities.task_tracker import TaskTrackingbility
from capabilities.stateaware_non_llm import StateAwareNonLlm
from models.agent_context import AgentContext, PlanContext

config_list = autogen.config_list_from_json(env_or_file="AOAI_CONFIG_LIST")
llm_config = {"config_list": config_list}

SEQUENTIAL_STEP = "SequentialStep"
PARALLEL_STEP = "ParallelStep"
MAX_TURNS_PER_AGENT = 5
MAX_ROUNDS_PER_GROUP_CHAT = 12

# Retrieve the existing plan for a customer
def retrieve_plan(customer_id: str, file_name: str):
    # Open the JSON file and load it into a Python object
    with open(file_name) as f:
        data = json.load(f)
        
        return data

# Execute the plan retrieved for the customer
async def execute_plan(plan: json):
    carry_over = ""
    user_feedback = None
    #user_feedback = "For the 3rd step \"How many months are profitable\" you can assume the latest financial reports show a profit of 10% each month on average"
    deliverable = retrieve_deliverable(plan)
    
    # Iterate over the "Steps" array
    for step in plan['Steps']:
        #print(f"Step ID: {step['Id']}, Step Name: {step['Name']}")

        print(f"\tRunning a {step['Type']} step")
        if(step['Type'] == SEQUENTIAL_STEP):
            carry_over = run_sequential_tasks(deliverable=deliverable, step=step, carry_over=carry_over, user_feedback=user_feedback)

def retrieve_deliverable(plan: json)->PlanContext:
    deliverable = PlanContext(planId=plan['Id'], planName=plan['Name'], deliverableName=plan['DeliverableName'])
    
    return deliverable
    
def create_group_for_task(groupTask: json, deliverable: PlanContext, parent_agent_name: str, is_state_aware: bool = True):
    agents = []
    for task in groupTask['SubTasks']:
        print(f"\tIn GroupTask, creating agent for Task: {task['Name']}")
        agents.append(create_agent_for_task(task=task, deliverable=deliverable, parent_agent_name=parent_agent_name, is_state_aware=is_state_aware))
        
    # Create a groupchat and groupchat manager based on the task
    groupchat = autogen.GroupChat(agents=agents, messages=[], max_round=MAX_ROUNDS_PER_GROUP_CHAT)
    manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config, name=groupTask['Name'], system_message=groupTask['InitialMessage'])

    # if True: #is_state_aware == True:
    #     # Instantiate a StateAware object. Its parameters are all optional.
    #     state_aware_ability = StateAwareNonLlm(
    #         verbosity=2,
    #         context= AgentContext(deliverable, groupTask['Id'], groupTask['Name'])#, taskType)
    #     )
        
    #     # Inject user feedback
    #     # TODO: 

    #     # Now add state_aware_ability to the agent
    #     state_aware_ability.add_to_agent(manager)
        
        #state_aware_ability.recollect_and_hydrate()

        # task_aware_ability = TaskTrackingbility(
        # reset_db=False,  # Use True to force-reset the memo DB, and False to use an existing DB.
        # path_to_db_dir="./tmp/interactive/stateaware_db",  # Can be any path, but StateAware agents in a group chat require unique paths.
        # verbosity=2
        # )
        
    # messages = retrieve_group_chat_messages(manager)
    # if messages is not None:
    #     groupchat.messages = messages
        
    return manager

def persist_messages_to_agent_memory(recipient, messages, sender, config): 
    if "callback" in config and  config["callback"] is not None:
        callback = config["callback"]
        callback(sender, recipient, messages[-1])
    print(f"Messages sent to: {recipient.name} | num messages: {len(messages)}")
    return False, None  # required to ensure the agent communication flow continues


# Create an agent for a specific task
def create_agent_for_task(task: json, deliverable: PlanContext, parent_agent_name: str, is_state_aware: bool = True):    
    taskType = None
    
    if 'Type' in task:
        taskType = task['Type']
        
    print(f"\tTask: {task['Name']}, Type: {taskType}")
    if taskType != None and taskType == "Group":
        return create_group_for_task(task, deliverable,parent_agent_name)
    else:     
        
        # Create an agent based on the task
        # We use an assistant agent as we do not need human interaction for this demo
        assistant = autogen.ConversableAgent( #autogen.AssistantAgent( #
            name=task['Name'],
            system_message=task['InitialMessage'],
            #description=task['Description'],
            llm_config=llm_config,
            max_consecutive_auto_reply=1,#,
            human_input_mode="NEVER",
            code_execution_config=False
            #chat_messages=conversation_history
        )
        if True: #is_state_aware == True:
            # Instantiate a StateAware object. Its parameters are all optional.
            state_aware_ability = StateAwareNonLlm(
                verbosity=2,
                context= AgentContext(deliverable, task['Id'], task['Name'], parentAgentName=parent_agent_name)#, taskType)
            )
            
            # Inject user feedback
            # TODO: 

            # Now add state_aware_ability to the agent
            state_aware_ability.add_to_agent(assistant)
        
        # task_aware_ability.add_to_agent(assistant)
        
        return assistant

# Build the array used to send list of agents to a sequential chat
def build_agent_list_with_prereqs(agents: list, tasks: list):
    agent_list = []
    
    for agent in agents:
        task = tasks[agents.index(agent)]
        # print(f"\tTask: {task['Name']}, Prerequisites: {task['Prerequisites']}")
        prerequisites = task.get('Prerequisites', [])
        if prerequisites is not None and isinstance(prerequisites, list):
            prerequisites = [] #prerequisites
        else:
            prerequisites = []
        # print(f"\tPrerequisites: {prerequisites}")
        agent_list.append({
            "chat_id": task['Id'],
            "recipient": agent,
            "message": agent.system_message,
            "clear_history": False, # Do not clear the history
            "max_turns": MAX_TURNS_PER_AGENT,
            "summary_method": "last_msg",
            "silent": False,
            "prerequisites": prerequisites
        })
    
    return agent_list
        
# Build the array used to send list of agents to a sequential chat
def build_agent_list(agents: list, user_feedback: str = None, clear_history: bool = False):
    agent_list = []
        
    for agent in agents:
        message = user_feedback if user_feedback else agent.system_message
        
        agent_list.append({
            "recipient": agent,
            "message": message, #agent.system_message,
            "clear_history": clear_history, # Do not clear the history
            "max_turns": MAX_TURNS_PER_AGENT,
            "summary_method": "last_msg",
        })
    
    return agent_list

# Execute a sequential step with the carry_over from previous chats as needed
def run_sequential_tasks(deliverable: AgentContext, step: json, carry_over: str, user_feedback: str = None):
    agents = []
    group_managers = []
    
    # Iterate over the "Tasks" array within each step
    for task in step['Tasks']:
        if 'Type' in task:
            taskType = task['Type']
            
        # print(f"\tTask: {task['Name']}, Type: {taskType}")
        if taskType != None and taskType == "Group":
            group_managers.append(create_group_for_task(groupTask=task, deliverable=deliverable, parent_agent_name=step['Name']))
        else:
            agents.append(create_agent_for_task(task, deliverable=deliverable, parent_agent_name=step['Name']))    
    
    user_proxy_system_message = user_feedback if user_feedback else step['InitialMessage']
    
    # initiate the chat with the agents
    # The Number Agent always returns the same numbers.
    step_agent = autogen.UserProxyAgent( # autogen.AssistantAgent(
        name=step['Name'],
        #system_message=step['InitialMessage'],
        description=step['Description'],
        llm_config=llm_config,
        #human_input_mode="NEVER",
        max_consecutive_auto_reply=1,
        code_execution_config=False,
        is_termination_msg=lambda user_proxy_system_message: True # Always True so we terminate if we get a message to relay to the user
    )
    
    print(f"\tName: {step['Name']}, InitialMessage: {step['InitialMessage']}, Description: {step['Description']}")
    
    if(len(group_managers) > 0):

        chat_results = step_agent.initiate_chats(build_agent_list(group_managers, user_proxy_system_message))
        
        # For each groupchat manager we store their conversation history so we can retrieve it afterward
        # TODO: Move to a DB so we can handle store/retrieve better
        for group_manager in group_managers:
            manager: autogen.GroupChatManager = group_manager
            
            persist_group_chat(manager)
    else:
        chat_results = step_agent.initiate_chats(build_agent_list(agents, user_proxy_system_message))
    
    summary = chat_results[-1].summary
    print(f"\t Returning carry_over summary of: {summary}")
    return summary

# Read the json_str from a text file
def retrieve_group_chat_messages(group_manager: autogen.GroupChatManager):
    # Read the json_str from a text file
    file_name = get_file_name(group_manager)
    if os.path.exists(file_name):
        with open(file_name, "r") as file:
            json_str = file.read()
            return json.loads(json_str)
    else:
        return None
    
def persist_group_chat(group_manager: autogen.GroupChatManager):
    messages_json = group_manager.chat_messages_for_summary(group_manager)
    
    json_str = json.dumps(messages_json)
    
    # Write the json_str to a text file
    with open(get_file_name(group_manager), "w") as file:
        file.write(json_str)

def get_file_name(group_manager: autogen.GroupChatManager):
    return f"group_chat_history_{group_manager.name}.txt"

async def main():
    plan = retrieve_plan("123", "sample_plan_group_only.json")
    
    await execute_plan(plan)

# Run the main function
asyncio.run(main())