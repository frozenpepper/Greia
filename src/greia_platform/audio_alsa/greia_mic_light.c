/*
 * greia_mic_light.c — Greia platform-owned lightweight microphone cleanup.
 *
 * Architecture authority: docs/adr/0031-platform-owned-microphone-processing.md
 * Physical protocol: docs/testing/2026-08-23_ACER_MICROPHONE_PROCESSING_ACCEPTANCE.md
 *
 * Tiny ALSA external filter PCM (ExtPlug) applying SpeexDSP preprocessor
 * denoising to a fixed mono/S16_LE voice stream. It runs inside whichever
 * process opens the logical capture endpoint `greia_mic_light` (SDL/pygame
 * Activity, arecord probe, ...), so the cost is strictly on-demand: no
 * audio daemon exists and no CPU is spent when nothing is recording.
 *
 * Deliberate policy encoded here:
 *   - denoising enabled, conservative suppression (default -15 dB);
 *   - Speex AGC DISABLED because Greia owns the separate mic_gain control;
 *   - no dereverberation / echo cancellation in this tranche;
 *   - no physical card identity below this file — the capture slave is bound
 *     in Greia-owned /etc/asound.conf, never exposed to Activities.
 *
 * ALSA composition (see build/overlay/etc/asound.conf):
 *   plug (app-rate/format/channels conversion)
 *     -> greia_denoise ExtPlug (mono/S16 voice transform, any common rate)
 *     -> plughw capture slave
 *
 * Build: see Makefile in this directory.
 */
#include <alsa/asoundlib.h>
#include <alsa/pcm_external.h>
#include <speex/speex_preprocess.h>

/* Voice frame target: 20 ms at the negotiated stream rate. */
#define GREIA_MIC_FRAME_MS 20

#define GREIA_MIC_DEFAULT_SUPPRESS_DB -15

struct greia_mic {
	snd_pcm_extplug_t ext;
	SpeexPreprocessState *pre;
	int16_t accum[GREIA_MIC_FRAME_MS * 96000 / 1000]; /* max 96 kHz frame */
	size_t accum_fill;
	size_t frame_size;
	int suppress_db;
};

static int16_t *area_sample(const snd_pcm_channel_area_t *areas,
			    snd_pcm_uframes_t offset)
{
	unsigned char *base = areas[0].addr;
	unsigned long step = areas[0].step;
	return (int16_t *)(base + ((offset * step) >> 3));
}

static void greia_process(struct greia_mic *mic, int16_t *samples,
			  snd_pcm_uframes_t frames)
{
	snd_pcm_uframes_t i = 0;

	if (!mic->pre || mic->frame_size == 0)
		return;

	while (i < frames) {
		size_t space = mic->frame_size - mic->accum_fill;
		size_t take = (size_t)(frames - i) < space ?
				      (size_t)(frames - i) :
				      space;

		memcpy(&mic->accum[mic->accum_fill], &samples[i],
		       take * sizeof(int16_t));
		mic->accum_fill += take;

		if (mic->accum_fill == mic->frame_size) {
			speex_preprocess_run(mic->pre, mic->accum);
		}
		memcpy(&samples[i], &mic->accum[mic->accum_fill - take],
		       take * sizeof(int16_t));
		i += take;
		if (mic->accum_fill == mic->frame_size)
			mic->accum_fill = 0;
	}
}

static snd_pcm_sframes_t greia_transfer(snd_pcm_extplug_t *ext,
					const snd_pcm_channel_area_t *dst_areas,
					snd_pcm_uframes_t dst_offset,
					const snd_pcm_channel_area_t *src_areas,
					snd_pcm_uframes_t src_offset,
					snd_pcm_uframes_t size)
{
	struct greia_mic *mic = ext->private_data;
	int16_t *dst = area_sample(dst_areas, dst_offset);
	const int16_t *src = area_sample(src_areas, src_offset);

	if (size > 0)
		memcpy(dst, src, size * sizeof(int16_t));
	greia_process(mic, dst, size);
	return (snd_pcm_sframes_t)size;
}

static void greia_release(struct greia_mic *mic)
{
	if (mic->pre) {
		speex_preprocess_state_destroy(mic->pre);
		mic->pre = NULL;
	}
	mic->accum_fill = 0;
	mic->frame_size = 0;
}

static int greia_init(snd_pcm_extplug_t *ext)
{
	struct greia_mic *mic = ext->private_data;

	if (ext->stream != SND_PCM_STREAM_CAPTURE)
		return -EINVAL;

	greia_release(mic);

	if (ext->rate < 4000 || ext->rate > 96000 ||
	    ext->channels < 1 || (unsigned int)sizeof(mic->accum) /
					 sizeof(mic->accum[0]) <
			(size_t)(GREIA_MIC_FRAME_MS * ext->rate / 1000))
		return -EINVAL;

	mic->frame_size = GREIA_MIC_FRAME_MS * ext->rate / 1000;
	mic->accum_fill = 0;
	mic->pre = speex_preprocess_state_init((int)mic->frame_size, ext->rate);
	if (!mic->pre)
		return -ENOMEM;

	{
		int denoise = 1;
		int agc = 0;
		int suppress = mic->suppress_db;
		speex_preprocess_ctl(mic->pre, SPEEX_PREPROCESS_SET_DENOISE,
				     &denoise);
		speex_preprocess_ctl(mic->pre, SPEEX_PREPROCESS_SET_AGC, &agc);
		speex_preprocess_ctl(mic->pre,
				     SPEEX_PREPROCESS_SET_NOISE_SUPPRESS,
				     &suppress);
	}
	return 0;
}

static int greia_hw_free(snd_pcm_extplug_t *ext)
{
	struct greia_mic *mic = ext->private_data;

	greia_release(mic);
	return 0;
}

static int greia_close(snd_pcm_extplug_t *ext)
{
	struct greia_mic *mic = ext->private_data;

	greia_release(mic);
	free(mic);
	return 0;
}

static const snd_pcm_extplug_callback_t greia_callback = {
	.close = greia_close,
	.init = greia_init,
	.hw_free = greia_hw_free,
	.transfer = greia_transfer,
};

SND_PCM_PLUGIN_DEFINE_FUNC(greia_denoise)
{
	snd_config_iterator_t i, next;
	snd_config_t *slave = NULL;
	struct greia_mic *mic;
	int err;
	static const unsigned int fmt_list[] = { SND_PCM_FORMAT_S16_LE };
	static const unsigned int ch_list[] = { 1 };

	snd_config_for_each(i, next, conf) {
		snd_config_t *n = snd_config_iterator_entry(i);
		const char *id;
		if (snd_config_get_id(n, &id) < 0)
			continue;
		if (strcmp(id, "comment") == 0 || strcmp(id, "type") == 0 ||
		    strcmp(id, "hint") == 0)
			continue;
		if (strcmp(id, "slave") == 0) {
			slave = n;
			continue;
		}
		SNDERR("greia_denoise: unknown field %s", id);
		return -EINVAL;
	}

	if (!slave) {
		SNDERR("greia_denoise: no slave defined");
		return -EINVAL;
	}

	mic = calloc(1, sizeof(*mic));
	if (!mic)
		return -ENOMEM;
	mic->suppress_db = GREIA_MIC_DEFAULT_SUPPRESS_DB;

	mic->ext.version = SND_PCM_EXTPLUG_VERSION;
	mic->ext.name = "Greia microphone light cleanup";
	mic->ext.callback = &greia_callback;
	mic->ext.private_data = mic;

	err = snd_pcm_extplug_create(&mic->ext, name, root, slave, stream,
				     mode);
	if (err < 0) {
		free(mic);
		return err;
	}

	/* Fixed voice contract on both sides; the surrounding plug layers
	 * convert whatever the application requested onto this contract.
	 * Rate is intentionally unconstrained here: ExtPlug cannot convert
	 * rate, so client and slave share the application-negotiated rate
	 * and the preprocessor adapts its frame size to it. */
	snd_pcm_extplug_set_param_list(&mic->ext, SND_PCM_EXTPLUG_HW_FORMAT,
				       1, fmt_list);
	snd_pcm_extplug_set_param_list(&mic->ext, SND_PCM_EXTPLUG_HW_CHANNELS,
				       1, ch_list);
	snd_pcm_extplug_set_slave_param_list(&mic->ext,
					     SND_PCM_EXTPLUG_HW_FORMAT, 1,
					     fmt_list);
	snd_pcm_extplug_set_slave_param_list(&mic->ext,
					     SND_PCM_EXTPLUG_HW_CHANNELS, 1,
					     ch_list);

	*pcmp = mic->ext.pcm;
	return 0;
}

SND_PCM_PLUGIN_SYMBOL(greia_denoise);
