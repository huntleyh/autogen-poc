from autogen import GroupChatManager, GroupChat
from models.agent_context import AgentContext
import json

class ResumableGroupChatManager(GroupChatManager):
    groupchat: GroupChat

    def __init__(self, groupchat: GroupChat, context: AgentContext, **kwargs):
        self.groupchat = groupchat
        
        if history:
            self.groupchat.messages = history

        super().__init__(groupchat, **kwargs)

        if history:
            self.restore_from_history(history)

    def restore_from_history(self, history) -> None:
        for message in history:
            # broadcast the message to all agents except the speaker.  
            # This idea is the same way GroupChat is implemented in AutoGen for new messages, this method simply allows us to replay old messages first.
            for agent in self.groupchat.agents:
                if agent != self:
                    self.send(message, agent, request_reply=False, silent=True)

