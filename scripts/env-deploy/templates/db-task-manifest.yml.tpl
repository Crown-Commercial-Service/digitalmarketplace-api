applications:
- name: {env_name}-db-task
  command: run.sh
  buildpack: python_buildpack
  instances: 1
  memory: 1G
  disk_quota: 512M
  services:
  - {postgres_service_name}