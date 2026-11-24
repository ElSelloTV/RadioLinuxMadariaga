package ar.tuyu.grabadora;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.ServiceConnection;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.media.*;
import android.os.*;
import android.text.InputType;
import android.view.*;
import android.widget.*;
import java.io.File;
import java.util.*;

public class MainActivity extends Activity {
    private Store store;
    private SharedPreferences prefs;
    private AudioManager am;
    private final Handler ui = new Handler(Looper.getMainLooper());

    // UI
    private TextView tvEstado, tvTimer;
    private Button btnRec, btnCancel, btnSubir;
    private Spinner spMic;
    private ListView lista;
    private Adapter adapter;

    // grabación
    private boolean grabando = false;
    private Store.Rec destino = null;      // null = grabación nueva; si no, reemplaza a este
    private long t0;

    // reproducción
    private MediaPlayer player;
    private Store.Rec sonando;

    // micrófonos
    private final List<AudioDeviceInfo> mics = new ArrayList<>();
    private boolean subiendo = false, procesando = false;
    private ProgressBar pbProc;

    private final Runnable tick = new Runnable() {
        @Override public void run() {
            if (grabando) {
                long s = (SystemClock.elapsedRealtime() - t0) / 1000;
                tvTimer.setText(String.format(Locale.US, "%02d:%02d", s / 60, s % 60));
            } else if (!subiendo && !procesando && store.normalizeIfNewDay()) {
                adapter.notifyDataSetChanged();
                toast("Nuevo día: las grabaciones se renumeraron en orden.");
            }
            ui.postDelayed(this, 1000);
        }
    };

    @Override protected void onCreate(Bundle b) {
        super.onCreate(b);
        store = new Store(this);
        prefs = store.prefs;
        am = (AudioManager) getSystemService(Context.AUDIO_SERVICE);
        construirUi();
        pedirPermisos();
        bindService(new Intent(this, RecorderService.class), conn, BIND_AUTO_CREATE);
        am.registerAudioDeviceCallback(new AudioDeviceCallback() {
            @Override public void onAudioDevicesAdded(AudioDeviceInfo[] d) { refrescarMics(); }
            @Override public void onAudioDevicesRemoved(AudioDeviceInfo[] d) { refrescarMics(); }
        }, ui);
        store.normalizeIfNewDay();
        adapter.notifyDataSetChanged();
    }

    @Override protected void onResume() { super.onResume(); ui.post(tick); refrescarMics(); }
    @Override protected void onPause() { super.onPause(); ui.removeCallbacks(tick); }
    @Override protected void onDestroy() {
        super.onDestroy();
        try { unbindService(conn); } catch (Exception ignored) { }   // la grabación sigue en el servicio
        detenerReproduccion();
    }

    // ------------------------------------------------------------ UI
    private int dp(int v) { return (int) (v * getResources().getDisplayMetrics().density); }

    private Button boton(String t, int color) {
        Button x = new Button(this);
        x.setText(t); x.setAllCaps(false); x.setTextColor(Color.WHITE); x.setTextSize(16);
        GradientDrawable g = new GradientDrawable();
        g.setColor(color); g.setCornerRadius(dp(10));
        x.setBackground(g);
        return x;
    }

    private void construirUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.parseColor("#F4F4F4"));

        // cabecera
        LinearLayout head = new LinearLayout(this);
        head.setOrientation(LinearLayout.HORIZONTAL);
        head.setGravity(Gravity.CENTER_VERTICAL);
        head.setBackgroundColor(Color.parseColor("#B71C1C"));
        head.setPadding(dp(16), dp(36), dp(8), dp(12));
        TextView t = new TextView(this);
        t.setText("Grabadora de Voz"); t.setTextColor(Color.WHITE); t.setTextSize(20); t.setTypeface(null, Typeface.BOLD);
        head.addView(t, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        Button cfg = new Button(this);
        cfg.setText("⚙ Configuración"); cfg.setAllCaps(false); cfg.setTextColor(Color.WHITE);
        cfg.setBackgroundColor(Color.TRANSPARENT);
        cfg.setOnClickListener(v -> dialogoConfig());
        head.addView(cfg);
        root.addView(head);

        // micrófono
        LinearLayout mic = new LinearLayout(this);
        mic.setOrientation(LinearLayout.HORIZONTAL);
        mic.setGravity(Gravity.CENTER_VERTICAL);
        mic.setPadding(dp(16), dp(10), dp(16), 0);
        TextView lm = new TextView(this); lm.setText("Micrófono:"); lm.setTextColor(Color.DKGRAY);
        mic.addView(lm);
        spMic = new Spinner(this);
        mic.addView(spMic, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        root.addView(mic);

        // timer + estado
        tvTimer = new TextView(this);
        tvTimer.setText("00:00"); tvTimer.setTextSize(44); tvTimer.setGravity(Gravity.CENTER);
        tvTimer.setTextColor(Color.parseColor("#212121")); tvTimer.setTypeface(Typeface.MONOSPACE);
        root.addView(tvTimer);
        tvEstado = new TextView(this);
        tvEstado.setText("Listo para grabar"); tvEstado.setGravity(Gravity.CENTER); tvEstado.setTextColor(Color.GRAY);
        root.addView(tvEstado);
        pbProc = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        pbProc.setMax(100); pbProc.setVisibility(View.GONE);
        LinearLayout.LayoutParams lpp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        lpp.setMargins(dp(24), dp(6), dp(24), 0);
        root.addView(pbProc, lpp);

        LinearLayout bar = new LinearLayout(this);
        bar.setOrientation(LinearLayout.HORIZONTAL);
        bar.setPadding(dp(16), dp(10), dp(16), dp(6));
        btnRec = boton("●  GRABAR", Color.parseColor("#D32F2F"));
        btnRec.setTextSize(20);
        btnRec.setOnClickListener(v -> { if (grabando) detenerGrabacion(); else iniciarGrabacion(null); });
        bar.addView(btnRec, new LinearLayout.LayoutParams(0, dp(64), 1));
        btnCancel = boton("Cancelar", Color.parseColor("#757575"));
        btnCancel.setVisibility(View.GONE);
        btnCancel.setOnClickListener(v -> { cancelarGrabacion(); toast("Grabación descartada"); });
        LinearLayout.LayoutParams lpc = new LinearLayout.LayoutParams(dp(110), dp(64));
        lpc.leftMargin = dp(8);
        bar.addView(btnCancel, lpc);
        root.addView(bar);

        lista = new ListView(this);
        adapter = new Adapter();
        lista.setAdapter(adapter);
        lista.setDividerHeight(dp(1));
        root.addView(lista, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1));

        btnSubir = boton("☁  SUBIR TODO A DRIVE", Color.parseColor("#1565C0"));
        LinearLayout.LayoutParams lps = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(56));
        lps.setMargins(dp(16), dp(8), dp(16), dp(16));
        btnSubir.setOnClickListener(v -> subirTodo());
        root.addView(btnSubir, lps);

        setContentView(root);
    }

    private void toast(String s) { Toast.makeText(this, s, Toast.LENGTH_LONG).show(); }

    // ------------------------------------------------------------ permisos y micrófonos
    private void pedirPermisos() {
        List<String> p = new ArrayList<>();
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED)
            p.add(Manifest.permission.RECORD_AUDIO);
        if (Build.VERSION.SDK_INT >= 31 && checkSelfPermission("android.permission.BLUETOOTH_CONNECT") != PackageManager.PERMISSION_GRANTED)
            p.add("android.permission.BLUETOOTH_CONNECT");
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission("android.permission.POST_NOTIFICATIONS") != PackageManager.PERMISSION_GRANTED)
            p.add("android.permission.POST_NOTIFICATIONS");
        if (!p.isEmpty()) requestPermissions(p.toArray(new String[0]), 1);
    }

    @Override public void onRequestPermissionsResult(int rc, String[] perms, int[] res) {
        refrescarMics();
    }

    private String nombreMic(AudioDeviceInfo d) {
        String n = d.getProductName() == null ? "" : d.getProductName().toString();
        switch (d.getType()) {
            case AudioDeviceInfo.TYPE_BUILTIN_MIC: return "Micrófono del celular";
            case AudioDeviceInfo.TYPE_WIRED_HEADSET: return "Cable / auricular con micrófono " + n;
            case AudioDeviceInfo.TYPE_USB_DEVICE:
            case AudioDeviceInfo.TYPE_USB_HEADSET: return "USB " + n;
            case AudioDeviceInfo.TYPE_BLUETOOTH_SCO: return "Bluetooth " + n;
            default: return "Bluetooth BLE " + n;
        }
    }

    private boolean esMicExterno(AudioDeviceInfo d) {
        int t = d.getType();
        return t == AudioDeviceInfo.TYPE_BUILTIN_MIC || t == AudioDeviceInfo.TYPE_WIRED_HEADSET
                || t == AudioDeviceInfo.TYPE_USB_DEVICE || t == AudioDeviceInfo.TYPE_USB_HEADSET
                || t == AudioDeviceInfo.TYPE_BLUETOOTH_SCO || (Build.VERSION.SDK_INT >= 31 && t == 26 /*BLE_HEADSET*/);
    }

    private void refrescarMics() {
        if (grabando) return;
        AudioDeviceInfo sel = micElegido();
        int selId = sel == null ? -1 : sel.getId();
        mics.clear();
        List<String> nombres = new ArrayList<>();
        nombres.add("Automático (el que esté conectado)");
        for (AudioDeviceInfo d : am.getDevices(AudioManager.GET_DEVICES_INPUTS)) {
            if (esMicExterno(d)) { mics.add(d); nombres.add(nombreMic(d)); }
        }
        ArrayAdapter<String> a = new ArrayAdapter<>(this, android.R.layout.simple_spinner_dropdown_item, nombres);
        spMic.setAdapter(a);
        for (int i = 0; i < mics.size(); i++) if (mics.get(i).getId() == selId) spMic.setSelection(i + 1);
    }

    private AudioDeviceInfo micElegido() {
        int pos = spMic == null ? 0 : spMic.getSelectedItemPosition();
        return (pos > 0 && pos - 1 < mics.size()) ? mics.get(pos - 1) : null;
    }

    // ------------------------------------------------------------ grabación (en un servicio de primer plano)
    private RecorderService svc;
    private final ServiceConnection conn = new ServiceConnection() {
        @Override public void onServiceConnected(ComponentName n, IBinder b) {
            svc = ((RecorderService.LocalBinder) b).get();
            if (svc.isRecording() && !grabando) {          // volvimos a la app con una grabación en curso
                grabando = true;
                t0 = SystemClock.elapsedRealtime() - svc.elapsedMs();
                String df = prefs.getString("destino", "");
                destino = null;
                for (Store.Rec r : store.recs) if (r.file.equals(df)) destino = r;
                uiGrabando();
            }
        }
        @Override public void onServiceDisconnected(ComponentName n) { svc = null; }
    };

    private void iniciarGrabacion(Store.Rec reemplazar) {
        if (subiendo || procesando) { toast("Esperá a que termine la subida o el procesado"); return; }
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            pedirPermisos(); return;
        }
        if (svc == null) { toast("Iniciando servicio, probá de nuevo"); return; }
        detenerReproduccion();
        AudioDeviceInfo dev = micElegido();
        boolean bt = dev != null && (dev.getType() == AudioDeviceInfo.TYPE_BLUETOOTH_SCO
                || (Build.VERSION.SDK_INT >= 31 && dev.getType() == 26));
        Intent it = new Intent(this, RecorderService.class);
        if (Build.VERSION.SDK_INT >= 26) startForegroundService(it); else startService(it);
        String err = svc.start(store.tempFile(), dev == null ? -1 : dev.getId(), bt);
        if (err != null) { toast("No se pudo grabar: " + err); return; }
        destino = reemplazar;
        prefs.edit().putString("destino", reemplazar == null ? "" : reemplazar.file).apply();
        grabando = true;
        t0 = SystemClock.elapsedRealtime();
        uiGrabando();
    }

    private void uiGrabando() {
        btnRec.setText("■  DETENER");
        btnCancel.setVisibility(View.VISIBLE);
        btnSubir.setEnabled(false);
        spMic.setEnabled(false);
        tvEstado.setText(destino == null ? "Grabando archivo " + store.nextFreeNumber() + "  (podés cambiar de app)"
                : "Regrabando archivo " + Store.numberOf(destino) + " (reemplaza al anterior)");
        tvEstado.setTextColor(Color.parseColor("#D32F2F"));
    }

    private void detenerGrabacion() {
        final long dur = svc != null ? svc.stop() : -1;
        grabando = false;                                   // el reloj se detiene ya
        long sg = Math.max(0, dur) / 1000;
        tvTimer.setText(String.format(Locale.US, "%02d:%02d", sg / 60, sg % 60));
        final File tmp = store.tempFile();
        if (dur < 0 || !tmp.exists() || tmp.length() == 0) {
            tmp.delete(); toast("Grabación demasiado corta, descartada"); finGrabacion(); return;
        }
        final boolean fm = prefs.getBoolean("fm", true), cortina = prefs.getBoolean("cortina", true);
        if (!fm && !cortina) { guardarGrabacion(tmp, dur); return; }
        // Procesado en segundo plano con barra de progreso
        procesando = true;
        btnRec.setEnabled(false); btnCancel.setVisibility(View.GONE); btnSubir.setEnabled(false);
        pbProc.setProgress(0); pbProc.setVisibility(View.VISIBLE);
        tvEstado.setText("Procesando… 0%");
        tvEstado.setTextColor(Color.parseColor("#1565C0"));
        new Thread(() -> {
            File sal = new File(store.dir, "procesado.tmp");
            long[] d = new long[1];
            final String err = Processor.process(tmp, sal, fm, cortina, getAssets(),
                    (pct, msg) -> ui.post(() -> { pbProc.setProgress(pct); tvEstado.setText(msg + " " + pct + "%"); }), d);
            ui.post(() -> {
                boolean ok = (err == null || err.startsWith("AVISO:")) && sal.exists() && sal.length() > 0;
                if (ok) {
                    tmp.delete();
                    if (err != null) toast(err.substring(6).trim());
                    guardarGrabacion(sal, d[0] > 0 ? d[0] : dur);
                } else {
                    sal.delete();
                    toast("No se pudo procesar (" + err + "). Se guardó la grabación original.");
                    guardarGrabacion(tmp, dur);
                }
            });
        }).start();
    }

    private void guardarGrabacion(File f, long dur) {
        if (destino == null) {
            Store.Rec r = store.add(f, dur);
            toast("Guardado como " + r.file);
        } else {
            store.replace(destino, f, dur);
            toast("Archivo " + destino.file + " reemplazado");
        }
        finGrabacion();
    }

    private void cancelarGrabacion() {
        if (svc != null) svc.stop();
        store.tempFile().delete();
        finGrabacion();
    }

    private void finGrabacion() {
        grabando = false; procesando = false; destino = null;
        pbProc.setVisibility(View.GONE);
        btnRec.setEnabled(true);
        btnRec.setText("●  GRABAR");
        btnCancel.setVisibility(View.GONE);
        btnSubir.setEnabled(true);
        spMic.setEnabled(true);
        tvTimer.setText("00:00");
        tvEstado.setText("Listo para grabar");
        tvEstado.setTextColor(Color.GRAY);
        adapter.notifyDataSetChanged();
        refrescarMics();
    }

    // ------------------------------------------------------------ reproducción
    private void alternarReproduccion(Store.Rec r) {
        if (sonando == r) { detenerReproduccion(); return; }
        detenerReproduccion();
        try {
            player = new MediaPlayer();
            player.setDataSource(store.fileOf(r).getAbsolutePath());
            player.prepare(); player.start();
            player.setOnCompletionListener(mp -> detenerReproduccion());
            sonando = r;
        } catch (Exception e) { toast("No se pudo reproducir"); detenerReproduccion(); }
        adapter.notifyDataSetChanged();
    }

    private void detenerReproduccion() {
        if (player != null) { try { player.release(); } catch (Exception ignored) { } player = null; }
        sonando = null;
        if (adapter != null) adapter.notifyDataSetChanged();
    }

    // ------------------------------------------------------------ lista
    private class Adapter extends BaseAdapter {
        @Override public int getCount() { return store.recs.size(); }
        @Override public Object getItem(int i) { return store.recs.get(i); }
        @Override public long getItemId(int i) { return i; }
        @Override public View getView(int i, View v, ViewGroup p) {
            final Store.Rec r = store.recs.get(i);
            LinearLayout row = new LinearLayout(MainActivity.this);
            row.setOrientation(LinearLayout.HORIZONTAL);
            row.setGravity(Gravity.CENTER_VERTICAL);
            row.setPadding(dp(16), dp(8), dp(8), dp(8));
            row.setBackgroundColor(Color.WHITE);

            TextView num = new TextView(MainActivity.this);
            num.setText(String.valueOf(Store.numberOf(r)));
            num.setTextSize(28); num.setTypeface(null, Typeface.BOLD); num.setTextColor(Color.parseColor("#B71C1C"));
            row.addView(num, new LinearLayout.LayoutParams(dp(56), ViewGroup.LayoutParams.WRAP_CONTENT));

            long s = r.durMs / 1000;
            TextView info = new TextView(MainActivity.this);
            info.setText(String.format(Locale.US, "%02d:%02d  ·  %d KB", s / 60, s % 60, store.fileOf(r).length() / 1024));
            info.setTextColor(Color.DKGRAY);
            row.addView(info, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));

            row.addView(chico(sonando == r ? "■" : "▶", x -> alternarReproduccion(r)));
            row.addView(chico("🎙", x -> confirmarRegrabar(r)));
            row.addView(chico("🗑", x -> confirmarBorrar(r)));
            return row;
        }
        private Button chico(String t, View.OnClickListener l) {
            Button b = new Button(MainActivity.this);
            b.setText(t); b.setTextSize(18); b.setAllCaps(false);
            b.setBackgroundColor(Color.TRANSPARENT);
            b.setOnClickListener(l);
            b.setMinWidth(0); b.setMinimumWidth(dp(48));
            return b;
        }
    }

    private void confirmarRegrabar(Store.Rec r) {
        if (grabando || procesando) return;
        new AlertDialog.Builder(this).setTitle("Reemplazar archivo " + r.file)
                .setMessage("Se grabará de nuevo y, al detener, reemplaza el audio actual de " + r.file + ".")
                .setPositiveButton("Grabar", (d, w) -> iniciarGrabacion(r))
                .setNegativeButton("Cancelar", null).show();
    }

    private void confirmarBorrar(Store.Rec r) {
        if (grabando || procesando) return;
        new AlertDialog.Builder(this).setTitle("Borrar " + r.file + "?")
                .setPositiveButton("Borrar", (d, w) -> {
                    if (sonando == r) detenerReproduccion();
                    store.delete(r); adapter.notifyDataSetChanged();
                }).setNegativeButton("Cancelar", null).show();
    }

    // ------------------------------------------------------------ configuración Drive
    private EditText campo(LinearLayout l, String hint, String val) {
        EditText e = new EditText(this);
        e.setHint(hint); e.setText(val); e.setSingleLine(true);
        e.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        l.addView(e);
        return e;
    }

    private void dialogoConfig() {
        LinearLayout l = new LinearLayout(this);
        l.setOrientation(LinearLayout.VERTICAL);
        l.setPadding(dp(20), dp(10), dp(20), 0);
        TextView t = new TextView(this);
        t.setText("Se configura una sola vez. Ver instrucciones del Apps Script (apps_script/subir_a_drive.gs).");
        t.setTextSize(13);
        l.addView(t);
        EditText carpeta = campo(l, "Enlace de la carpeta de Drive", prefs.getString("carpeta", ""));
        EditText script = campo(l, "URL del Apps Script (…/exec)", prefs.getString("script", ""));
        EditText token = campo(l, "Clave secreta (token)", prefs.getString("token", ""));
        CheckBox fm = new CheckBox(this);
        fm.setText("Ecualizar para radio FM (al terminar de grabar)");
        fm.setChecked(prefs.getBoolean("fm", true));
        l.addView(fm);
        CheckBox cort = new CheckBox(this);
        cort.setText("Agregar cortina musical con ducking (la voz entra a los 12 s)");
        cort.setChecked(prefs.getBoolean("cortina", true));
        l.addView(cort);
        new AlertDialog.Builder(this).setTitle("Configuración").setView(l)
                .setPositiveButton("Guardar", (d, w) -> {
                    if (Uploader.folderId(carpeta.getText().toString()).isEmpty()) {
                        toast("El enlace de la carpeta no es válido"); return;
                    }
                    prefs.edit().putString("carpeta", carpeta.getText().toString().trim())
                            .putString("script", script.getText().toString().trim())
                            .putString("token", token.getText().toString().trim())
                            .putBoolean("fm", fm.isChecked()).putBoolean("cortina", cort.isChecked()).apply();
                    toast("Configuración guardada");
                }).setNegativeButton("Cancelar", null).show();
    }

    // ------------------------------------------------------------ subida
    private void subirTodo() {
        if (grabando || subiendo || procesando) return;
        final String script = prefs.getString("script", "");
        final String token = prefs.getString("token", "");
        final String folder = Uploader.folderId(prefs.getString("carpeta", ""));
        if (script.isEmpty() || folder.isEmpty()) { dialogoConfig(); toast("Primero configurá la carpeta y el script"); return; }
        if (store.recs.isEmpty()) { toast("No hay grabaciones para subir"); return; }
        final List<Store.Rec> todas = new ArrayList<>(store.recs);
        subiendo = true;
        btnSubir.setEnabled(false); btnRec.setEnabled(false);
        new Thread(() -> {
            int ok = 0; String err = null;
            for (int i = 0; i < todas.size(); i++) {
                final Store.Rec r = todas.get(i);
                final int n = i + 1;
                ui.post(() -> tvEstado.setText("Subiendo " + r.file + " (" + n + "/" + todas.size() + ")…"));
                String e = Uploader.upload(script, token, folder, store.fileOf(r), r.file);
                if (e == null) {
                    ok++;
                    ui.post(() -> { store.delete(r); adapter.notifyDataSetChanged(); });  // ya está en Drive: se borra del celular
                } else { err = r.file + ": " + e; }
            }
            final int fok = ok; final String ferr = err;
            ui.post(() -> {
                subiendo = false;
                btnSubir.setEnabled(true); btnRec.setEnabled(true);
                tvEstado.setText("Listo para grabar");
                new AlertDialog.Builder(this).setTitle(ferr == null ? "Subida completa" : "Subida con errores")
                        .setMessage(fok + " archivo(s) subidos y borrados del celular." + (ferr == null ? "" : "\n\nNo se subió (se conserva en el celular):\n" + ferr))
                        .setPositiveButton("OK", null).show();
            });
        }).start();
    }
}
