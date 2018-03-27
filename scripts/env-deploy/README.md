Requirements
https://github.com/cloudfoundry/cli
https://github.com/contraband/autopilot
https://github.com/govau/cf-run-and-wait

Usage
```python deploy.up up --name my-environment```

Limitations:
* Doesn't update environment. Must delete existing by running ```python deploy.py down --name my-environment```

Known Buys/ Issues
* Failed error shows up, but it seems to run fine.
* db-task doesn't start properly.