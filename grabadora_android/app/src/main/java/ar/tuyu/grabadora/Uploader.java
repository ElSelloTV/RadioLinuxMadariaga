package ar.tuyu.grabadora;

import android.util.Base64;
import org.json.JSONObject;
import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.regex.*;

/** Sube un archivo a la carpeta de Drive vía el Apps Script del usuario (reemplaza si existe). */
class Uploader {
    static String folderId(String link) {
        if (link == null) return "";
        link = link.trim();
        Matcher m = Pattern.compile("folders/([A-Za-z0-9_-]+)").matcher(link);
        if (m.find()) return m.group(1);
        m = Pattern.compile("[?&]id=([A-Za-z0-9_-]+)").matcher(link);
        if (m.find()) return m.group(1);
        return link.matches("[A-Za-z0-9_-]{15,}") ? link : "";
    }

    /** @return null si salió bien, o el mensaje de error. */
    static String upload(String scriptUrl, String token, String folderId, File f, String name) {
        HttpURLConnection c = null;
        try {
            byte[] data = new byte[(int) f.length()];
            DataInputStream in = new DataInputStream(new FileInputStream(f));
            in.readFully(data); in.close();
            JSONObject body = new JSONObject();
            body.put("token", token);
            body.put("folderId", folderId);
            body.put("name", name);
            body.put("mime", "audio/mp4");
            body.put("data", Base64.encodeToString(data, Base64.NO_WRAP));
            byte[] out = body.toString().getBytes("UTF-8");

            c = (HttpURLConnection) new URL(scriptUrl).openConnection();
            c.setRequestMethod("POST");
            c.setDoOutput(true);
            c.setConnectTimeout(20000);
            c.setReadTimeout(120000);
            c.setFixedLengthStreamingMode(out.length);
            c.setRequestProperty("Content-Type", "text/plain; charset=utf-8");
            OutputStream os = c.getOutputStream(); os.write(out); os.close();

            int code = c.getResponseCode();
            InputStream is = code >= 400 ? c.getErrorStream() : c.getInputStream();
            StringBuilder sb = new StringBuilder();
            if (is != null) {
                BufferedReader br = new BufferedReader(new InputStreamReader(is, "UTF-8"));
                String l; while ((l = br.readLine()) != null) sb.append(l);
                br.close();
            }
            if (code >= 400) return "HTTP " + code;
            try {
                JSONObject r = new JSONObject(sb.toString());
                if (r.optBoolean("ok")) return null;
                return "Drive: " + r.optString("error", "respuesta inválida");
            } catch (Exception e) {
                return "Respuesta inesperada (¿URL del script correcta y publicada para 'Cualquier usuario'?)";
            }
        } catch (Exception e) {
            return e.getClass().getSimpleName() + ": " + e.getMessage();
        } finally {
            if (c != null) c.disconnect();
        }
    }
}
