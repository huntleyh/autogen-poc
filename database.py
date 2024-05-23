import os
import pyodbc
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase
from termcolor import colored

SERVER = os.environ["SERVER"]
DATABASE = os.environ["DATABASE"]
USERNAME = os.environ["USERNAME"]
PASSWORD = os.environ["PASSWORD"]
connectionString = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD}'

class Tasks:

    def update_task(self, agent_name: str, task: str, detail: str, status: str):
        global connectionString
        conn = pyodbc.connect(connectionString)
        cursor = conn.cursor()

        # if the task has any single quotes, we need to replace with two single quotes to avoid an unclosed quotation mark
        task = task.replace("'", "''")

        SQL_STATEMENT = f"""
            Update TaskTracker
            Set Status = '{status}', Detail = '{detail}'
            Where Agent = '{agent_name}' and Task = '{task}'
            """
        cursor.execute(
            SQL_STATEMENT            
        )
        
        conn.commit()

        print(colored(f"Task {task}, for Agent {agent_name} updated. New status: {status}", "green"))

    # Print all tasks that exist in the database
    def print_tasks(self):
        global connectionString
        conn = pyodbc.connect(connectionString)
        cursor = conn.cursor()

        SQL_STATEMENT = """
            Select * from TaskTracker
            """
        cursor.execute(
            SQL_STATEMENT
        )
        for row in cursor.fetchall():
            print(colored(row, "light_green"))

    # Determines if a task exists in the database or not
    def task_exists(self, task: str):
        task_exists = False

        global connectionString
        conn = pyodbc.connect(connectionString)
        cursor = conn.cursor()

        SQL_STATEMENT = f"""
            Select Task from TaskTracker where Task = '{task}'
            """
        cursor.execute(
            SQL_STATEMENT
        )

        row = cursor.fetchval()

        if row != None:
            task_exists = True
        
        return task_exists


    def add_task(self, agent_name: str, task: str):
        global connectionString
        conn = pyodbc.connect(connectionString)
        cursor = conn.cursor()

        SQL_STATEMENT = """
            INSERT TaskTracker (
            Agent,
            Task, 
            Status,
            Detail
            ) OUTPUT INSERTED.ID 
            VALUES (?, ?, ?, ?)
            """
        cursor.execute(
            SQL_STATEMENT,
            agent_name,
            task,
            f'NOT DONE', # all new tasks start as NOT DONE
            'Not started'
        )
        resultId = cursor.fetchval()
        conn.commit()

        print(colored(f"Task Added: Agent: {agent_name}, Task: {task} (ID: {resultId})", "green"))