package ar.tuyu.grabadora;

import android.content.Context;
import android.content.SharedPreferences;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.text.SimpleDateFormat;
import java.util.*;

/** Índice de grabaciones: nombres numéricos 1.m4a, 2.m4a... y renumeración diaria. */
class Store {
    static class Rec { String file; long created; long durMs; }

    static final String EXT = ".m4a";
    final File dir;
    final File index;
    final SharedPreferences prefs;
    final List<Rec> recs = new ArrayList<>();

    Store(Context c) {
        dir = new File(c.getExternalFilesDir(null), "grabaciones");
        dir.mkdirs();
        index = new File(dir, "indice.json");
        prefs = c.getSharedPreferences("cfg", Context.MODE_PRIVATE);
        load();
    }

    File fileOf(Rec r) { return new File(dir, r.file); }
    File tempFile() { return new File(dir, "grabando.tmp"); }

    private void load() {
        recs.clear();
        try {
            if (!index.exists()) return;
            BufferedReader br = new BufferedReader(new FileReader(index));
            StringBuilder sb = new StringBuilder(); String l;
            while ((l = br.readLine()) != null) sb.append(l);
            br.close();
            JSONArray a = new JSONArray(sb.toString());
            for (int i = 0; i < a.length(); i++) {
                JSONObject o = a.getJSONObject(i);
                Rec r = new Rec();
                r.file = o.getString("file"); r.created = o.getLong("created"); r.durMs = o.optLong("dur");
                if (fileOf(r).exists()) recs.add(r);
            }
            sort();
        } catch (Exception e) { /* índice corrupto: se reconstruye vacío */ }
    }

    private void sort() {
        Collections.sort(recs, (x, y) -> Long.compare(x.created, y.created));
    }

    void save() {
        try {
            JSONArray a = new JSONArray();
            for (Rec r : recs) {
                JSONObject o = new JSONObject();
                o.put("file", r.file); o.put("created", r.created); o.put("dur", r.durMs);
                a.put(o);
            }
            File tmp = new File(dir, "indice.tmp");
            FileWriter w = new FileWriter(tmp); w.write(a.toString()); w.close();
            tmp.renameTo(index);
        } catch (Exception ignored) { }
    }

    static int numberOf(Rec r) {
        try { return Integer.parseInt(r.file.replace(EXT, "")); } catch (Exception e) { return 0; }
    }

    int nextFreeNumber() {
        Set<Integer> used = new HashSet<>();
        for (Rec r : recs) used.add(numberOf(r));
        int n = 1;
        while (used.contains(n)) n++;
        return n;
    }

    Rec add(File temp, long durMs) {
        Rec r = new Rec();
        r.file = nextFreeNumber() + EXT;
        r.created = System.currentTimeMillis();
        r.durMs = durMs;
        File dest = fileOf(r);
        dest.delete();
        temp.renameTo(dest);
        recs.add(r); sort(); save();
        return r;
    }

    /** Reemplaza el audio manteniendo el mismo nombre y el mismo lugar en el orden. */
    void replace(Rec r, File temp, long durMs) {
        File dest = fileOf(r);
        dest.delete();
        temp.renameTo(dest);
        r.durMs = durMs;
        save();
    }

    void delete(Rec r) {
        fileOf(r).delete();
        recs.remove(r);
        save();
    }

    /** Si cambió el día, vuelve a numerar 1,2,3... según el orden de grabación. */
    boolean normalizeIfNewDay() {
        String today = new SimpleDateFormat("yyyyMMdd", Locale.US).format(new Date());
        if (today.equals(prefs.getString("ultimoDia", ""))) return false;
        renumber();
        prefs.edit().putString("ultimoDia", today).apply();
        return true;
    }

    void renumber() {
        sort();
        for (int i = 0; i < recs.size(); i++) {           // paso 1: nombres temporales (evita choques)
            Rec r = recs.get(i);
            File f = fileOf(r);
            File t = new File(dir, "renum_" + i + ".tmp");
            if (f.renameTo(t)) r.file = "renum_" + i + ".tmp";
        }
        for (int i = 0; i < recs.size(); i++) {           // paso 2: nombres finales
            Rec r = recs.get(i);
            File t = fileOf(r);
            String fin = (i + 1) + EXT;
            if (t.renameTo(new File(dir, fin))) r.file = fin;
        }
        save();
    }
}
