package ar.tuyu.grabadora;

import android.media.*;
import java.io.File;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;

/** Decodifica el audio grabado, le aplica el procesado FM (Dsp) y lo vuelve a guardar como AAC .m4a. */
class Processor {
    /** @return null si salió bien, o el mensaje de error (el original queda intacto). */
    static String process(File in, File out) {
        try {
            int[] fmt = new int[2];
            float[] pcm = decode(in, fmt);
            int sr = fmt[0];
            if (pcm.length < sr / 2) return "audio muy corto";
            float[] y = Dsp.process(pcm, sr);
            pcm = null;
            encode(y, sr, out);
            return null;
        } catch (Throwable e) {
            return e.getClass().getSimpleName() + ": " + e.getMessage();
        }
    }

    private static float[] decode(File f, int[] fmt) throws Exception {
        MediaExtractor ex = new MediaExtractor();
        ex.setDataSource(f.getAbsolutePath());
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
        long est = Math.max(1, tf.containsKey(MediaFormat.KEY_DURATION) ? tf.getLong(MediaFormat.KEY_DURATION) / 1000000L + 2 : 60);
        float[] buf = new float[(int) (est * sr)];
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
                if (n + frames > buf.length) buf = java.util.Arrays.copyOf(buf, Math.max(buf.length * 3 / 2, n + frames));
                for (int i = 0; i < frames; i++) {
                    float s = 0;
                    for (int c = 0; c < ch; c++) s += sb.get() / 32768f;
                    buf[n++] = s / ch;                            // a mono
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
        return java.util.Arrays.copyOf(buf, n);
    }

    private static void encode(float[] x, int sr, File out) throws Exception {
        MediaFormat f = MediaFormat.createAudioFormat(MediaFormat.MIMETYPE_AUDIO_AAC, sr, 1);
        f.setInteger(MediaFormat.KEY_AAC_PROFILE, MediaCodecInfo.CodecProfileLevel.AACObjectLC);
        f.setInteger(MediaFormat.KEY_BIT_RATE, 96000);
        f.setInteger(MediaFormat.KEY_MAX_INPUT_SIZE, 16384);
        MediaCodec enc = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_AUDIO_AAC);
        enc.configure(f, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE);
        enc.start();
        out.delete();
        MediaMuxer mux = new MediaMuxer(out.getAbsolutePath(), MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4);
        int mt = -1; boolean muxOn = false;
        MediaCodec.BufferInfo bi = new MediaCodec.BufferInfo();
        int pos = 0; boolean inDone = false, outDone = false;
        while (!outDone) {
            if (!inDone) {
                int ii = enc.dequeueInputBuffer(10000);
                if (ii >= 0) {
                    ByteBuffer b = enc.getInputBuffer(ii);
                    b.clear();
                    int frames = Math.min(x.length - pos, b.capacity() / 2);
                    long pts = (long) pos * 1000000L / sr;
                    if (frames <= 0) { enc.queueInputBuffer(ii, 0, 0, pts, MediaCodec.BUFFER_FLAG_END_OF_STREAM); inDone = true; }
                    else {
                        b.order(ByteOrder.nativeOrder());
                        for (int i = 0; i < frames; i++) {
                            float v = Math.max(-1f, Math.min(1f, x[pos + i]));
                            b.putShort((short) Math.round(v * 32767f));
                        }
                        enc.queueInputBuffer(ii, 0, frames * 2, pts, 0);
                        pos += frames;
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
        if (muxOn) { mux.stop(); }
        mux.release();
    }
}
