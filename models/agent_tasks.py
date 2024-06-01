import os
import pyodbc

from termcolor import colored

class Tasks:
    def __init__(self, planId, agentName, taskId):
        # Sample connection string: replace with your actual connection string
        # self.connection_string = "Driver={SQL Server};Server=myServerAddress;Database=myDatabase;Uid=myUsername;Pwd=myPassword;"
        self.connection_string = os.environ.get('SQL_CONNECTIONSTRING')
        self.planId = planId
        self.agentName = agentName
        self.taskId = taskId

    def print_tasks(self):
        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()

            # Call the stored procedure with the appropriate parameters
            cursor.execute("EXECUTE select * from vAllTasks")
            conn.commit()

            for row in cursor.fetchall():
                print(colored(row, "light_green"))

            cursor.close()
            conn.close()

        except pyodbc.Error as e:
            print(f"Error saving task: {e}")

    def add_task(self, taskId: str, agentName: str, taskName: str):
        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()

            # Call the stored procedure with the appropriate parameters
            cursor.execute("EXECUTE dbo.AddTask ?, ?, ?, ?",
                            self.planId, taskId, agentName, taskName)
            conn.commit()

            cursor.close()
            conn.close()

            print(colored(f"Task Added: Agent: {self.agentName}, Task: {taskName} (ID: {self.taskId})", "green"))
        except pyodbc.Error as e:
            print(f"Error saving task: {e}")

    def update_task(self, agentName: str, taskName: str, detail: str, status: str, chat_history: str):
        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()

            # Call the stored procedure with the appropriate parameters
            cursor.execute("EXECUTE dbo.UpdateTask ?, ?, ?, ?, ?, ?, ?",
                            self.planId, self.taskId, agentName, taskName, 
                            status, detail, chat_history)
            conn.commit()

            cursor.close()
            conn.close()

            print(colored(f"Task {taskName} for Agent {self.agentName} updated. New status: {status}", "green"))
        except pyodbc.Error as e:
            print(f"Error updating task: {e}")
    
    def task_exists(self, taskId: str):
        try:
            task_exists = False

            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()

            # Call the stored procedure with the appropriate parameters
            cursor.execute("EXECUTE dbo.RetrieveTask ?",
                            taskId)
            
            row = cursor.fetchval()

            if row != None:
                task_exists = True

            cursor.close()
            conn.close()

            return task_exists
        except pyodbc.Error as e:
            print(f"Error updating task: {e}")