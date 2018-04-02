Requirements
https://github.com/cloudfoundry/cli
https://github.com/contraband/autopilot
https://github.com/govau/cf-run-and-wait

Usage
```cd scripts/env-deploy
# first time only
mkdir temp
python deploy.py up --name my-environment```

Limitations:
* Doesn't update environment. Must delete existing by running ```python deploy.py down --name my-environment```
* Assumes other repos have been cloned relative to this repo

Known Buys/ Issues
* Failed error shows up, but it seems to run fine.
* db-task doesn't start properly.
