# Greia lightweight microphone endpoint — ALSA ExtPlug build
#
# Runtime dependency: libspeexdsp1 (Debian). Build dependencies (gcc,
# libc6-dev, libasound2-dev, libspeexdsp-dev) are development-only and must
# never enter the child runtime image.
#
# The install directory is ALSA's compiled plugin directory for the target
# multiarch triplet. It is taken from the compiler itself (`-print-multiarch`,
# always available with Debian gcc) rather than dpkg-architecture, which lives
# in dpkg-dev and is absent from a --no-install-recommends toolchain. There is
# deliberately no architecture fallback: an empty triplet installed the module
# into /usr/lib/alsa-lib, where alsa-lib never looks.

CC ?= gcc
CFLAGS ?= -O2 -Wall -Wextra -fPIC -DPIC
MULTIARCH ?= $(shell $(CC) -print-multiarch 2>/dev/null)
ALSA_LIBDIR = /usr/lib/$(MULTIARCH)/alsa-lib
MODULE = libasound_module_pcm_greia_mic_light.so

$(MODULE): greia_mic_light.c
	$(CC) $(CFLAGS) -shared -o $@ $< \
		$(shell pkg-config --cflags --libs alsa speexdsp 2>/dev/null || \
			echo "-lasound -lspeexdsp -lm")

install: $(MODULE)
	@test -n "$(MULTIARCH)" || { echo "cannot determine the target multiarch triplet" >&2; exit 1; }
	install -D -m 0755 $< $(DESTDIR)$(ALSA_LIBDIR)/$<

clean:
	rm -f $(MODULE)

.PHONY: install clean
