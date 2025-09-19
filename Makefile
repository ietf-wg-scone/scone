LIBDIR := lib
include $(LIBDIR)/main.mk

$(LIBDIR)/main.mk:
ifneq (,$(shell grep "path *= *$(LIBDIR)" .gitmodules 2>/dev/null))
	git submodule sync
	git submodule update --init
else
ifneq (,$(wildcard $(ID_TEMPLATE_HOME)))
	ln -s "$(ID_TEMPLATE_HOME)" $(LIBDIR)
else
	git clone -q --depth 10 -b main \
	    https://github.com/martinthomson/i-d-template $(LIBDIR)
endif
endif

.INTERMEDIATE: ta.py.excerpt
ta.py.excerpt: ta.py
	sed -e '1,/^#>>>/d;/^#<<</,$$d' $< > $@

draft-ietf-scone-protocol.xml: ta.py.excerpt

clean::
	-rm -rf ta.py.excerpt
