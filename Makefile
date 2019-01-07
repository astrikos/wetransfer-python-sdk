VERSION_FILE = "src/wetransfer/version.py"
VERSION = $(shell cat ${VERSION_FILE} | awk -F '"' '{ print $$2 }')

current-version:
	@echo "Current version is ${VERSION}"

build:
	python setup.py bdist_wheel

install: build
	pip install dist/wetransfer-${VERSION}-py2.py3-none-any.whl

_commit:
	git commit ${VERSION_FILE} -m "Bumped version to ${VERSION}"
	git push

release:
	git tag -a v${VERSION} -m "v${VERSION}"
	git push origin v${VERSION}

_patch:
	@echo "__version__ = \"`echo ${VERSION} | awk -F. '{$$NF = $$NF + 1;} 1' | sed 's/ /./g'`\"" > ${VERSION_FILE}.tmp && mv ${VERSION_FILE}.tmp ${VERSION_FILE}
bump-patch: current-version _patch _commit

_minor:
	@echo "__version__ = \"`echo ${VERSION} | awk -F. '{$$(NF-1) = $$(NF-1) + 1; $$(NF) = 0;} 1' | sed 's/ /./g' `\"" > ${VERSION_FILE}.tmp && mv ${VERSION_FILE}.tmp ${VERSION_FILE}
bump-minor: current-version _minor _commit

_major:
	@echo "__version__ = \"`echo ${VERSION} | awk -F. '{$$(NF-2) = $$(NF-2) + 1; $$(NF-1) = 0; $$(NF) = 0;} 1' | sed 's/ /./g'`\"" > ${VERSION_FILE}.tmp && mv ${VERSION_FILE}.tmp ${VERSION_FILE}
bump-major: current-version _major _commit

clean:
	rm -rf dist build
	find . -name "*.pyc" -exec rm -f {} \;

_install_test_deps:
	pip install tox

test: _install_test_deps
	tox

.PHONY: clean
