package ar.tuyu.grabadora;

import android.content.res.AssetFileDescriptor;
import android.content.res.AssetManager;
import android.media.*;
import java.io.File;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.Arrays;

/** Decodifica la grabación, aplica el procesado FM y la cortina con ducking (Dsp) y la guarda como AAC .m4a. */
class Processor {
    interface Progreso { void p(int pct, String msg); }

    /** Origen de audio por tramos para el codificador (no se guarda la mezcla completa en memoria). */
    interface Fuente { int canales(); int leer(short[] buf, int frames); long totalFrames(); }

    static final int PROC_SIN = 0, PROC_FM = 1, PROC_CORTINA = 2;

    /**
     * @param info [0] = duración final en ms, [1] = estado (0 sin procesar, 1 solo FM, 2 FM + cortina)
     * @return null si salió bien; "AVISO:..." si salió bien pero sin cortina; otro texto = error (el original queda intacto)
     */
    static String process(File in, File out, boolean fm, boolean cortina, AssetManager assets, Progreso cb, long[] info) {
        try {
            cb.p(2, "Leyendo la grabación…");
            int[] fmt = new int[2];
            MediaExtractor ex = new MediaExtractor();
            ex.setDataSource(in.getAbsolutePath());
            short[][] raw = decode(ex, fmt);
            int sr = fmt[0];
            float[] voz = aMono(raw);
            raw = null;
            if (voz.length < sr / 2) return "audio muy corto";

            cb.p(15, fm ? "Ecualizando para radio FM…" : "Nivelando el volumen…");
            Dsp.process(voz, sr, fm);

            Fuente fuente = null; int srOut = sr; String aviso = null;
            if (cortina) {
                try {
                    cb.p(40, "Cargando la cortina…");
                    AssetFileDescriptor afd = assets.openFd("cortina.mp3");
                    MediaExtractor ec = new MediaExtractor();
                    ec.setDataSource(afd.getFileDescriptor(), afd.getStartOffset(), afd.getLength());
                    int[] fc = new int[2];
                    short[][] cor = decode(ec, fc);
                    afd.close();
                    srOut = fc[0];
                    final Dsp.MixStream mix = new Dsp.MixStream(voz, sr, cor, srOut);
                    final int nch = cor.length;
                    fuente = new Fuente() {
                        public int canales() { return nch; }
                        public int leer(short[] b, int n) { return mix.read(b, n); }
                        public long totalFrames() { return mix.total(); }
                    };
                    info[1] = PROC_CORTINA;
                } catch (Throwable t) {
                    fuente = null; srOut = sr;
                    aviso = "AVISO: no se pudo agregar la cortina (" + (t.getMessage() == null ? t.getClass().getSimpleName() : t.getMessage()) + ")";
                }
            }
            if (fuente == null) {
                final float[] v = voz;
                final int[] pos = {0};
                info[1] = fm ? PROC_FM : PROC_SIN;
                fuente = new Fuente() {
                    public int canales() { return 1; }
                    public int leer(short[] b, int n) {
                        int k = Math.min(n, v.length - pos[0]);
                        for (int i = 0; i < k; i++) b[i] = (short) Math.round(Math.max(-1f, Math.min(1f, v[pos[0] + i])) * 32767f);
                        pos[0] += k; return k;
                    }
                    public long totalFrames() { return v.length; }
                };
            }
            info[0] = fuente.totalFrames() * 1000L / srOut;
            encode(fuente, srOut, out, cb);
            cb.p(100, "Listo");
            return aviso;
        } catch (OutOfMemoryError e) {
            return "memoria insuficiente (audio demasiado largo)";
        } catch (Throwable e) {
            return e.getClass().getSimpleName() + ": " + e.getMessage();
        }
    }

    private static float[] aMono(short[][] c) {
        int n = c[0].length; float[] m = new float[n];
        if (c.length == 1) for (int i = 0; i < n; i++) m[i] = c[0][i] / 32768f;
        else for (int i = 0; i < n; i++) m[i] = (c[0][i] + c[1][i]) / 65536f;
        return m;
    }

    /** @return [canal][muestra] en 16 bits (1 o 2 canales); fmt[0]=frecuencia, fmt[1]=canales originales. */
    private static short[][] decode(MediaExtractor ex, int[] fmt) throws Exception {
        int track = -1; MediaFormat tf = null;
        for (int i = 0; i < ex.getTrackCount(); i++) {
            MediaFormat mf = ex.getTrackFormat(i);
            String m = mf.getString(MediaFormat.KEY_MIME);
            if (m != null && m.startsWith("audio/")) { track = i; tf = mf; break; }
        }
        if (track < 0) throw new Exception("sin pista de audio");
        ex.selectTrack(track);
        MediaCodec dec = MediaCodec.createDecoderByType(tf.getString(MediaFormat.KEY_MIME));
        dec.configure(tf, null, null, 0);
        dec.start();
        int sr = tf.getInteger(MediaFormat.KEY_SAMPLE_RATE), ch = tf.getInteger(MediaFormat.KEY_CHANNEL_COUNT);
        int nout = Math.min(ch, 2);
        long est = tf.containsKey(MediaFormat.KEY_DURATION) ? tf.getLong(MediaFormat.KEY_DURATION) / 1000000L + 2 : 60;
        short[][] buf = new short[nout][(int) (Math.max(1, est) * sr)];
        int n = 0;
        MediaCodec.BufferInfo bi = new MediaCodec.BufferInfo();
        boolean inDone = false, outDone = false;
        while (!outDone) {
            if (!inDone) {
                int ii = dec.dequeueInputBuffer(10000);
                if (ii >= 0) {
                    ByteBuffer b = dec.getInputBuffer(ii);
                    int sz = ex.readSampleData(b, 0);
                    if (sz < 0) { dec.queueInputBuffer(ii, 0, 0, 0, MediaCodec.BUFFER_FLAG_END_OF_STREAM); inDone = true; }
                    else { dec.queueInputBuffer(ii, 0, sz, ex.getSampleTime(), 0); ex.advance(); }
                }
            }
            int oi = dec.dequeueOutputBuffer(bi, 10000);
            if (oi >= 0) {
                ByteBuffer ob = dec.getOutputBuffer(oi);
                ob.position(bi.offset); ob.limit(bi.offset + bi.size);
                java.nio.ShortBuffer sb = ob.order(ByteOrder.nativeOrder()).asShortBuffer();
                int frames = sb.remaining() / ch;
                if (n + frames > buf[0].length) {
                    int nc = Math.max(buf[0].length + buf[0].length / 4, n + frames);
                    for (int c = 0; c < nout; c++) buf[c] = Arrays.copyOf(buf[c], nc);
                }
                for (int i = 0; i < frames; i++) {
                    for (int c = 0; c < ch; c++) { short s = sb.get(); if (c < nout) buf[c][n] = s; }
                    n++;
                }
                dec.releaseOutputBuffer(oi, false);
                if ((bi.flags & MediaCodec.BUFFER_FLAG_END_OF_STREAM) != 0) outDone = true;
            } else if (oi == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED) {
                MediaFormat of = dec.getOutputFormat();
                sr = of.getInteger(MediaFormat.KEY_SAMPLE_RATE);
            }
        }
        dec.stop(); dec.release(); ex.release();
        fmt[0] = sr; fmt[1] = ch;
        short[][] res = new short[nout][];
        for (int c = 0; c < nout; c++) res[c] = buf[c].length == n ? buf[c] : Arrays.copyOf(buf[c], n);
        return res;
    }

    private static void encode(Fuente src, int sr, File out, Progreso cb) throws Exception {
        int ch = src.canales();
        long total = Math.max(1, src.totalFrames());
        MediaFormat f = MediaFormat.createAudioFormat(MediaFormat.MIMETYPE_AUDIO_AAC, sr, ch);
        f.setInteger(MediaFormat.KEY_AAC_PROFILE, MediaCodecInfo.CodecProfileLevel.AACObjectLC);
        f.setInteger(MediaFormat.KEY_BIT_RATE, ch == 2 ? 128000 : 96000);
        f.setInteger(MediaFormat.KEY_MAX_INPUT_SIZE, 16384);
        MediaCodec enc = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_AUDIO_AAC);
        enc.configure(f, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE);
        enc.start();
        out.delete();
        MediaMuxer mux = new MediaMuxer(out.getAbsolutePath(), MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4);
        int mt = -1; boolean muxOn = false;
        MediaCodec.BufferInfo bi = new MediaCodec.BufferInfo();
        long pos = 0; int lastPct = -1; boolean inDone = false, outDone = false;
        short[] tmp = new short[16384];
        while (!outDone) {
            if (!inDone) {
                int ii = enc.dequeueInputBuffer(10000);
                if (ii >= 0) {
                    ByteBuffer b = enc.getInputBuffer(ii);
                    b.clear();
                    int max = Math.min(b.capacity() / (2 * ch), tmp.length / ch);
                    int frames = src.leer(tmp, max);
                    long pts = pos * 1000000L / sr;
                    if (frames <= 0) { enc.queueInputBuffer(ii, 0, 0, pts, MediaCodec.BUFFER_FLAG_END_OF_STREAM); inDone = true; }
                    else {
                        b.order(ByteOrder.nativeOrder());
                        for (int i = 0; i < frames * ch; i++) b.putShort(tmp[i]);
                        enc.queueInputBuffer(ii, 0, frames * 2 * ch, pts, 0);
                        pos += frames;
                        int pct = 55 + (int) (44L * pos / total);
                        if (pct != lastPct) { lastPct = pct; cb.p(Math.min(99, pct), "Mezclando y guardando…"); }
                    }
                }
            }
            int oi = enc.dequeueOutputBuffer(bi, 10000);
            if (oi >= 0) {
                ByteBuffer ob = enc.getOutputBuffer(oi);
                if ((bi.flags & MediaCodec.BUFFER_FLAG_CODEC_CONFIG) != 0) bi.size = 0;
                if (bi.size > 0 && muxOn) { ob.position(bi.offset); ob.limit(bi.offset + bi.size); mux.writeSampleData(mt, ob, bi); }
                enc.releaseOutputBuffer(oi, false);
                if ((bi.flags & MediaCodec.BUFFER_FLAG_END_OF_STREAM) != 0) outDone = true;
            } else if (oi == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED) {
                mt = mux.addTrack(enc.getOutputFormat()); mux.start(); muxOn = true;
            }
        }
        enc.stop(); enc.release();
        if (muxOn) mux.stop();
        mux.release();
    }
}
