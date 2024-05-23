import pyodbc

class SqlManager:
    def __init__(self, server: str, database: str, username: str, password: str):
        # Retrieve the connection strings here
        self.server = server
        self.database = database
        self.username = username
        self.password = password
        self.use_connection_string = False
        
    def __init__(self, connection_string: str):
        # Retrieve the connection strings here
        self.connection_string = connection_string
        self.use_connection_string = True
        
    def __get_connection(self):
        if self.use_connection_string:
            return pyodbc.connect(self.connection_string)
        else:
            return pyodbc.connect(
                f"DRIVER={{ODBC Driver 17for SQL Server}};"
                f"SERVER={self.server};"
                f"DATABASE={self.database};"
                f"UID={self.username};"
                f"PWD={self.password};"
            )
            
    def executeSql(self, sql):
        try:
            # Establish a connection to the Azure SQL database
            conn = self.__get_connection()
            
            # Create a cursor object to execute SQL statements
            cursor = conn.cursor()
            
            # Execute the SQL statement
            cursor.execute(sql)
            
            # Commit the changes (if any)
            conn.commit()
            
            # Close the cursor and connection
            cursor.close()
            conn.close()
            
            # Return any desired result or success message
            return "SQL statement executed successfully"
        
        except pyodbc.Error as e:
            # Handle any errors that occur during execution
            return f"Error executing SQL statement: {str(e)}"