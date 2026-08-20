#define _POSIX_C_SOURCE 200809L
#include <fcntl.h>
#include <linux/fb.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

/*
 * Greia's earliest Linux-owned visual cover.
 *
 * Design constraints:
 * - no stdout/stderr output in the normal path;
 * - no sleeps, retries, PNG/JPEG decoding, SDL, Python or subprocesses;
 * - discover framebuffer geometry/pixel layout at runtime;
 * - fail quickly when fbdev is unavailable so boot is never delayed;
 * - consume a deliberately trivial P6 PPM generated from the canonical boot
 *   artwork at build time;
 * - optionally render an honest milestone progress bar. The percentage is
 *   supplied by boot-stage owners; this renderer never invents time-based
 *   progress and never treats service retries as forward progress.
 *
 * Exit codes:
 *   0  frame rendered
 *   2  framebuffer unavailable/unsupported (fail-soft)
 *   3  boot image invalid/unreadable
 *   64 invalid command line
 */

struct ppm_image {
    uint32_t width;
    uint32_t height;
    uint8_t *rgb;
};

static int next_token(const uint8_t *data, size_t size, size_t *offset,
                      char *token, size_t capacity) {
    size_t used = 0;
    if (capacity < 2) return -1;
    for (;;) {
        while (*offset < size && data[*offset] <= ' ') (*offset)++;
        if (*offset >= size) return -1;
        if (data[*offset] != '#') break;
        while (*offset < size && data[*offset] != '\n') (*offset)++;
    }
    while (*offset < size && data[*offset] > ' ') {
        if (used + 1 >= capacity) return -1;
        token[used++] = (char)data[(*offset)++];
    }
    token[used] = '\0';
    return 0;
}

static unsigned long parse_uint(const char *text, int *ok) {
    unsigned long value = 0;
    if (!*text) {
        *ok = 0;
        return 0;
    }
    for (; *text; ++text) {
        if (*text < '0' || *text > '9') {
            *ok = 0;
            return 0;
        }
        if (value > 100000000UL) {
            *ok = 0;
            return 0;
        }
        value = value * 10UL + (unsigned long)(*text - '0');
    }
    *ok = 1;
    return value;
}

static int load_ppm(const char *path, struct ppm_image *image) {
    int fd = -1;
    struct stat st;
    uint8_t *file_data = NULL;
    size_t file_size, offset = 0, pixel_bytes;
    char token[32];
    unsigned long width, height, maxval;
    int ok = 0;

    fd = open(path, O_RDONLY);
    if (fd < 0 || fstat(fd, &st) != 0 || st.st_size <= 0 ||
        st.st_size > 64 * 1024 * 1024) {
        goto bad;
    }
    file_size = (size_t)st.st_size;
    file_data = malloc(file_size);
    if (!file_data) goto bad;

    size_t done = 0;
    while (done < file_size) {
        ssize_t got = read(fd, file_data + done, file_size - done);
        if (got <= 0) goto bad;
        done += (size_t)got;
    }
    close(fd);
    fd = -1;

    if (next_token(file_data, file_size, &offset, token, sizeof token) ||
        strcmp(token, "P6") != 0) {
        goto bad;
    }
    if (next_token(file_data, file_size, &offset, token, sizeof token)) goto bad;
    width = parse_uint(token, &ok);
    if (!ok) goto bad;
    if (next_token(file_data, file_size, &offset, token, sizeof token)) goto bad;
    height = parse_uint(token, &ok);
    if (!ok) goto bad;
    if (next_token(file_data, file_size, &offset, token, sizeof token)) goto bad;
    maxval = parse_uint(token, &ok);
    if (!ok) goto bad;

    if (!width || !height || width > 4096 || height > 4096 || maxval != 255) {
        goto bad;
    }
    /* Greia's generator writes the canonical P6 header as `...255\n`.
     * Consume exactly that one structural separator. Do NOT skip arbitrary
     * bytes <= ASCII space here: P6 raster data is binary, so perfectly valid
     * dark RGB channels can have values such as 13 or 30. */
    if (offset >= file_size || file_data[offset] != '\n') goto bad;
    offset++;
    if (width > SIZE_MAX / height / 3u) goto bad;
    pixel_bytes = (size_t)width * (size_t)height * 3u;
    if (offset > file_size || file_size - offset != pixel_bytes) goto bad;

    image->rgb = malloc(pixel_bytes);
    if (!image->rgb) goto bad;
    memcpy(image->rgb, file_data + offset, pixel_bytes);
    image->width = (uint32_t)width;
    image->height = (uint32_t)height;
    free(file_data);
    return 0;

bad:
    if (fd >= 0) close(fd);
    free(file_data);
    return -1;
}

static uint32_t scale_channel(uint8_t value, uint32_t bits) {
    if (bits == 0) return 0;
    if (bits >= 8) return ((uint32_t)value) << (bits - 8);
    return ((uint32_t)value) >> (8 - bits);
}

static uint32_t pack_pixel(const struct fb_var_screeninfo *v,
                           uint8_t r, uint8_t g, uint8_t b) {
    uint32_t pixel = 0;
    pixel |= scale_channel(r, v->red.length) << v->red.offset;
    pixel |= scale_channel(g, v->green.length) << v->green.offset;
    pixel |= scale_channel(b, v->blue.length) << v->blue.offset;
    if (v->transp.length && v->transp.length < 32) {
        uint32_t alpha = (1u << v->transp.length) - 1u;
        pixel |= alpha << v->transp.offset;
    }
    return pixel;
}

static void write_pixel(uint8_t *dst, unsigned bytes_per_pixel, uint32_t pixel) {
    for (unsigned i = 0; i < bytes_per_pixel; ++i) {
        dst[i] = (uint8_t)(pixel >> (8u * i));
    }
}

static void fill_rect(uint8_t *memory,
                      const struct fb_fix_screeninfo *fix,
                      const struct fb_var_screeninfo *var,
                      unsigned bytes_per_pixel,
                      uint32_t x,
                      uint32_t y,
                      uint32_t width,
                      uint32_t height,
                      uint32_t pixel) {
    if (x >= var->xres || y >= var->yres) return;
    if (width > var->xres - x) width = var->xres - x;
    if (height > var->yres - y) height = var->yres - y;
    for (uint32_t dy = 0; dy < height; ++dy) {
        uint8_t *row = memory +
            (size_t)(y + dy + var->yoffset) * fix->line_length +
            (size_t)(x + var->xoffset) * bytes_per_pixel;
        for (uint32_t dx = 0; dx < width; ++dx) {
            write_pixel(row + (size_t)dx * bytes_per_pixel,
                        bytes_per_pixel, pixel);
        }
    }
}

static void draw_progress_bar(uint8_t *memory,
                              const struct fb_fix_screeninfo *fix,
                              const struct fb_var_screeninfo *var,
                              unsigned bytes_per_pixel,
                              unsigned progress) {
    uint32_t visible_w = var->xres;
    uint32_t visible_h = var->yres;
    uint32_t bar_w = (uint32_t)(((uint64_t)visible_w * 52u) / 100u);
    uint32_t bar_h = visible_h / 48u;
    uint32_t border;
    uint32_t x;
    uint32_t y;
    uint32_t inner_w;
    uint32_t inner_h;
    uint32_t filled_w;
    uint32_t border_px;
    uint32_t track_px;
    uint32_t fill_px;

    if (bar_w < 120u) bar_w = visible_w > 24u ? visible_w - 24u : visible_w;
    if (bar_h < 8u) bar_h = 8u;
    if (bar_h > 18u) bar_h = 18u;
    if (bar_w > visible_w) bar_w = visible_w;
    if (bar_h > visible_h) bar_h = visible_h;
    border = bar_h >= 12u ? 2u : 1u;
    if (bar_w <= 2u * border || bar_h <= 2u * border) return;

    x = (visible_w - bar_w) / 2u;
    y = (uint32_t)(((uint64_t)visible_h * 88u) / 100u);
    if (y + bar_h > visible_h) y = visible_h - bar_h;
    inner_w = bar_w - 2u * border;
    inner_h = bar_h - 2u * border;
    filled_w = (uint32_t)(((uint64_t)inner_w * progress + 50u) / 100u);
    if (filled_w > inner_w) filled_w = inner_w;

    /* Shared Greia UI colours chosen for strong contrast on dark and light
     * artwork and retained visibility after RGB565 quantization. */
    border_px = pack_pixel(var, 87, 66, 45);
    track_px = pack_pixel(var, 255, 247, 226);
    fill_px = pack_pixel(var, 255, 194, 52);

    fill_rect(memory, fix, var, bytes_per_pixel,
              x, y, bar_w, bar_h, border_px);
    fill_rect(memory, fix, var, bytes_per_pixel,
              x + border, y + border, inner_w, inner_h, track_px);
    if (filled_w) {
        fill_rect(memory, fix, var, bytes_per_pixel,
                  x + border, y + border, filled_w, inner_h, fill_px);
    }
}

static int draw(const char *device, const struct ppm_image *image, int progress) {
    int fd = open(device, O_RDWR);
    struct fb_fix_screeninfo fix;
    struct fb_var_screeninfo var;
    uint8_t *memory;
    size_t map_len;
    unsigned bytes_per_pixel;
    uint32_t visible_w, visible_h, dest_w, dest_h, x0, y0, background;

    if (fd < 0) return 2;
    if (ioctl(fd, FBIOGET_FSCREENINFO, &fix) != 0 ||
        ioctl(fd, FBIOGET_VSCREENINFO, &var) != 0) {
        close(fd);
        return 2;
    }
    if (var.bits_per_pixel != 16 && var.bits_per_pixel != 24 &&
        var.bits_per_pixel != 32) {
        close(fd);
        return 2;
    }
    /* fbdev can describe reversed bitfields. The compact renderer deliberately
     * supports the overwhelmingly common LSB-oriented layouts and fails soft on
     * an exotic layout rather than painting silently corrupted colours. */
    if (var.red.msb_right || var.green.msb_right || var.blue.msb_right) {
        close(fd);
        return 2;
    }

    bytes_per_pixel = var.bits_per_pixel / 8u;
    visible_w = var.xres;
    visible_h = var.yres;
    if (!visible_w || !visible_h || !image->width || !image->height || !image->rgb ||
        fix.line_length < visible_w * bytes_per_pixel) {
        close(fd);
        return 2;
    }

    map_len = fix.smem_len;
    if (map_len < (size_t)fix.line_length *
                      (size_t)(var.yoffset + visible_h)) {
        close(fd);
        return 2;
    }
    memory = mmap(NULL, map_len, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (memory == MAP_FAILED) {
        close(fd);
        return 2;
    }

    /* The generated landscape canvas extends the source artwork's own corner
     * colour into its safe margins. Use that same colour for any letterbox
     * pixels introduced by a display with a different aspect ratio, so there is
     * no white flash or visible rectangle around the composition. */
    background = pack_pixel(&var, image->rgb[0], image->rgb[1], image->rgb[2]);
    for (uint32_t y = 0; y < visible_h; ++y) {
        uint8_t *row = memory +
            (size_t)(y + var.yoffset) * fix.line_length +
            (size_t)var.xoffset * bytes_per_pixel;
        for (uint32_t x = 0; x < visible_w; ++x) {
            write_pixel(row + (size_t)x * bytes_per_pixel,
                        bytes_per_pixel, background);
        }
    }

    /* Proportional `padding` fit. The artwork generator, not this renderer,
     * owns visual scale and safe margins inside the landscape composition.
     * That keeps this runtime adapter resolution-independent and prevents the
     * old failure where the 222x600 portrait source consumed nearly the entire
     * physical display height. */
    dest_w = visible_w;
    dest_h = (uint32_t)(((uint64_t)image->height * visible_w +
                         image->width / 2u) / image->width);
    if (dest_h > visible_h) {
        dest_h = visible_h;
        dest_w = (uint32_t)(((uint64_t)image->width * visible_h +
                             image->height / 2u) / image->height);
    }
    if (!dest_w) dest_w = 1;
    if (!dest_h) dest_h = 1;
    if (dest_w > visible_w) dest_w = visible_w;
    if (dest_h > visible_h) dest_h = visible_h;
    x0 = (visible_w - dest_w) / 2u;
    y0 = (visible_h - dest_h) / 2u;

    for (uint32_t dy = 0; dy < dest_h; ++dy) {
        uint32_t sy = (uint32_t)(((uint64_t)dy * image->height) / dest_h);
        uint8_t *row = memory +
            (size_t)(dy + y0 + var.yoffset) * fix.line_length +
            (size_t)(x0 + var.xoffset) * bytes_per_pixel;
        for (uint32_t dx = 0; dx < dest_w; ++dx) {
            uint32_t sx = (uint32_t)(((uint64_t)dx * image->width) / dest_w);
            const uint8_t *rgb = image->rgb +
                ((size_t)sy * image->width + sx) * 3u;
            write_pixel(row + (size_t)dx * bytes_per_pixel,
                        bytes_per_pixel,
                        pack_pixel(&var, rgb[0], rgb[1], rgb[2]));
        }
    }

    if (progress >= 0) {
        draw_progress_bar(memory, &fix, &var, bytes_per_pixel, (unsigned)progress);
    }

    munmap(memory, map_len);
    close(fd);
    return 0;
}

int main(int argc, char **argv) {
    const char *device = "/dev/fb0";
    const char *image_path = "/etc/greia-boot/boot-logo.ppm";
    struct ppm_image image = {0};
    int progress = -1;
    int result;

    for (int i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "--device") == 0 && i + 1 < argc) {
            device = argv[++i];
        } else if (strcmp(argv[i], "--image") == 0 && i + 1 < argc) {
            image_path = argv[++i];
        } else if (strcmp(argv[i], "--progress") == 0 && i + 1 < argc) {
            int ok = 0;
            unsigned long value = parse_uint(argv[++i], &ok);
            if (!ok || value > 100u) return 64;
            progress = (int)value;
        } else {
            return 64;
        }
    }

    if (load_ppm(image_path, &image) != 0) return 3;
    result = draw(device, &image, progress);
    free(image.rgb);
    return result;
}
