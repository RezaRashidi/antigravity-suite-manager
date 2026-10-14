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
	install -m 755 bin/manage-antigravity.sh $(BINDIR)/manage-antigravity.sh
	install -m 755 bin/antigravity-generate-icons.py $(BINDIR)/antigravity-generate-icons.py
	install -m 755 bin/antigravity-apply-icon.py $(BINDIR)/antigravity-apply-icon.py
	install -m 755 bin/scale_icon $(BINDIR)/scale_icon
	cp -f assets/antigravity-master-*.png $(ICONDIR)/ 2>/dev/null || true
	ln -sfn $(BINDIR)/manage-antigravity.sh $(HOME)/manage-antigravity.sh
	@echo "Installation successful. Run '~/manage-antigravity.sh status' to inspect."

clean:
	rm -f bin/scale_icon /tmp/scaled_*.raw /tmp/raw_*_1024.raw
