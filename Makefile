PYTHON ?= python3
PYTHONPATH := src
PYTHON_SOURCE_ROOTS := src tests tools activities

.PHONY: verify test validate assets visual-assets visual-assets-check footprint shell-check clean-bytecode

verify: clean-bytecode test validate shell-check footprint
	$(MAKE) clean-bytecode

clean-bytecode:
	$(PYTHON) tools/clean_bytecode.py

test: clean-bytecode
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest discover -s tests -v

validate:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/validate_project.py
	@for activity in activities/*; do \
		if [ -f "$$activity/activity.toml" ]; then \
			PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/validate_activity.py "$$activity" || exit $$?; \
		fi; \
	done

assets:
	$(PYTHON) tools/extract_core_icons.py \
		--source assets/source/core_icons_v1_source.png \
		--output-root assets/icons/core/v1 \
		--catalog assets/catalog/core_icons_v1.toml \
		--contact-sheet assets/catalog/core_icons_v1_contact_sheet.png

visual-assets:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/build_visual_renditions.py

visual-assets-check:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/validate_visual_renditions.py

shell-check:
	@find build -type f -perm -0100 -print | while read file; do bash -n "$$file"; done

footprint:
	build/footprint-source.sh
