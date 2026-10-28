CC ?= gcc
CFLAGS ?= -O3 -Wall
PREFIX ?= $(HOME)/.local
BINDIR ?= $(PREFIX)/bin
ICONDIR ?= $(PREFIX)/share/icons

.PHONY: all build install clean

all: build

build: bin/scale_icon

bin/scale_icon: src/scale_icon.c
	@mkdir -p bin
	$(CC) $(CFLAGS) $< -lm -o $@

install: build
	@mkdir -p $(BINDIR) $(ICONDIR)
	install -m 755 install.sh $(BINDIR)/install.sh
	install -m 755 bin/manage-antigravity.sh $(BINDIR)/manage-antigravity.sh
	install -m 755 bin/antigravity-generate-icons.py $(BINDIR)/antigravity-generate-icons.py
	install -m 755 bin/antigravity-apply-icon.py $(BINDIR)/antigravity-apply-icon.py
	install -m 755 bin/antigravity-merge-history.py $(BINDIR)/antigravity-merge-history.py
	install -m 755 bin/antigravity-migration.py $(BINDIR)/antigravity-migration.py
	install -m 755 bin/antigravity-detect.py $(BINDIR)/antigravity-detect.py
	install -m 755 bin/antigravity-keyring.py $(BINDIR)/antigravity-keyring.py
	install -m 755 bin/antigravity-checksums.py $(BINDIR)/antigravity-checksums.py 2>/dev/null || true
	install -m 755 bin/antigravity-benchmark.py $(BINDIR)/antigravity-benchmark.py 2>/dev/null || true
	install -m 755 bin/antigravity-cloud-sync.py $(BINDIR)/antigravity-cloud-sync.py 2>/dev/null || true
	install -m 755 bin/antigravity-models.py $(BINDIR)/antigravity-models.py 2>/dev/null || true
	install -m 755 bin/antigravity-multi-account.py $(BINDIR)/antigravity-multi-account.py 2>/dev/null || true
	install -m 755 bin/antigravity-f5-patch.js $(BINDIR)/antigravity-f5-patch.js 2>/dev/null || true
	install -m 755 bin/antigravity-selector-patch.js $(BINDIR)/antigravity-selector-patch.js 2>/dev/null || true
	install -m 755 bin/antigravity-fork-patch.js $(BINDIR)/antigravity-fork-patch.js 2>/dev/null || true
	install -m 755 bin/scale_icon $(BINDIR)/scale_icon
	mkdir -p $(BINDIR)/lib
	cp -rf bin/lib/* $(BINDIR)/lib/ 2>/dev/null || true
	cp -f assets/antigravity-master-*.png $(ICONDIR)/ 2>/dev/null || true
	mkdir -p $(HOME)/.gemini/config/skills $(HOME)/.gemide/config/skills
	cp -rf skills/whoami skills/accounts skills/switch $(HOME)/.gemini/config/skills/ 2>/dev/null || true
	cp -rf skills/whoami skills/accounts skills/switch $(HOME)/.gemide/config/skills/ 2>/dev/null || true
	@python3 -c 'import site, os; sp = site.getusersitepackages(); os.makedirs(sp, exist_ok=True); open(os.path.join(sp, "antigravity_suite.pth"), "w").write("$(CURDIR)/src\n")' 2>/dev/null || true
	ln -sfn $(BINDIR)/manage-antigravity.sh $(HOME)/manage-antigravity.sh
	ln -sfn $(BINDIR)/install.sh $(HOME)/install.sh
	@echo "Installation successful. Run '~/manage-antigravity.sh' or '~/install.sh' to inspect."

clean:
	rm -f bin/scale_icon /tmp/scaled_*.raw /tmp/raw_*_1024.raw
