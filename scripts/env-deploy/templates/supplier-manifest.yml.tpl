applications:
- name: {supplier_name}
  command: scripts/cf_run_app.sh
  buildpack: python_buildpack
  memory: 256M
  disk_quota: 512M
  instances: 1
  services:
  - ups-secret-service
  - {common_config_name}
  - {supplier_config_name}
  routes:
  - route: {env_name}.apps.y.cld.gov.au/sellers
  - route: {supplier_name}.apps.y.cld.gov.au