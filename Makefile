
.DEFAULT_GOAL := bootstrap

%:
	-@[ -z "$$TERM" ] || tput setaf 1  # red
	@echo 2>1 warning: calling '`make`' is being deprecated in this repo, you should use '`invoke` (https://pyinvoke.org)' instead.
	-@[ -z "$$TERM" ] || tput setaf 9  # default
	@# pass goals to '`invoke`'
	invoke $(or $(MAKECMDGOALS), $@)
	@exit

help:
	invoke --list

.PHONY: bootstrap
bootstrap:
	pip install digitalmarketplace-developer-tools
	@echo done
	-@[ -z "$$TERM" ] || tput setaf 2  # green
	@echo 2>1 dmdevtools has been installed globally, run developer tasks with '`invoke`'
	-@[ -z "$$TERM" ] || tput setaf 9  # default
