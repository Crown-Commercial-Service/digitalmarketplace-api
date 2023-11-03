# docker-aws

Changes to the Docker build process for the 2023 AWS native migration.

## Explanation

The DMP1.5 (and 1.0) task architecture is as follows: a Supervisord task which runs Nginx, uWSGI and awslogs. Some points about this:

We do not require an awslogs router task anymore, rather just to write the logs to stdout / stderr and let Docker and the ECS-included awslogs driver route these naturally to CloudWatch Logs

Supervisord is a poor task manager for an ECS task because it maintains the perception of a healthy container even when a sub-process (e.g. uWSGI) has died (zombie tasks are pretty common in this case)

We must therefore arrive at an alternative architecture for the ECS Tasks and a change of Docker build process to support this. Please see ticket and code changes for [GMBP-195](https://crowncommercialservice.atlassian.net/browse/GMBP-195) for a more detailed explanation.