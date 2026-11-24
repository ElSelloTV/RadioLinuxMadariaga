package ar.tuyu.grabadora;

/** Procesado de voz para radio FM + cortina con ducking. Java puro (sin Android), pensado para usar poca memoria. */
class Dsp {
    static final double OBJETIVO_LUFS = -16.0;
    static final double TECHO = Math.pow(10, -1.5 / 20);   // pico máximo -1.5 dBFS
    static final double SEG_ANTES = 12.0, SEG_DESPUES = 3.0; // segundos de cortina antes y después de la voz
    static final double NIVEL_CORTINA_LUFS = -19.0;           // cortina sola (audible)
    static final double DUCK_DB = -12.0;                      // atenuación de la cortina bajo la voz

    /** Biquad RBJ (forma directa I). */
    static class Bq {
        double b0, b1, b2, a1, a2, x1, x2, y1, y2;
        Bq(double b0, double b1, double b2, double a0, double a1, double a2) {
            this.b0 = b0 / a0; this.b1 = b1 / a0; this.b2 = b2 / a0; this.a1 = a1 / a0; this.a2 = a2 / a0;
        }
        double sample(double in) {
            double y = b0 * in + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2;
            x2 = x1; x1 = in; y2 = y1; y1 = y;
            return y;
        }
        void run(float[] x) { for (int i = 0; i < x.length; i++) x[i] = (float) sample(x[i]); }
        static Bq highpass(double f, double q, double sr) {
            double w = 2 * Math.PI * f / sr, c = Math.cos(w), al = Math.sin(w) / (2 * q);
            return new Bq((1 + c) / 2, -(1 + c), (1 + c) / 2, 1 + al, -2 * c, 1 - al);
        }
        static Bq peak(double f, double q, double gDb, double sr) {
            double A = Math.pow(10, gDb / 40), w = 2 * Math.PI * f / sr, c = Math.cos(w), al = Math.sin(w) / (2 * q);
            return new Bq(1 + al * A, -2 * c, 1 - al * A, 1 + al / A, -2 * c, 1 - al / A);
        }
        static Bq highShelf(double f, double gDb, double sr) {   // pendiente S=1
            double A = Math.pow(10, gDb / 40), w = 2 * Math.PI * f / sr, c = Math.cos(w), s = Math.sin(w);
            double al = s / 2 * Math.sqrt((A + 1 / A) * (1 / 1.0 - 1) + 2), t = 2 * Math.sqrt(A) * al;
            return new Bq(A * ((A + 1) + (A - 1) * c + t), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - t),
                    (A + 1) - (A - 1) * c + t, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - t);
        }
    }

    // ------------------------------------------------------------------ voz (EN EL LUGAR: modifica y devuelve x)
    static float[] process(float[] x, int sr) { return process(x, sr, true); }

    static float[] process(float[] x, int sr, boolean fm) {
        if (fm) {
            Bq[] eq = {
                Bq.highpass(85, 0.7071, sr), Bq.peak(140, 1.0, -2.0, sr), Bq.peak(280, 1.0, -3.5, sr),
                Bq.peak(500, 1.2, -2.0, sr), Bq.peak(2800, 1.0, 4.0, sr), Bq.peak(5000, 1.2, 3.0, sr),
                Bq.highShelf(9000, 2.5, sr)
            };
            for (Bq b : eq) b.run(x);
            compress(x, sr, -24, 3.5, 8, 120, 6);
        }
        double l = lufs(x, sr);
        if (!Double.isInfinite(l) && !Double.isNaN(l)) {
            double g = Math.min(24, Math.max(-12, OBJETIVO_LUFS - l));
            float k = (float) Math.pow(10, g / 20);
            for (int i = 0; i < x.length; i++) x[i] *= k;
        }
        limit(x);
        return x;
    }

    static void compress(float[] x, int sr, double thDb, double ratio, double attMs, double relMs, double kneeDb) {
        double aRms = Math.exp(-1.0 / (sr * 0.010));
        double aAtt = Math.exp(-1.0 / (sr * attMs / 1000)), aRel = Math.exp(-1.0 / (sr * relMs / 1000));
        double ms = 0, grDb = 0;
        for (int i = 0; i < x.length; i++) {
            ms = aRms * ms + (1 - aRms) * x[i] * x[i];
            double lv = 10 * Math.log10(ms + 1e-12), over = lv - thDb, target;
            if (over <= -kneeDb / 2) target = 0;
            else if (over >= kneeDb / 2) target = over * (1 - 1 / ratio);
            else { double d = over + kneeDb / 2; target = (1 - 1 / ratio) * d * d / (2 * kneeDb); }
            double a = target > grDb ? aAtt : aRel;
            grDb = a * grDb + (1 - a) * target;
            x[i] *= (float) Math.pow(10, -grDb / 20);
        }
    }

    // ------------------------------------------------------------------ sonoridad (sin copias del audio)
    /** Sonoridad integrada aproximada (ponderación K + compuertas, estilo BS.1770), por bloques de 100 ms. */
    static class Lufs {
        final Bq hp, sh; final int hop;
        double[] e = new double[256]; int ne = 0, cnt = 0; double acc = 0;
        Lufs(int sr) { hp = Bq.highpass(38, 0.5, sr); sh = Bq.highShelf(1500, 4.0, sr); hop = Math.max(1, sr / 10); }
        void add(double s) {
            double y = sh.sample(hp.sample(s));
            acc += y * y;
            if (++cnt == hop) {
                if (ne == e.length) e = java.util.Arrays.copyOf(e, ne * 2);
                e[ne++] = acc; acc = 0; cnt = 0;
            }
        }
        double result() {
            int nb = ne - 3;
            if (nb < 1) return Double.NEGATIVE_INFINITY;
            double[] p = new double[nb];
            for (int b = 0; b < nb; b++) p[b] = (e[b] + e[b + 1] + e[b + 2] + e[b + 3]) / (4.0 * hop);
            double s = 0; int n = 0;
            for (double v : p) if (-0.691 + 10 * Math.log10(v + 1e-20) > -70) { s += v; n++; }
            if (n == 0) return Double.NEGATIVE_INFINITY;
            double rel = -0.691 + 10 * Math.log10(s / n) - 10;
            s = 0; n = 0;
            for (double v : p) { double l = -0.691 + 10 * Math.log10(v + 1e-20); if (l > -70 && l > rel) { s += v; n++; } }
            return n == 0 ? Double.NEGATIVE_INFINITY : -0.691 + 10 * Math.log10(s / n);
        }
    }

    static double lufs(float[] x, int sr) {
        Lufs l = new Lufs(sr);
        for (float v : x) l.add(v);
        return l.result();
    }

    // ------------------------------------------------------------------ limitador con anticipación (en flujo)
    /** Ningún pico supera el techo. Retardo de L-1 cuadros: push() devuelve true cuando hay un cuadro de salida. */
    static class Limiter {
        final int L, ch, cap;
        final float[][] ring;           // últimos L cuadros de entrada
        final float[] gmin;             // últimos L valores de ganancia mínima
        final long[] dqIdx; final float[] dqVal; int h = 0, t = 0;   // cola circular monótona (mínimo móvil)
        long j = 0; double sum = 0;
        Limiter(int sr, int ch) {
            L = Math.max(2, (int) (0.005 * sr)); this.ch = ch; cap = L + 1;
            ring = new float[L][ch]; gmin = new float[L];
            dqIdx = new long[cap]; dqVal = new float[cap];
        }
        boolean push(float[] in, float[] out) {
            float a = 0;
            for (int c = 0; c < ch; c++) a = Math.max(a, Math.abs(in[c]));
            float g = a > TECHO ? (float) (TECHO / a) : 1f;
            System.arraycopy(in, 0, ring[(int) (j % L)], 0, ch);
            while (t != h && dqVal[(t - 1 + cap) % cap] >= g) t = (t - 1 + cap) % cap;
            dqIdx[t] = j; dqVal[t] = g; t = (t + 1) % cap;
            while (dqIdx[h] < j - L + 1) h = (h + 1) % cap;      // fuera de la ventana [j-L+1, j]
            boolean emit = false;
            if (j >= L - 1) {
                float m = dqVal[h];                               // gmin[p], p = j-L+1
                long p = j - L + 1;
                if (p == 0) { java.util.Arrays.fill(gmin, m); sum = (double) m * L; }
                else { int s = (int) (p % L); sum += m - gmin[s]; gmin[s] = m; }
                float k = (float) (sum / L);
                float[] src = ring[(int) (p % L)];
                for (int c = 0; c < ch; c++) out[c] = src[c] * k;
                emit = true;
            }
            j++;
            return emit;
        }
    }

    static void limit(float[] x) {
        Limiter lim = new Limiter(44100, 1);
        float[] in = new float[1], out = new float[1];
        int n = x.length, p = 0;
        for (int j = 0; j < n + lim.L - 1; j++) {
            in[0] = j < n ? x[j] : 0;
            if (lim.push(in, out) && p < n) x[p++] = out[0];
        }
    }

    // ------------------------------------------------------------------ cortina + ducking (en flujo)
    /** Primer instante con voz (se conserva 150 ms antes) para que la voz arranque justo en el segundo 12. */
    static int inicioVoz(float[] v, int sr) {
        int w = (int) (0.010 * sr);
        for (int i = 0; i + w <= v.length; i += w) {
            double s = 0; for (int j = i; j < i + w; j++) s += v[j] * v[j];
            if (10 * Math.log10(s / w + 1e-12) > -32) return Math.max(0, i - (int) (0.15 * sr));
        }
        return 0;
    }

    /**
     * Mezcla cortina (en bucle) + voz desde el segundo 12 + 3 s finales, con ducking inmediato.
     * Entrega el resultado por tramos (read) sin guardar el audio mezclado completo.
     */
    static class MixStream {
        final float[] voz; final int srV, srO, a, vs, vnOut, total, ch, cn, xf, P;
        final short[][] cor; final boolean[] dil;
        final float gc, duck; final double aAtt, aRel, stepV;
        final int blockO, fi, fo;
        final Limiter lim; final float[] fin, fout;
        double g = 1; int i = 0, emitted = 0, kSeg = 0, tSeg = 0;

        MixStream(float[] voz, int srV, short[][] cor, int srO) {
            this.voz = voz; this.srV = srV; this.srO = srO; this.cor = cor;
            ch = cor.length; cn = cor[0].length;
            a = inicioVoz(voz, srV);
            int vnV = voz.length - a;
            vs = (int) (SEG_ANTES * srO);
            vnOut = (int) ((long) vnV * srO / srV);
            total = vs + vnOut + (int) (SEG_DESPUES * srO);
            stepV = srV / (double) srO;
            blockO = srO / 100;

            // nivel de la cortina
            Lufs lf = new Lufs(srO);
            for (int k = 0; k < cn; k++) { double s = 0; for (short[] c : cor) s += c[k]; lf.add(s / ch / 32768.0); }
            double l = lf.result();
            double gcDb = Double.isInfinite(l) || Double.isNaN(l) ? 0 : Math.max(-30, Math.min(10, NIVEL_CORTINA_LUFS - l));
            gc = (float) Math.pow(10, gcDb / 20);

            // detector de voz por bloques de 10 ms (anticipación 40 ms, sostén 300 ms)
            int wv = Math.max(1, srV / 100), nb = vnV / wv;
            dil = new boolean[nb + 35];
            double thr = Math.pow(10, -3.2);
            for (int b = 0; b < nb; b++) {
                double s = 0; for (int k = a + b * wv; k < a + (b + 1) * wv; k++) s += (double) voz[k] * voz[k];
                if (s / wv > thr) for (int k = b; k <= b + 34 && k < dil.length; k++) dil[k] = true;
            }
            duck = (float) Math.pow(10, DUCK_DB / 20);
            aAtt = Math.exp(-1.0 / (srO * 0.015)); aRel = Math.exp(-1.0 / (srO * 0.45));
            fi = (int) (0.05 * srO); fo = (int) (2.5 * srO);
            xf = Math.min(srO, cn / 4); P = cn - xf;
            lim = new Limiter(srO, ch); fin = new float[ch]; fout = new float[ch];
        }

        int total() { return total; }

        private void frame() {
            double v = 0;
            if (i >= vs && i - vs < vnOut) {
                double p = a + (i - vs) * stepV; int k = (int) p; double f = p - k;
                float x0 = voz[Math.min(k, voz.length - 1)], x1 = voz[Math.min(k + 1, voz.length - 1)];
                v = x0 + (x1 - x0) * f;
            }
            int bk = Math.floorDiv(i - vs, blockO) + 4;
            double tgt = (bk >= 0 && bk < dil.length && dil[bk]) ? duck : 1, c = tgt < g ? aAtt : aRel;
            g = c * g + (1 - c) * tgt;
            double fade = 1;
            if (i < fi) fade = (double) i / fi;
            if (i >= total - fo) fade = 0.5 * (1 + Math.cos(Math.PI * (i - (total - fo)) / fo));
            float gain = (float) (g * fade) * gc;
            for (int ci = 0; ci < ch; ci++) {
                short[] cc = cor[ci]; float m;
                if (kSeg > 0 && tSeg < xf) {
                    double ww = (double) tSeg / xf;
                    m = (float) ((cc[tSeg] * Math.sin(ww * Math.PI / 2) + cc[P + tSeg] * Math.cos(ww * Math.PI / 2)) / 32768.0);
                } else m = cc[tSeg] / 32768f;
                fin[ci] = m * gain + (float) v;
            }
            if (++tSeg >= P) { tSeg = 0; kSeg++; }
        }

        /** Llena buf (intercalado, 16 bits) con hasta maxFrames cuadros; devuelve cuántos escribió (0 = terminó). */
        int read(short[] buf, int maxFrames) {
            int w = 0;
            while (w < maxFrames && emitted < total) {
                if (i < total) frame(); else java.util.Arrays.fill(fin, 0f);
                i++;
                if (lim.push(fin, fout)) {
                    for (int c = 0; c < ch; c++)
                        buf[w * ch + c] = (short) Math.round(Math.max(-1f, Math.min(1f, fout[c])) * 32767f);
                    w++; emitted++;
                }
            }
            return w;
        }
    }
}
