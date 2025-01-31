
TARGETS = tlsrpt-collectd.1 tlsrpt-fetcher.1 tlsrpt-reportd.1

.phony: all clean 

all: ${TARGETS}

%.1 : %.adoc manpage-*.adoc Makefile
	asciidoctor -b manpage $<

clean:
	rm ${TARGETS} 
