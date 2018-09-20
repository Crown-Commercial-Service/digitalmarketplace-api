applications:
- name: {buyer_name}
  command: ./scripts/cf_run_app.sh
  buildpack: python_buildpack
  memory: 1G
  disk_quota: 512M
  instances: 1
  routes:
  - route: {env_name}.apps.y.cld.gov.au
  - route: {buyer_name}.apps.y.cld.gov.au
  services:
  - ups-secret-service
  - {common_config_name}
  - {buyer_config_name}