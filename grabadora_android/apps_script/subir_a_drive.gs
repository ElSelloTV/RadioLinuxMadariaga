/**
 * Receptor de la Grabadora de Voz. Se pega UNA vez en script.google.com
 * (ver LEEME.txt). Guarda cada audio en la carpeta de Drive indicada por la
 * app y, si ya existe un archivo con el mismo nombre, lo reemplaza.
 */
var TOKEN = 'CAMBIA_ESTA_CLAVE';   // la misma que pongas en la app

function doPost(e) {
  try {
    var d = JSON.parse(e.postData.contents);
    if (d.token !== TOKEN) return resp({ok: false, error: 'clave incorrecta'});
    var carpeta = DriveApp.getFolderById(d.folderId);
    var existentes = carpeta.getFilesByName(d.name);
    while (existentes.hasNext()) existentes.next().setTrashed(true);   // reemplazo
    var blob = Utilities.newBlob(Utilities.base64Decode(d.data), d.mime, d.name);
    carpeta.createFile(blob);
    return resp({ok: true});
  } catch (err) {
    return resp({ok: false, error: String(err)});
  }
}

function resp(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}
