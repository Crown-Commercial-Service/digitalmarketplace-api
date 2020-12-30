
.DEFAULT_GOAL := bootstrap

%:
	@[ -z $$TERM ] || tput setaf 1  # red
	@echo 2>1 warning: calling '`make`' is being deprecated in this repo, you should use '`invoke` (https://pyinvoke.org)' instead.
	@[ -z $$TERM ] || tput setaf 9  # default
	@# pass goals to '`invoke`'
	invoke $(or $(MAKECMDGOALS), $@)

help:
	invoke --list

.PHONY: bootstrap
bootstrap:
	pip install git+https://github.com/alphagov/digitalmarketplace-developer-tools.git#egg=digitalmarketplace-developer-tools
	@echo done
	@[ -z $$TERM ] || tput setaf 2  # green
	@echo 2>1 dmdevtools has been installed globally, run developer tasks with '`invoke`'
	@[ -z $$TERM ] || tput setaf 9  # default
