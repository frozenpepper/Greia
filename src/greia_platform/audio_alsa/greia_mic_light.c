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
 *     in Greia-owned ALSA composition, never exposed to Activities.
 *
 * DSP rate: the SpeexDSP preprocessor is specified for rates up to 32 kHz.
 * The transport contract is fixed at 48 kHz (pinned by the surrounding ALSA
 * composition), so the signal is band-limited and decimated to an in-spec
 * DSP rate (default 24 kHz) before denoising and interpolated back after.
 * Measured stationary-noise suppression at 48 kHz was far weaker than the
 * same preprocessor in its specified range.
 *
 * ALSA composition (see runtime/alsa/greia-activity-overrides.conf):
 *   plug (app-rate/format/channels conversion, pins 48 kHz mono S16)
 *     -> greia_denoise ExtPlug (FIR decimate -> SpeexDSP -> FIR interpolate)
 *     -> plughw capture slave
 *
 * Build: see Makefile in this directory.
 */
#include <alsa/asoundlib.h>
#include <math.h>
#include <stdbool.h>
#include <alsa/pcm_external.h>
#include <speex/speex_preprocess.h>

/* Transport contract: 48 kHz mono S16_LE (pinned by the surrounding plug). */
#define GREIA_MIC_TRANSPORT_RATE 48000

/* In-spec SpeexDSP processing rate and 20 ms frame. */
#define GREIA_MIC_DSP_RATE 24000
#define GREIA_MIC_FRAME_MS 20

#define GREIA_MIC_DEFAULT_SUPPRESS_DB -15

/* Anti-alias / reconstruction FIR (33-tap Hamming-windowed sinc, fc≈10.5 kHz
 * at 48 kHz). Separate history per path: decimator and interpolator stream
 * independent signals and must not share filter memory. */
#define GREIA_FIR_TAPS 33
static const float greia_fir[GREIA_FIR_TAPS] = {
	-0.00019918f, 0.00179035f, 0.00125798f, -0.00296759f, -0.00438242f,
	0.00395949f, 0.01100239f, -0.00199299f, -0.02141244f, -0.00711120f,
	0.03432167f, 0.02972645f, -0.04706681f, -0.08252113f, 0.05645538f,
	0.30945892f, 0.43936225f, 0.30945892f, 0.05645538f, -0.08252113f,
	-0.04706681f, 0.02972645f, 0.03432167f, -0.00711120f, -0.02141244f,
	-0.00199299f, 0.01100239f, 0.00395949f, -0.00438242f, -0.00296759f,
	0.00125798f, 0.00179035f, -0.00019918f
};

struct greia_mic {
	snd_pcm_extplug_t ext;
	SpeexPreprocessState *pre;
	int suppress_db;
	int dsp_rate;

	int factor;
	float dec_hist[GREIA_FIR_TAPS];
	int dec_phase;
	float int_hist[GREIA_FIR_TAPS];

	int16_t dsp_frame[GREIA_MIC_DSP_RATE * GREIA_MIC_FRAME_MS / 1000];
	size_t dsp_frame_fill;
	size_t frame_size;

	/* Output delay line: the pipeline (decimator -> denoise frame ->
	 * interpolator) introduces bounded latency, so processed samples are
	 * staged here and each transfer() pops exactly the requested count.
	 * The FIFO is primed at init so a transfer never underflows. */
	int16_t *out_fifo;
	size_t out_cap;
	size_t out_head;
	size_t out_count;
};

static bool greia_out_push(struct greia_mic *mic, int16_t sample)
{
	if (mic->out_count >= mic->out_cap)
		return false;
	mic->out_fifo[(mic->out_head + mic->out_count) % mic->out_cap] =
		sample;
	mic->out_count++;
	return true;
}

static int16_t greia_out_pop(struct greia_mic *mic)
{
	int16_t sample = mic->out_fifo[mic->out_head];

	mic->out_head = (mic->out_head + 1) % mic->out_cap;
	mic->out_count--;
	return sample;
}

static int16_t *area_sample(const snd_pcm_channel_area_t *areas,
			    snd_pcm_uframes_t offset)
{
	unsigned char *base = areas[0].addr;
	unsigned long step = areas[0].step;
	return (int16_t *)(base + ((offset * step) >> 3));
}

static float greia_fir_run(float *hist, float sample)
{
	float acc = 0.0f;

	hist[0] = sample;
	for (int k = 0; k < GREIA_FIR_TAPS; k++)
		acc += greia_fir[k] * hist[k];
	memmove(&hist[1], &hist[0], (GREIA_FIR_TAPS - 1) * sizeof(float));
	return acc;
}

/* Push one transport sample through the decimator; every `factor`-th
 * filtered sample becomes one DSP sample. Returns 1 when produced. */
static int greia_decimate(struct greia_mic *mic, int16_t in, int16_t *out)
{
	float filtered = greia_fir_run(mic->dec_hist, (float)in);

	mic->dec_phase++;
	if (mic->dec_phase >= mic->factor) {
		mic->dec_phase = 0;
		*out = (int16_t)lrintf(filtered);
		return 1;
	}
	return 0;
}

static void greia_emit_interpolated(struct greia_mic *mic, int16_t dsp_sample)
{
	/* Zero-stuff by `factor`, run the reconstruction FIR, compensate the
	 * 1/factor zero-stuffing gain. Emits factor transport samples into
	 * the delay-line FIFO. */
	for (int k = 0; k < mic->factor; k++) {
		float impulse = k == 0 ? (float) dsp_sample * (float) mic->factor
				       : 0.0f;
		float filtered = greia_fir_run(mic->int_hist, impulse);
		greia_out_push(mic, (int16_t) lrintf(filtered));
	}
}

/* Feed transport samples through the whole pipeline. Output samples land
 * in the delay-line FIFO, decoupled from input buffer positions, so the
 * pipeline latency never glitches the stream. */
static void greia_pipeline_feed(struct greia_mic *mic, const int16_t *samples,
				snd_pcm_uframes_t frames)
{
	for (snd_pcm_uframes_t i = 0; i < frames; i++) {
		int16_t dsp_sample;

		if (!greia_decimate(mic, samples[i], &dsp_sample))
			continue;
		mic->dsp_frame[mic->dsp_frame_fill++] = dsp_sample;
		if (mic->dsp_frame_fill < mic->frame_size)
			continue;

		speex_preprocess_run(mic->pre, mic->dsp_frame);
		mic->dsp_frame_fill = 0;
		for (size_t k = 0; k < mic->frame_size; k++)
			greia_emit_interpolated(mic, mic->dsp_frame[k]);
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

	greia_pipeline_feed(mic, src, size);
	for (snd_pcm_uframes_t i = 0; i < size; i++)
		dst[i] = mic->out_count > 0 ? greia_out_pop(mic) : 0;
	return (snd_pcm_sframes_t)size;
}

static void greia_release(struct greia_mic *mic)
{
	if (mic->pre) {
		speex_preprocess_state_destroy(mic->pre);
		mic->pre = NULL;
	}
	mic->dsp_frame_fill = 0;
	mic->out_head = 0;
	mic->out_count = 0;
	mic->dec_phase = 0;
	memset(mic->dec_hist, 0, sizeof(mic->dec_hist));
	memset(mic->int_hist, 0, sizeof(mic->int_hist));
	mic->frame_size = 0;
}

static int greia_init(snd_pcm_extplug_t *ext)
{
	struct greia_mic *mic = ext->private_data;

	if (ext->stream != SND_PCM_STREAM_CAPTURE)
		return -EINVAL;

	greia_release(mic);

	if (ext->rate != GREIA_MIC_TRANSPORT_RATE || ext->channels != 1)
		return -EINVAL;
	if (mic->dsp_rate <= 0 || mic->dsp_rate > 32000 ||
	    ext->rate % mic->dsp_rate != 0)
		return -EINVAL;

	mic->factor = ext->rate / mic->dsp_rate;
	mic->frame_size = (size_t)(mic->dsp_rate * GREIA_MIC_FRAME_MS / 1000);
	mic->pre = speex_preprocess_state_init((int)mic->frame_size,
					       mic->dsp_rate);
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

	/* Prime the delay line with silence: flushes the pipeline so every
	 * later transfer can pop its complete count of processed samples. */
	{
		int16_t silence[256] = { 0 };
		size_t prime = mic->frame_size * (size_t)mic->factor * 2 +
			       GREIA_FIR_TAPS + 256;
		while (prime > 0) {
			size_t chunk = prime < 256 ? prime : 256;
			greia_pipeline_feed(mic, silence, chunk);
			prime -= chunk;
		}
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
	free(mic->out_fifo);
	mic->out_fifo = NULL;
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

	mic = calloc(1, sizeof(*mic));
	if (!mic)
		return -ENOMEM;
	mic->suppress_db = GREIA_MIC_DEFAULT_SUPPRESS_DB;
	mic->dsp_rate = GREIA_MIC_DSP_RATE;

	snd_config_for_each(i, next, conf) {
		snd_config_t *n = snd_config_iterator_entry(i);
		const char *id;
		if (snd_config_get_id(n, &id) < 0)
			continue;
		if (strcmp(id, "comment") == 0 || strcmp(id, "type") == 0 ||
		    strcmp(id, "hint") == 0)
			continue;
		if (strcmp(id, "suppress_db") == 0) {
			long v;
			if (snd_config_get_integer(n, &v) < 0 || v > 0 ||
			    v < -60) {
				SNDERR("greia_denoise: invalid suppress_db");
				free(mic);
				return -EINVAL;
			}
			mic->suppress_db = (int)v;
			continue;
		}
		if (strcmp(id, "dsp_rate") == 0) {
			long v;
			if (snd_config_get_integer(n, &v) < 0) {
				SNDERR("greia_denoise: invalid dsp_rate");
				free(mic);
				return -EINVAL;
			}
			mic->dsp_rate = (int)v;
			continue;
		}
		if (strcmp(id, "slave") == 0) {
			slave = n;
			continue;
		}
		SNDERR("greia_denoise: unknown field %s", id);
		free(mic);
		return -EINVAL;
	}

	if (!slave) {
		SNDERR("greia_denoise: no slave defined");
		free(mic);
		return -EINVAL;
	}

	mic->out_cap = 16384;
	mic->out_fifo = calloc(mic->out_cap, sizeof(int16_t));
	if (!mic->out_fifo) {
		free(mic);
		return -ENOMEM;
	}

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
	 * convert whatever the application requested onto this contract and
	 * pin the transport rate to GREIA_MIC_TRANSPORT_RATE. */
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
