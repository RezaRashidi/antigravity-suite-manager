#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <math.h>

static inline double cubic(double x) {
    x = fabs(x);
    if (x < 1.0) return 0.5 * (2.0 + x * x * (-5.0 + x * 3.0));
    if (x < 2.0) return 0.5 * (x * (-1.0 + x * (5.0 - x * 2.0)) - 4.0 + 8.0 * x - 5.0 * x * x + x * x * x);
    return 0.0;
}

void bicubic_scale(const uint8_t *src, int sw, int sh, uint8_t *dst, int dw, int dh) {
    double scale_x = (double)sw / dw, scale_y = (double)sh / dh;
    for (int dy = 0; dy < dh; dy++) {
        double sy = (dy + 0.5) * scale_y - 0.5;
        int iy = (int)floor(sy);
        double fy = sy - iy;
        for (int dx = 0; dx < dw; dx++) {
            double sx = (dx + 0.5) * scale_x - 0.5;
            int ix = (int)floor(sx);
            double fx = sx - ix, c[4] = {0, 0, 0, 0}, total_w = 0.0;
            for (int m = -1; m <= 2; m++) {
                int py = (iy + m < 0) ? 0 : (iy + m >= sh ? sh - 1 : iy + m);
                double wy = cubic(m - fy);
                for (int n = -1; n <= 2; n++) {
                    int px = (ix + n < 0) ? 0 : (ix + n >= sw ? sw - 1 : ix + n);
                    double w = wy * cubic(n - fx);
                    int s_idx = (py * sw + px) * 4;
                    double a = src[s_idx + 3] / 255.0;
                    c[0] += src[s_idx] * a * w; c[1] += src[s_idx + 1] * a * w;
                    c[2] += src[s_idx + 2] * a * w; c[3] += src[s_idx + 3] * w;
                    total_w += w;
                }
            }
            int d_idx = (dy * dw + dx) * 4;
            double a = c[3] / total_w;
            if (a < 0.0) a = 0.0; else if (a > 255.0) a = 255.0;
            dst[d_idx + 3] = (uint8_t)(a + 0.5);
            if (a > 0.5) {
                double a_frac = a / 255.0;
                for (int ch = 0; ch < 3; ch++) {
                    double val = (c[ch] / total_w) / a_frac;
                    dst[d_idx + ch] = (uint8_t)((val < 0.0 ? 0.0 : (val > 255.0 ? 255.0 : val)) + 0.5);
                }
            } else {
                dst[d_idx] = dst[d_idx + 1] = dst[d_idx + 2] = 0;
            }
        }
    }
}

int main(int argc, char **argv) {
    if (argc < 7) return 1;
    int sw = atoi(argv[2]), sh = atoi(argv[3]), dw = atoi(argv[5]), dh = atoi(argv[6]);
    FILE *fin = fopen(argv[1], "rb");
    if (!fin) return 2;
    uint8_t *src = malloc(sw * sh * 4);
    if (fread(src, 1, sw * sh * 4, fin) != (size_t)(sw * sh * 4)) {
        fclose(fin); free(src); return 4;
    }
    fclose(fin);
    uint8_t *dst = malloc(dw * dh * 4);
    bicubic_scale(src, sw, sh, dst, dw, dh);
    FILE *fout = fopen(argv[4], "wb");
    if (!fout) { free(src); free(dst); return 3; }
    fwrite(dst, 1, dw * dh * 4, fout);
    fclose(fout); free(src); free(dst);
    return 0;
}
