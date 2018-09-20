applications:
- name: {api_name}
  command: ./scripts/cf_run_app.sh
  buildpack: python_buildpack
  health-check-type: port
  health-check-timeout: 180
  instances: 1
  memory: 512M
  disk_quota: 512M
  services:
  - ups-secret-service
  - {postgres_service_name}
  - {common_config_name}
  - {api_config_name}
  routes:
  - route: {env_name}.apps.y.cld.gov.au/api
  - route: {api_name}.apps.y.cld.gov.au