/****** Object:  StoredProcedure [dbo].[SaveToMemory]    Script Date: 6/4/2024 1:46:49 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE PROCEDURE [dbo].[SaveToMemory]
    @planId NVARCHAR(50),
    @agentName NVARCHAR(200),
    @taskId NVARCHAR(50),
    @role NVARCHAR(50),
    @message NVARCHAR(MAX),
    @message_type NVARCHAR(50),
	@fromAgentName NVARCHAR(200)
AS
BEGIN
    INSERT INTO MemoryTable (PlanId, AgentName, TaskId, Role, Message, MessageType, FromAgent)
    VALUES (@planId, @agentName, @taskId, @role, @message, @message_type, @fromAgentName)
END
GO
