# Greia system audio assets

This directory owns short platform-level sounds that are not Activity content.

## `greia-boot-chime.wav`

The boot chime is intentionally **not yet canonized as an arbitrary generated waveform**. The local hardware acceptance session may create or install a provisional candidate here, but it becomes the default Greia sound only after it is mechanically valid and has been listened to on representative low-end speakers.

Contract:

- PCM WAV is preferred for the first implementation because it avoids a runtime codec dependency;
- mono is sufficient;
- target duration roughly 0.5–1.0 s; hard test bound <=1.2 s;
- gentle attack/release; no startling transient;
- conservative peak level suitable for tiny netbook speakers;
- launcher starts it only after the first graphical frame has been presented;
- playback is nonblocking and fail-silent;
- missing/broken audio must never delay or fail boot;
- one shot per machine boot, not per launcher restart;
- respect device/platform mute and a future Parent-owned global boot-sound setting;
- no audio runtime or asset belongs in initramfs.

The exact sound is a product/creative decision. Source validity alone must not be used to claim that the chime is pleasant.