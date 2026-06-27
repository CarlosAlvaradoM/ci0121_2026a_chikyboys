P4C := p4c
TARGET := bmv2
ARCH := v1model
JSON := build/dns_cache.json

all: $(JSON)

$(JSON): dns_cache.p4
	mkdir -p build
	$(P4C) --target $(TARGET) --arch $(ARCH) -o build dns_cache.p4

run: $(JSON)
	sudo $(shell which python3) topology.py

stats:
	python3 scripts/stats.py

clean:
	-rm -rf build *.log /tmp/s1.log

.PHONY: all run stats clean
