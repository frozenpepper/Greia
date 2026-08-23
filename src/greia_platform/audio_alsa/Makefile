# Greia lightweight microphone endpoint — ALSA ExtPlug build
#
# Runtime dependency: libspeexdsp1 (Debian). Build dependencies are
# development-only and must never enter the child runtime image.

CC ?= gcc
CFLAGS ?= -O2 -Wall -Wextra -fPIC -DPIC
ALSA_LIBDIR := /usr/lib/$(shell dpkg-architecture -qDEB_HOST_MULTIARCH 2>/dev/null || echo i386-linux-gnu)/alsa-lib

libasound_module_pcm_greia_mic_light.so: greia_mic_light.c
	$(CC) $(CFLAGS) -shared -o $@ $< \
		$(shell pkg-config --cflags --libs alsa speexdsp 2>/dev/null || \
			echo "-lasound -lspeexdsp")

install: libasound_module_pcm_greia_mic_light.so
	install -D -m 0755 $< $(DESTDIR)$(ALSA_LIBDIR)/$<

clean:
	rm -f libasound_module_pcm_greia_mic_light.so

.PHONY: install clean
