package ar.tuyu.grabadora;

import android.app.*;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.media.*;
import android.os.*;
import java.io.File;

/** Servicio en primer plano: mantiene la grabación viva aunque se cambie de app o se apague la pantalla. */
public class RecorderService extends Service {
    static final String CANAL = "grabando";
    private final IBinder binder = new LocalBinder();
    class LocalBinder extends Binder { RecorderService get() { return RecorderService.this; } }

    private MediaRecorder rec;
    private boolean grabando = false, btActivo = false;
    private long t0;
    private AudioManager am;

    @Override public void onCreate() {
        super.onCreate();
        am = (AudioManager) getSystemService(AUDIO_SERVICE);
        if (Build.VERSION.SDK_INT >= 26) {
            NotificationChannel c = new NotificationChannel(CANAL, "Grabación en curso", NotificationManager.IMPORTANCE_LOW);
            ((NotificationManager) getSystemService(NOTIFICATION_SERVICE)).createNotificationChannel(c);
        }
    }

    @Override public IBinder onBind(Intent i) { return binder; }

    @Override public int onStartCommand(Intent i, int f, int id) {
        ponerPrimerPlano();
        return START_NOT_STICKY;
    }

    private void ponerPrimerPlano() {
        Intent abrir = new Intent(this, MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_REORDER_TO_FRONT);
        PendingIntent pi = PendingIntent.getActivity(this, 0, abrir, PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
        Notification.Builder b = Build.VERSION.SDK_INT >= 26 ? new Notification.Builder(this, CANAL) : new Notification.Builder(this);
        Notification n = b.setContentTitle("● Grabando…").setContentText("Tocá para volver a la app y detener")
                .setSmallIcon(android.R.drawable.ic_btn_speak_now).setOngoing(true).setContentIntent(pi).build();
        if (Build.VERSION.SDK_INT >= 29) startForeground(1, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE);
        else startForeground(1, n);
    }

    boolean isRecording() { return grabando; }
    long elapsedMs() { return SystemClock.elapsedRealtime() - t0; }

    /** @return null si arrancó bien, o el mensaje de error. */
    String start(File out, int deviceId, boolean bt) {
        try {
            ponerPrimerPlano();
            AudioDeviceInfo dev = null;
            if (deviceId >= 0)
                for (AudioDeviceInfo d : am.getDevices(AudioManager.GET_DEVICES_INPUTS)) if (d.getId() == deviceId) dev = d;
            if (bt && dev != null) activarBluetooth(dev);
            out.delete();
            rec = Build.VERSION.SDK_INT >= 31 ? new MediaRecorder(this) : new MediaRecorder();
            rec.setAudioSource(bt ? MediaRecorder.AudioSource.VOICE_COMMUNICATION : MediaRecorder.AudioSource.MIC);
            rec.setOutputFormat(MediaRecorder.OutputFormat.MPEG_4);
            rec.setAudioEncoder(MediaRecorder.AudioEncoder.AAC);
            rec.setAudioChannels(1);
            rec.setAudioSamplingRate(44100);
            rec.setAudioEncodingBitRate(64000);
            rec.setOutputFile(out.getAbsolutePath());
            if (dev != null) rec.setPreferredDevice(dev);
            rec.prepare();
            rec.start();
            grabando = true;
            t0 = SystemClock.elapsedRealtime();
            return null;
        } catch (Exception e) {
            liberar();
            return e.getMessage() == null ? e.getClass().getSimpleName() : e.getMessage();
        }
    }

    /** @return duración en ms, o -1 si la grabación fue demasiado corta/falló. */
    long stop() {
        long dur = elapsedMs();
        boolean ok = grabando;
        try { if (rec != null) rec.stop(); } catch (RuntimeException e) { ok = false; }
        liberar();
        return ok ? dur : -1;
    }

    private void liberar() {
        grabando = false;
        if (rec != null) { try { rec.release(); } catch (Exception ignored) { } rec = null; }
        desactivarBluetooth();
        stopForeground(true);
        stopSelf();
    }

    @SuppressWarnings("deprecation")
    private void activarBluetooth(AudioDeviceInfo dev) {
        am.setMode(AudioManager.MODE_IN_COMMUNICATION);
        if (Build.VERSION.SDK_INT >= 31) {
            for (AudioDeviceInfo o : am.getAvailableCommunicationDevices())
                if (o.getId() == dev.getId() || (o.getType() == dev.getType() && o.getAddress().equals(dev.getAddress())))
                    { am.setCommunicationDevice(o); break; }
        } else { am.startBluetoothSco(); am.setBluetoothScoOn(true); }
        btActivo = true;
        try { Thread.sleep(900); } catch (InterruptedException ignored) { }
    }

    @SuppressWarnings("deprecation")
    private void desactivarBluetooth() {
        if (!btActivo) return;
        if (Build.VERSION.SDK_INT >= 31) am.clearCommunicationDevice();
        else { am.setBluetoothScoOn(false); am.stopBluetoothSco(); }
        am.setMode(AudioManager.MODE_NORMAL);
        btActivo = false;
    }

    @Override public void onDestroy() { if (grabando) liberar(); super.onDestroy(); }
}
