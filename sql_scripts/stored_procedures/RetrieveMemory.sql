/****** Object:  StoredProcedure [dbo].[RetrieveMemory]    Script Date: 6/4/2024 1:44:07 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE PROCEDURE [dbo].[RetrieveMemory]
    @planId NVARCHAR(50),
    @agentName NVARCHAR(50),
    @taskId NVARCHAR(50)
AS
BEGIN
    SELECT * FROM MemoryTable m
    WHERE PlanId = @planId AND AgentName = @agentName AND TaskId = @taskId
	ORDER BY m.InsertTimeStamp ASC
END
GO


