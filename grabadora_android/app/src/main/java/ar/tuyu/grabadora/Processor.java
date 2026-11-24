package ar.tuyu.grabadora;

import android.content.res.AssetFileDescriptor;
import android.content.res.AssetManager;
import android.media.*;
import java.io.File;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.Arrays;

/** Decodifica la grabación, le aplica el procesado FM + cortina con ducking (Dsp) y la guarda como AAC .m4a. */
class Processor {
    interface Progreso { void p(int pct, String msg); }

    /**
     * @param outDurMs [0] = duración final en ms
     * @return null si salió bien; "AVISO:..." si salió bien pero sin cortina; otro texto = error (el original queda intacto)
     */
    static String process(File in, File out, boolean fm, boolean cortina, AssetManager assets, Progreso cb, long[] outDurMs) {
        try {
            cb.p(2, "Leyendo la grabación…");
            int[] fmt = new int[2];
            MediaExtractor ex = new MediaExtractor();
            ex.setDataSource(in.getAbsolutePath());
            float[][] raw = decode(ex, fmt);
            int sr = fmt[0];
            float[] voz = raw.length == 1 ? raw[0] : mono(raw);
            raw = null;
            if (voz.length < sr / 2) return "audio muy corto";

            cb.p(15, fm ? "Ecualizando para radio FM…" : "Nivelando el volumen…");
            voz = Dsp.process(voz, sr, fm);

            float[][] res = null; int srOut = sr; String aviso = null;
            if (cortina) {
                try {
                    cb.p(40, "Cargando la cortina…");
                    AssetFileDescriptor afd = assets.openFd("cortina.mp3");
                    MediaExtractor ec = new MediaExtractor();
                    ec.setDataSource(afd.getFileDescriptor(), afd.getStartOffset(), afd.getLength());
                    int[] fc = new int[2];
                    float[][] cor = decode(ec, fc);
                    afd.close();
                    cb.p(55, "Mezclando con la cortina (ducking)…");
                    float[] v2 = Dsp.resample(voz, sr, fc[0]);
                    res = Dsp.mezclarConCortina(v2, fc[0], cor);
                    srOut = fc[0];
                } catch (Throwable t) {
                    res = null;
                    aviso = "AVISO: no se pudo agregar la cortina (" + t.getMessage() + ")";
                }
            }
            if (res == null) res = new float[][]{voz};
            outDurMs[0] = (long) res[0].length * 1000L / srOut;
            voz = null;

            encode(res, srOut, out, cb);
            cb.p(100, "Listo");
            return aviso;
        } catch (Throwable e) {
            return e.getClass().getSimpleName() + ": " + e.getMessage();
        }
    }

    private static float[] mono(float[][] c) {
        float[] m = new float[c[0].length];
        for (int i = 0; i < m.length; i++) { float s = 0; for (float[] x : c) s += x[i]; m[i] = s / c.length; }
        return m;
    }

    /** @return [canal][muestra] (1 o 2 canales); fmt[0]=frecuencia, fmt[1]=canales originales. */
    private static float[][] decode(MediaExtractor ex, int[] fmt) throws Exception {
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
        long est = tf.containsKey(MediaFormat.KEY_DURATION) ? tf.getLong(MediaFormat.KEY_DURATION) / 1000000L + 2 : 60;
        int cap = (int) (Math.max(1, est) * sr);
        float[][] buf = new float[2][cap];
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
                    int nc = Math.max(buf[0].length * 3 / 2, n + frames);
                    buf[0] = Arrays.copyOf(buf[0], nc); buf[1] = Arrays.copyOf(buf[1], nc);
                }
                for (int i = 0; i < frames; i++) {
                    float l = 0, r = 0;
                    for (int c = 0; c < ch; c++) { float s = sb.get() / 32768f; if (c == 0) l = s; if (c == 1) r = s; }
                    buf[0][n] = l; buf[1][n] = ch > 1 ? r : l;
                    n++;
                }
                dec.releaseOutputBuffer(oi, false);
                if ((bi.flags & MediaCodec.BUFFER_FLAG_END_OF_STREAM) != 0) outDone = true;
            } else if (oi == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED) {
                MediaFormat of = dec.getOutputFormat();
                sr = of.getInteger(MediaFormat.KEY_SAMPLE_RATE); ch = of.getInteger(MediaFormat.KEY_CHANNEL_COUNT);
            }
        }
        dec.stop(); dec.release(); ex.release();
        fmt[0] = sr; fmt[1] = ch;
        if (ch == 1) return new float[][]{Arrays.copyOf(buf[0], n)};
        return new float[][]{Arrays.copyOf(buf[0], n), Arrays.copyOf(buf[1], n)};
    }

    private static void encode(float[][] x, int sr, File out, Progreso cb) throws Exception {
        int ch = x.length, len = x[0].length;
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
        int pos = 0, lastPct = -1; boolean inDone = false, outDone = false;
        while (!outDone) {
            if (!inDone) {
                int ii = enc.dequeueInputBuffer(10000);
                if (ii >= 0) {
                    ByteBuffer b = enc.getInputBuffer(ii);
                    b.clear();
                    int frames = Math.min(len - pos, b.capacity() / (2 * ch));
                    long pts = (long) pos * 1000000L / sr;
                    if (frames <= 0) { enc.queueInputBuffer(ii, 0, 0, pts, MediaCodec.BUFFER_FLAG_END_OF_STREAM); inDone = true; }
                    else {
                        b.order(ByteOrder.nativeOrder());
                        for (int i = 0; i < frames; i++)
                            for (int c = 0; c < ch; c++)
                                b.putShort((short) Math.round(Math.max(-1f, Math.min(1f, x[c][pos + i])) * 32767f));
                        enc.queueInputBuffer(ii, 0, frames * 2 * ch, pts, 0);
                        pos += frames;
                        int pct = 75 + (int) (24L * pos / len);
                        if (pct != lastPct) { lastPct = pct; cb.p(pct, "Guardando el audio…"); }
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
