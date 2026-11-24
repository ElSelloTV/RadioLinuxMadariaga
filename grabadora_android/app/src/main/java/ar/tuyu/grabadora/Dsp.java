package ar.tuyu.grabadora;

/** Procesado de voz para radio FM: filtros, compresor, nivelado a -16 LUFS y limitador. Java puro (sin Android). */
class Dsp {
    static final double OBJETIVO_LUFS = -16.0;
    static final double TECHO = Math.pow(10, -1.5 / 20);   // pico máximo -1.5 dBFS

    /** Biquad RBJ (forma directa I). */
    static class Bq {
        double b0, b1, b2, a1, a2, x1, x2, y1, y2;
        Bq(double b0, double b1, double b2, double a0, double a1, double a2) {
            this.b0 = b0 / a0; this.b1 = b1 / a0; this.b2 = b2 / a0; this.a1 = a1 / a0; this.a2 = a2 / a0;
        }
        void run(float[] x) {
            for (int i = 0; i < x.length; i++) {
                double in = x[i];
                double y = b0 * in + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2;
                x2 = x1; x1 = in; y2 = y1; y1 = y;
                x[i] = (float) y;
            }
        }
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

    static float[] process(float[] in, int sr) { return process(in, sr, true); }

    static float[] process(float[] in, int sr, boolean fm) {
        float[] x = in.clone();
        // 1) filtros
        Bq[] eq = fm ? new Bq[]{
            Bq.highpass(85, 0.7071, sr),
            Bq.peak(140, 1.0, -2.0, sr),
            Bq.peak(280, 1.0, -3.5, sr),
            Bq.peak(500, 1.2, -2.0, sr),
            Bq.peak(2800, 1.0, 4.0, sr),
            Bq.peak(5000, 1.2, 3.0, sr),
            Bq.highShelf(9000, 2.5, sr)
        } : new Bq[0];
        for (Bq b : eq) b.run(x);
        // 2) compresor
        if (fm) compress(x, sr, -24, 3.5, 8, 120, 6);
        // 3) nivelado a -16 LUFS
        double l = lufs(x, sr);
        if (!Double.isInfinite(l) && !Double.isNaN(l)) {
            double g = Math.min(24, Math.max(-12, OBJETIVO_LUFS - l));
            float k = (float) Math.pow(10, g / 20);
            for (int i = 0; i < x.length; i++) x[i] *= k;
        }
        // 4) limitador de picos
        limit(x, sr);
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

    /** Sonoridad integrada aproximada (ponderación K + compuertas, estilo BS.1770). */
    static double lufs(float[] x, int sr) {
        float[] k = x.clone();
        Bq.highpass(38, 0.5, sr).run(k);
        Bq.highShelf(1500, 4.0, sr).run(k);
        int blk = (int) (0.4 * sr), hop = blk / 4;
        if (k.length < blk) return Double.NEGATIVE_INFINITY;
        int nb = (k.length - blk) / hop + 1;
        double[] p = new double[nb];
        double[] cum = new double[k.length + 1];
        for (int i = 0; i < k.length; i++) cum[i + 1] = cum[i] + (double) k[i] * k[i];
        for (int b = 0; b < nb; b++) p[b] = (cum[b * hop + blk] - cum[b * hop]) / blk;
        double s = 0; int n = 0;
        for (double v : p) if (-0.691 + 10 * Math.log10(v + 1e-20) > -70) { s += v; n++; }
        if (n == 0) return Double.NEGATIVE_INFINITY;
        double rel = -0.691 + 10 * Math.log10(s / n) - 10;
        s = 0; n = 0;
        for (double v : p) { double l = -0.691 + 10 * Math.log10(v + 1e-20); if (l > -70 && l > rel) { s += v; n++; } }
        return n == 0 ? Double.NEGATIVE_INFINITY : -0.691 + 10 * Math.log10(s / n);
    }

    /** Limitador con anticipación: garantiza que ninguna muestra supere el techo. */
    static void limit(float[] x, int sr) { limitMulti(new float[][]{x}, sr); }

    /** El mismo recorte de ganancia se aplica a todos los canales (no mueve la imagen estéreo). */
    static void limitMulti(float[][] ch, int sr) {
        int n = ch[0].length, L = Math.max(2, (int) (0.005 * sr));
        float[] g = new float[n];
        for (int i = 0; i < n; i++) {
            float a = 0;
            for (float[] c : ch) a = Math.max(a, Math.abs(c[i]));
            g[i] = a > TECHO ? (float) (TECHO / a) : 1f;
        }
        float[] gmin = new float[n];
        int[] dq = new int[n]; int h = 0, t = 0;
        for (int i = n - 1; i >= 0; i--) {                 // mínimo de g[i .. i+L-1]
            while (t > h && g[dq[t - 1]] >= g[i]) t--;
            dq[t++] = i;
            while (dq[h] > i + L - 1) h++;
            gmin[i] = g[dq[h]];
        }
        double sum = 0;
        for (int i = 0; i < n; i++) {                      // promedio de gmin[i-L+1 .. i]
            sum += gmin[i];
            if (i >= L) sum -= gmin[i - L];
            int cnt = Math.min(i + 1, L);
            double pad = (L - cnt) * (double) gmin[0];       // antes del inicio: se repite el primer valor
            float k = (float) ((sum + pad) / L);
            for (float[] c : ch) c[i] *= k;
        }
    }

    // ------------------------------------------------------------------ cortina + ducking
    static final double SEG_ANTES = 12.0, SEG_DESPUES = 3.0;     // segundos de cortina antes y después de la voz
    static final double NIVEL_CORTINA_LUFS = -19.0;               // cortina sola (audible)
    static final double DUCK_DB = -12.0;                          // atenuación de la cortina bajo la voz

    static float[] resample(float[] x, int from, int to) {
        if (from == to) return x;
        int n = (int) ((long) x.length * to / from);
        float[] y = new float[n];
        double r = (double) from / to;
        for (int i = 0; i < n; i++) {
            double p = i * r; int k = (int) p; double f = p - k;
            float a = x[Math.min(k, x.length - 1)], b = x[Math.min(k + 1, x.length - 1)];
            y[i] = (float) (a + (b - a) * f);
        }
        return y;
    }

    /** Primer instante con voz (se conserva 150 ms antes) para que la voz arranque justo en el segundo 12. */
    static int inicioVoz(float[] v, int sr) {
        int w = (int) (0.010 * sr);
        for (int i = 0; i + w <= v.length; i += w) {
            double s = 0; for (int j = i; j < i + w; j++) s += v[j] * v[j];
            if (10 * Math.log10(s / w + 1e-12) > -40) return Math.max(0, i - (int) (0.15 * sr));
        }
        return 0;
    }

    /** Mezcla: cortina (en bucle) + voz desde el segundo 12 + 3 s finales, con ducking inmediato. Devuelve [canal][muestra]. */
    static float[][] mezclarConCortina(float[] voz, int sr, float[][] cor) {
        int ch = cor.length, cn = cor[0].length;
        int a = inicioVoz(voz, sr);
        int vs = (int) (SEG_ANTES * sr), vn = voz.length - a, total = vs + vn + (int) (SEG_DESPUES * sr);
        float[] v = new float[total];
        System.arraycopy(voz, a, v, vs, vn);

        float[] mono = new float[cn];
        for (int i = 0; i < cn; i++) { float s = 0; for (float[] c : cor) s += c[i]; mono[i] = s / ch; }
        double l = lufs(mono, sr);
        double gcDb = Double.isInfinite(l) || Double.isNaN(l) ? 0 : Math.max(-30, Math.min(10, NIVEL_CORTINA_LUFS - l));
        float gc = (float) Math.pow(10, gcDb / 20);

        // detector de voz (bloques de 10 ms) con anticipación de 40 ms y sostén de 300 ms
        int w = (int) (0.010 * sr), la = (int) (0.040 * sr), hold = (int) (0.300 * sr);
        boolean[] act = new boolean[total];
        int marcado = 0;
        for (int b = 0; (b + 1) * w <= total; b++) {
            double s = 0; for (int j = b * w; j < (b + 1) * w; j++) s += v[j] * v[j];
            if (10 * Math.log10(s / w + 1e-12) > -32) {
                int lo = Math.max(marcado, Math.max(0, b * w - la)), hi = Math.min(total, (b + 1) * w + hold);
                for (int i = lo; i < hi; i++) act[i] = true;
                marcado = Math.max(marcado, hi);
            }
        }
        float duck = (float) Math.pow(10, DUCK_DB / 20);
        double aAtt = Math.exp(-1.0 / (sr * 0.015)), aRel = Math.exp(-1.0 / (sr * 0.45));
        float[] gain = new float[total];
        double g = 1;
        int fo = (int) (2.5 * sr), fi = (int) (0.05 * sr);
        for (int i = 0; i < total; i++) {
            double tgt = act[i] ? duck : 1, c = tgt < g ? aAtt : aRel;
            g = c * g + (1 - c) * tgt;
            double f = 1;
            if (i < fi) f = (double) i / fi;
            if (i >= total - fo) f = 0.5 * (1 + Math.cos(Math.PI * (i - (total - fo)) / fo));
            gain[i] = (float) (g * f) * gc;
        }

        // cortina en bucle con empalme suave (1 s) cuando la grabación es más larga que la cortina
        int xf = Math.min(sr, cn / 4), P = cn - xf;
        float[][] out = new float[ch][total];
        for (int c = 0; c < ch; c++) {
            float[] cc = cor[c], o = out[c];
            for (int i = 0; i < total; i++) {
                int k = i / P, t = i - k * P;
                float m;
                if (k > 0 && t < xf) {
                    double ww = (double) t / xf;
                    m = (float) (cc[t] * Math.sin(ww * Math.PI / 2) + cc[P + t] * Math.cos(ww * Math.PI / 2));
                } else m = cc[t];
                o[i] = m * gain[i] + v[i];
            }
        }
        limitMulti(out, sr);
        return out;
    }
}
