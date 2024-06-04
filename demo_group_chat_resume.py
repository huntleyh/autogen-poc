import json
from typing import List, Dict
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

def add_capability_and_get_history(agent, deliverable: PlanContext, agent_id, agent_name, parent_agent_name, is_group_manager=False):
    # Instantiate a StateAware object. Its parameters are all optional 
    # however we will need to have AgentContext changed at some point
    state_aware_ability = StateAwareNonLlm(
        verbosity=2,
        context= AgentContext(deliverable, agent_id, agent_name, parentAgentName=parent_agent_name),
        is_group_manager=is_group_manager
    )
    
    # Now add state_aware_ability to the agent
    state_aware_ability.add_to_agent(agent)
    
    return state_aware_ability.recollect()
    
async def main():
    deliverable = PlanContext(planId="Plan2", planName="Plan2", deliverableName="Client Profile")
    
    all_messages: List[Dict] = []
    
    # We use an assistant agent as we do not need human interaction for this demo
    analyst = autogen.ConversableAgent( #autogen.AssistantAgent( #
        name="Analyst",
        system_message="Create a two line report for a client profile of 'Disney Corporation' with the current target market of the business. If you do not know then ASK User1 for this info. Do NOT make assumptions.",
        #description=task['Description'],
        llm_config=llm_config,
        #max_consecutive_auto_reply=1,
        human_input_mode="NEVER",
        code_execution_config=False
        #chat_messages=conversation_history
    )
    
    analyst_messages = add_capability_and_get_history(analyst, deliverable, agent_id="1", agent_name="Analyst", parent_agent_name="User1")
    
    # # We use an assistant agent as we do not need human interaction for this demo
    # researcher = autogen.ConversableAgent( #autogen.AssistantAgent( #
    #     name="Researcher",
    #     system_message="Create a one line report of the current CTO of the 'Disney Corporation' business. If you do not know then ASK User1 for this info. Do NOT make assumptions.",
    #     #description=task['Description'],
    #     llm_config=llm_config,
    #     max_consecutive_auto_reply=1,#,
    #     human_input_mode="NEVER",
    #     code_execution_config=False
    #     #chat_messages=conversation_history
    # )
    
    # researcher_messages = add_capability_and_get_history(analyst, deliverable, agent_id="2", agent_name="Researcher", parent_agent_name="User1")
    
    # # We use an assistant agent as we do not need human interaction for this demo
    # critic = autogen.ConversableAgent( #autogen.AssistantAgent( #
    #     name="Critic",
    #     system_message="Critic. You are focused on ensuring the final output is complete. If an agent has an ASK then TERMINATE the discussion and wait for user input.",
    #     #description=task['Description'],
    #     llm_config=llm_config,
    #     max_consecutive_auto_reply=1,#,
    #     human_input_mode="NEVER",
    #     code_execution_config=False
    #     #chat_messages=conversation_history
    # )
    
    # critic_messages = add_capability_and_get_history(analyst, deliverable, agent_id="3", agent_name="Critic", parent_agent_name="User1")
    
    #user_proxy_system_message = "Start building the completed client profile for 'Disney Corporation'."
    user_proxy_system_message = "The company name is 'Disney Corporation'."
    # user_proxy_system_message = """For the length of being in business, use 2 years. 
    # For the profitable months, assume each month was 10% more profitable than the previous month, 
    # starting with $100 USD in January through to December.
    # Do not forget to respond with the JSON as initially instructed.
    # """
    
    user_proxy = autogen.UserProxyAgent( # autogen.AssistantAgent(
            name="User1",
            #system_message=user_proxy_system_message,
            #description=step['Description'],
            llm_config=llm_config,
            human_input_mode="NEVER",
            #max_consecutive_auto_reply=1,
            code_execution_config=False,
            is_termination_msg=lambda user_proxy_system_message: True # Always True so we terminate if we get a message to relay to the user
        )
    
    user_proxy_messages = add_capability_and_get_history(user_proxy, deliverable, agent_id="4", agent_name="User1", parent_agent_name="User1", is_group_manager=True)
    
    # Create a groupchat and groupchat manager based on the task
    groupchat = autogen.GroupChat(
                    [
                        analyst, 
                        # researcher, 
                        #critic
                        user_proxy
                    ], 
                    messages=[],
                    speaker_selection_method="round_robin",
                    max_round=MAX_ROUNDS_PER_GROUP_CHAT)
    manager = autogen.GroupChatManager(
                    groupchat=groupchat, 
                    llm_config=llm_config,
                    system_message="You are the group manager. If there are any questions then ask User1 for input.",
                    name="GroupManager")
    
    group_manager_messages = add_capability_and_get_history_and_get_history(manager, deliverable, agent_id="4", agent_name="GroupManager", parent_agent_name="User1", is_group_manager=True)
    
    for entry in user_proxy_messages:
        all_messages.append(entry)
        #for key in entry.keys():
        #    all_messages.append(key, entry[key])
    for entry in analyst_messages:
        all_messages.append(entry)
        #for key in entry.keys():
        #    all_messages.append(key, entry[key])
    
    for entry in group_manager_messages:
        all_messages.append(entry)
        #for key in entry.keys():
        #    all_messages.append(key, entry[key])
            
    # all_messages += analyst_messages
    # all_messages += group_manager_messages
    # all_messages.append(researcher_messages)
    # all_messages.append(critic_messages)
    # all_messages.append(group_manager_messages)
    
    if(len(all_messages) > 0):
        manager.resume(messages=all_messages)
    
    chat_results = user_proxy.initiate_chat(manager, clear_history=False, message=user_proxy_system_message) #.initiate_chat(manager, message=user_proxy_system_message) #, user_proxy_system_message))
    
    messages_json = manager.chat_messages_for_summary(manager)
    
    json_str = json.dumps(messages_json)
    
    # Write the json_str to a text file
    with open(get_file_name(manager), "w") as file:
        file.write(json_str)
        
    print("Chat results: ", chat_results.summary)
        
def get_file_name(group_manager: autogen.GroupChatManager):
    return f"group_chat_history_{group_manager.name}.txt"

# Run the main function
asyncio.run(main())