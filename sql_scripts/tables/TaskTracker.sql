/****** Object:  Table [dbo].[TaskTracker]    Script Date: 6/4/2024 1:43:40 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[TaskTracker](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[PlanId] [nvarchar](50) NOT NULL,
	[TaskId] [nvarchar](50) NOT NULL,
	[AgentName] [nvarchar](200) NULL,
	[Task] [nvarchar](500) NULL,
	[insert_timestamp] [datetime] NOT NULL,
	[Status] [nvarchar](500) NOT NULL,
	[Detail] [nvarchar](500) NULL,
	[ChatHistory] [nvarchar](500) NULL,
 CONSTRAINT [PK_TaskTracker] PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO

ALTER TABLE [dbo].[TaskTracker] ADD  CONSTRAINT [DF_TaskTracker_insert_timestamp]  DEFAULT (getdate()) FOR [insert_timestamp]
GO


