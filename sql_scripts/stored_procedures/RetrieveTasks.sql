/****** Object:  StoredProcedure [dbo].[RetrieveTasks]    Script Date: 6/4/2024 2:11:33 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE PROCEDURE [dbo].[RetrieveTasks]
    @planId NVARCHAR(50),
    @taskId NVARCHAR(50)
AS
BEGIN
    SELECT * FROM TaskTracker
    WHERE PlanId = @planId AND TaskId = @taskId
END

select * from TaskTracker
GO


