/****** Object:  StoredProcedure [dbo].[UpdateTask]    Script Date: 6/4/2024 2:11:56 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO


CREATE PROCEDURE [dbo].[UpdateTask]
    @planId NVARCHAR(50),
	@taskId NVARCHAR(50),
	@agentName NVARCHAR(50),
	@task NVARCHAR(MAX),
	@status NVARCHAR(50),
	@detail NVARCHAR(500),
	@chat_history NVARCHAR(500)
    
AS
BEGIN
    UPDATE TaskTracker
	Set Status = @status, Detail = @detail, ChatHistory = @chat_history
    Where AgentName = @agentName and Task = @task
END
GO


