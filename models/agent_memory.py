import os
import pyodbc

from models.agent_context import AgentContext

class Event:
    def __init__(self, role, message, message_type, from_agent_name=None):
        self.role = role
        self.message = message
        self.message_type = message_type
        self.from_agent_name = from_agent_name
        
class Memory:
    def __init__(self, planId, agentName, taskId):
        # Sample connection string: replace with your actual connection string
        # self.connection_string = "Driver={SQL Server};Server=myServerAddress;Database=myDatabase;Uid=myUsername;Pwd=myPassword;"
        self.connection_string = os.environ.get('SQL_CONNECTIONSTRING')
        self.planId = planId
        self.agentName = agentName
        self.taskId = taskId

    def save_to_memory(self, event: Event):
        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()

            # Call the stored procedure with the appropriate parameters
            cursor.execute("EXECUTE dbo.SaveToMemory ?, ?, ?, ?, ?, ?, ?",
                            self.planId, self.agentName, self.taskId, 
                            event.role, event.message, event.message_type, event.from_agent_name)
            conn.commit()

            cursor.close()
            conn.close()
        except pyodbc.Error as e:
            print(f"Error saving to memory: {e}")

    def retrieve_memory(self, lookback: int = -1)->list[Event]:
        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()

            # Call the stored procedure with the appropriate parameters
            cursor.execute("EXECUTE dbo.RetrieveMemory ?, ?, ?",
                            self.planId, self.agentName, self.taskId)
            rows = cursor.fetchall()

            columns = [column[0] for column in cursor.description]
            rows = [dict(zip(columns, row)) for row in rows]

            cursor.close()
            conn.close()

            events = []
            for row in rows:
                role = row['Role']
                message = row['Message']
                message_type = row['MessageType']
                from_agent_name = row['FromAgent']
                event = Event(role, message, message_type, from_agent_name)
                events.append(event)
            
            return events
        except pyodbc.Error as e:
            print(f"Error retrieving memory: {e}")
            return []