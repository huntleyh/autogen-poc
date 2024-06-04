/****** Object:  Table [dbo].[MemoryTable]    Script Date: 6/4/2024 1:43:28 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[MemoryTable](
	[PlanId] [nvarchar](50) NULL,
	[AgentName] [nvarchar](50) NULL,
	[TaskId] [int] NULL,
	[Role] [nvarchar](50) NULL,
	[Message] [nvarchar](max) NULL,
	[MessageType] [nvarchar](50) NULL,
	[FromAgent] [nvarchar](200) NULL,
	[InsertTimeStamp] [datetime] NOT NULL
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO

ALTER TABLE [dbo].[MemoryTable] ADD  DEFAULT (getdate()) FOR [InsertTimeStamp]
GO


