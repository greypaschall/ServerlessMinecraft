AWS Stateless Minecraft Server 
-------------------------------

This project has been my introduction to automation basics and cloud hosting services. Using the foundational knowledge I gained while studying for my AWS solutions architect certification, I set out to build the cheapest possible Minecraft server, with minimal overhead and no manual upkeep. This system can spin up only when needed and stay off when idle. 

Costs:
___________

*Idle Costs:

-t4g.nano EC2 instance ~ $3.10/month (This small Ubuntu server runs the TCP listener in a tmux session 24/7)
  - associated EBS volume ~ $0.80/month (gp2 volume with 8gb stores Python listener script)

Active Costs (You are only charged when a player is using the server):

-t3.large EC2 instance ~ $0.0832/hour 
  -associated EBS volume ~ $0.00088/hour (temporary volume provisioned at startup and deleted at shutdown)


*Free Services:

-S3
-VPC w/ S3 Gateway

*Free in the context of this architecture:

-CloudWatch
-SNS
-StartMinecraftServer AWS Lambda ~  Free invocations under 1 million rquests
-StopMinecraftServer AWS Lambda ~ Free invocations under 1 million rquests





