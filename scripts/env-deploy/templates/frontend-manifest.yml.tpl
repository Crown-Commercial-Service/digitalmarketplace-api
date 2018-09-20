applications:
- name: {frontend_name}
  command:  ./scripts/cf_run_app.sh
  # TODO: once prod is on new envs, switch back to supported buildpack
  buildpack: legacy_marketplace_nodejs_buildpack
  memory: 256M
  disk_quota: 512M
  instances: 1
  services:
  - ups-secret-service
  - {common_config_name}
  - {frontend_config_name}
  routes:
  - route: {frontend_name}.apps.y.cld.gov.au
  - route: {env_name}.apps.y.cld.gov.au/bundle
  - route: {env_name}.apps.y.cld.gov.au/2
  - route: {env_name}.apps.y.cld.gov.au/orams