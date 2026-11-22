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

    static float[] process(float[] in, int sr) {
        float[] x = in.clone();
        // 1) filtros
        Bq[] eq = {
            Bq.highpass(85, 0.7071, sr),
            Bq.peak(140, 1.0, -2.0, sr),
            Bq.peak(280, 1.0, -3.5, sr),
            Bq.peak(500, 1.2, -2.0, sr),
            Bq.peak(2800, 1.0, 4.0, sr),
            Bq.peak(5000, 1.2, 3.0, sr),
            Bq.highShelf(9000, 2.5, sr)
        };
        for (Bq b : eq) b.run(x);
        // 2) compresor
        compress(x, sr, -24, 3.5, 8, 120, 6);
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
    static void limit(float[] x, int sr) {
        int n = x.length, L = Math.max(2, (int) (0.005 * sr));
        float[] g = new float[n];
        for (int i = 0; i < n; i++) { float a = Math.abs(x[i]); g[i] = a > TECHO ? (float) (TECHO / a) : 1f; }
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
            x[i] *= (float) ((sum + pad) / L);
        }
    }
}
