import json
import autogen
import asyncio
# from sqlalchemy import create_engine

import urllib
import os
from capabilities.stateaware import StateAware
from capabilities.stateaware_non_llm import StateAwareNonLlm

config_list = autogen.config_list_from_json(env_or_file="AOAI_CONFIG_LIST")
llm_config = {"config_list": config_list}

SEQUENTIAL_STEP = "SequentialStep"
PARALLEL_STEP = "ParallelStep"

# Retrieve the existing plan for a customer
def retrieve_plan(customer_id: str, file_name: str = "sample_plan_simplified.json"):
    # Open the JSON file and load it into a Python object
    with open(file_name) as f:
        data = json.load(f)
        
        return data

# Execute the plan retrieved for the customer
async def execute_plan(plan: json):
    carry_over = ""
    # Iterate over the "Steps" array
    for step in plan['Steps']:
        #print(f"Step ID: {step['Id']}, Step Name: {step['Name']}")

        print(f"\tRunning a {step['Type']} step")
        if(step['Type'] == SEQUENTIAL_STEP):
            carry_over = run_sequential_tasks(step, carry_over)
        elif(step['Type'] == PARALLEL_STEP):
            #carry_over = await run_parallel_tasks(step, carry_over)
            carry_over = ""

def create_group_for_task(groupTask: json):
    agents = []
    for task in groupTask['SubTasks']:
        agents.append(create_agent_for_task(task, False))
        
    # Create a groupchat and groupchat manager based on the task
    groupchat = autogen.GroupChat(agents=agents, messages=[], max_round=12)
    manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)

    return manager

# Create an agent for a specific task
def create_agent_for_task(task: json, is_state_aware: bool = True):    
    taskType = None
    
    if 'Type' in task:
        taskType = task['Type']
        
    print(f"\tTask: {task['Name']}, Type: {taskType}")
    if taskType != None and taskType == "Group":
        return create_group_for_task(task)
    else:
        # Create an agent based on the task
        # We use an assistant agent as we do not need human interaction for this demo
        assistant = autogen.AssistantAgent( #autogen.ConversableAgent( #
            name=task['Name'],
            system_message=task['InitialMessage'],
            #description=task['Description'],
            llm_config=llm_config,
        )
        
        if is_state_aware == True:
            # Instantiate a StateAware object. Its parameters are all optional.
            #state_aware_ability = StateAware(
            state_aware_ability = StateAwareNonLlm(
                #reset_db=False,  # Use True to force-reset the memo DB, and False to use an existing DB.
                #path_to_db_dir="./tmp/interactive/stateaware_db",  # Can be any path, but StateAware agents in a group chat require unique paths.
                verbosity=2
            )

            # Now add state_aware_ability to the agent
            state_aware_ability.add_to_agent(assistant)
    
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
            "max_turns": 2,
            "summary_method": "last_msg",
            "silent": False,
            "prerequisites": prerequisites
        })
    
    return agent_list
        
# Build the array used to send list of agents to a sequential chat
def build_agent_list(agents: list):
    agent_list = []
    
    for agent in agents:
        agent_list.append({
            "recipient": agent,
            "message": agent.system_message,
            "max_turns": 1,
            "summary_method": "last_msg",
        })
    
    return agent_list

# Execute a sequential step with the carry_over from previous chats as needed
def run_sequential_tasks(step: json, carry_over: str):
    agents = []
    group_managers = []
    
    # Iterate over the "Tasks" array within each step
    for task in step['Tasks']:
        # agents.append(create_agent_for_task(task))
            if 'Type' in task:
                taskType = task['Type']
                
            print(f"\tTask: {task['Name']}, Type: {taskType}")
            if taskType != None and taskType == "Group":
                group_managers.append(create_group_for_task(task))
            else:
                agents.append(create_agent_for_task(task))
    
    # initiate the chat with the agents
    # The Number Agent always returns the same numbers.
    step_agent = autogen.AssistantAgent( #ConversableAgent( #
        name=step['Name'],
        system_message=step['InitialMessage'],
        description=step['Description'],
        llm_config=llm_config,
        human_input_mode="NEVER",
    )
    
    if(group_managers.__len__() > 0):
        chat_results = step_agent.initiate_chats(build_agent_list(group_managers))
        
        manager: autogen.GroupChatManager = group_managers[0]
        
        messages_json = manager.chat_messages_for_summary(manager)
        
        json_str = json.dumps(messages_json)
        
        # Write the json_str to a text file
        with open("group_chat_history.txt", "w") as file:
            file.write(json_str)
    else:
        chat_results = step_agent.initiate_chats(build_agent_list(agents))
    
    summary = chat_results[-1].summary
    print(f"\t Returning carry_over summary of: {summary}")
    return summary
    
# Execute a parallel step
async def run_parallel_tasks(step: json, carry_over: str):
    agents = []
    tasks = []
    # Iterate over the "Tasks" array within each step
    for task in step['Tasks']:
        # Check the db to see if this task exists; if it does not, add it to the db. If it does,
        # check the done value so we know if an agent should be created for this task or not
        # TODO
        # print(f"\tTask: {task['Name']}, Prerequisites: {task['Prerequisites']}")
        agents.append(create_agent_for_task(task))
        tasks.append(task)
    
    # initiate the chat with the agents
    step_agent = autogen.AssistantAgent(
        name=step['Name'],
        system_message=step['InitialMessage'],
        description=step['Description'],
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    agent_list = build_agent_list_with_prereqs(agents, tasks)
    chat_results = await step_agent.a_initiate_chats(agent_list)
    
    # Use the chat id as the key to retrieve the summary
    summary = chat_results['3'].summary
    print(f"\tSummary: {summary}")
    return "summary"

async def main():
    plan = retrieve_plan("123", "sample_plan_group_only.json")
    
    await execute_plan(plan)

# Run the main function
asyncio.run(main())