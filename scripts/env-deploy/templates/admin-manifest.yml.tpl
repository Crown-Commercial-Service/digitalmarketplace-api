applications:
- name: {admin_name}
  command: ./scripts/cf_run_app.sh
  buildpack: python_buildpack
  instances: 1
  memory: 256M
  disk_quota: 512M
  services:
  - ups-secret-service
  - {common_config_name}
  - {admin_config_name}
  routes:
  - route: {env_name}.apps.y.cld.gov.au/admin
  - route: {admin_name}.apps.y.cld.gov.au