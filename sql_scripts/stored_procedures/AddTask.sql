/****** Object:  StoredProcedure [dbo].[AddTask]    Script Date: 6/4/2024 2:10:46 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO



CREATE PROCEDURE [dbo].[AddTask]
    @planId NVARCHAR(50),
	@taskId NVARCHAR(50),
	@agentName NVARCHAR(50),
	@task NVARCHAR(MAX)

AS
BEGIN
    INSERT INTO TaskTracker (PlanId, TaskId, AgentName, Task, insert_timestamp, Status, Detail)
    VALUES (@planId, @taskId, @agentName, @task, getdate(), 'NOT DONE', 'Not started')
END
GO


