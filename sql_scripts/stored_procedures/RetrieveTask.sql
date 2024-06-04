/****** Object:  StoredProcedure [dbo].[RetrieveTask]    Script Date: 6/4/2024 2:11:07 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO


ALTER PROCEDURE [dbo].[RetrieveTask]
	@taskId nvarchar(50),
	@agentName nvarchar(200),
	@task nvarchar(500)

AS
BEGIN
    Select Task FROM TaskTracker WHERE TaskId = @taskId and AgentName = @agentName and Task = @task
END
