import os
import pyodbc

from termcolor import colored

class Task:
    def __init__(self, is_subtask, task, status, detail):
        self.is_subtask = is_subtask
        self.task = task
        self.status = status
        self.detail = detail

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
    
    def task_exists(self, taskId: str, agent_name: str, task: str):
        try:
            task_exists = False

            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()

            # Call the stored procedure with the appropriate parameters
            cursor.execute("EXECUTE dbo.RetrieveTask ?, ?, ?",
                            taskId, agent_name, task)
            
            row = cursor.fetchval()

            if row != None:
                task_exists = True

            cursor.close()
            conn.close()

            return task_exists
        except pyodbc.Error as e:
            print(f"Error updating task: {e}")
    
    def retrieve_tasks(self)->list[Task]:
        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()

            # Call the stored procedure with the appropriate parameters
            cursor.execute("EXECUTE dbo.RetrieveTasks ?, ?",
                            self.planId, self.taskId)
            rows = cursor.fetchall()

            columns = [column[0] for column in cursor.description]
            rows = [dict(zip(columns, row)) for row in rows]

            cursor.close()
            conn.close()

            tasks = []
            for row in rows:
                is_subtask = False
                agent_name = str(row['AgentName'])
                if agent_name.find('-subtask') != -1:
                    is_subtask = True
                task = row['Task']
                status = row['Status']
                detail = row['Detail']
                task = Task(is_subtask, task, status, detail)
                tasks.append(task)
            
            return tasks
        except pyodbc.Error as e:
            print(f"Error retrieving tasks: {e}")
            return []