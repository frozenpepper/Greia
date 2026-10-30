PYTHON ?= python3
PYTHONPATH := src
.PHONY: verify verify-full test test-full test-slow validate assets assets-check visual-assets visual-assets-check footprint shell-check parent-app-test clean-bytecode

# Test lanes (owner: tests/suite_lanes.py). `verify`/`test` run the fast lane
# every turn must keep green; `verify-full`/`test-full` add the heavy
# end-to-end evidence suites (x8 QEMU rigs, install RSS gates,
# whole-repository sweeps); `test-slow` runs only those.
verify: clean-bytecode test validate shell-check footprint parent-app-test
	$(MAKE) clean-bytecode

verify-full: clean-bytecode test-full validate shell-check footprint parent-app-test
	$(MAKE) clean-bytecode

clean-bytecode:
	$(PYTHON) tools/clean_bytecode.py

test: clean-bytecode
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/run_tests.py --lane fast

test-full: clean-bytecode
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/run_tests.py --lane full

test-slow: clean-bytecode
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/run_tests.py --lane slow

validate:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/validate_project.py
	@for activity in activities/*; do \
		if [ -f "$$activity/activity.toml" ]; then \
			PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/validate_activity.py "$$activity" || exit $$?; \
		fi; \
	done

assets:
	$(PYTHON) tools/build_core_icons.py

assets-check:
	$(PYTHON) tools/build_core_icons.py --check

visual-assets:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/build_visual_renditions.py

visual-assets-check:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/validate_visual_renditions.py

shell-check:
	@find build -type f -perm -0100 -print | while read file; do bash -n "$$file"; done

footprint:
	build/footprint-source.sh

# Browser Parent client unit tests (parent-app/). Node >= 18 is optional
# tooling: without it the target prints a skip notice and succeeds.
parent-app-test:
	@if command -v node >/dev/null 2>&1 && [ "$$(node -p 'process.versions.node.split(".")[0]')" -ge 18 ]; then \
		node --test parent-app/tests/*.test.js; \
	else \
		echo "parent-app-test: skipped (Node >= 18 not found on PATH)"; \
	fi
