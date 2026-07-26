/*
    D-Bus server for gst-plugin-viperfx
    Copyright (C) 2020 ThePBone <tim.schneeberger(at)outlook.de>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
#include "dbus-interface.h"
#include <pthread.h>
#include <stdio.h>

static GDBusNodeInfo *introspection_data = NULL;

/* Introspection data for the service we are exporting */
static const gchar introspection_xml[] =
  "<node>"
  "  <interface name='me.noahbliss.ViperFx'>"
  "    <method name='GetVersion'>"
  "      <arg type='s' name='response' direction='out'/>"
  "    </method>"
  "    <method name='GetGstVersion'>"
  "      <arg type='s' name='response' direction='out'/>"
  "    </method>"
  "    <method name='GetAllowedCapabilities'>"
  "      <arg type='s' name='response' direction='out'/>"
  "    </method>"
  "    <method name='GetPackageName'>"
  "      <arg type='s' name='response' direction='out'/>"
  "    </method>"
  "    <method name='GetDriverStatus'>"
  "      <arg type='u' name='id' direction='in'/>"
  "      <arg type='i' name='response' direction='out'/>"
  "    </method>"
  "    <method name='CommitPropertyGroups'>"
  "      <arg type='u' name='bitmask' direction='in'/>"
  "      <arg type='u' name='response' direction='out'/>"
  "    </method>"
  "    <method name='CommitProperties'>"
  "      <arg type='u' name='response' direction='out'/>"
  "    </method>"
  "    <method name='PlayTestTone'>"
  "      <arg type='u' name='freq' direction='in'/>"
  "      <arg type='u' name='dur' direction='in'/>"
  "      <arg type='u' name='response' direction='out'/>\""
  "    </method>"
  "    <signal name='PropertiesCommitted'>"
  "      <arg type='u' name='bitmask' />"
  "      <annotation name='org.gtk.GDBus.Annotation' value='Onsignal'/>"
  "    </signal>"
  "    <property type='b' name='agc_enable' access='readwrite'/>"
  "    <property type='i' name='agc_maxgain' access='readwrite'/>"
  "    <property type='i' name='agc_ratio' access='readwrite'/>"
  "    <property type='i' name='agc_volume' access='readwrite'/>"
  "    <property type='b' name='ax_enable' access='readwrite'/>"
  "    <property type='i' name='ax_mode' access='readwrite'/>"
  "    <property type='b' name='colm_enable' access='readwrite'/>"
  "    <property type='i' name='colm_depth' access='readwrite'/>"
  "    <property type='i' name='colm_midimage' access='readwrite'/>"
  "    <property type='i' name='colm_widening' access='readwrite'/>"
  "    <property type='b' name='conv_enable' access='readwrite'/>"
  "    <property type='i' name='conv_cc_level' access='readwrite'/>"
  "    <property type='s' name='conv_ir_path' access='readwrite'/>"
  "    <property type='b' name='cure_enable' access='readwrite'/>"
  "    <property type='i' name='cure_level' access='readwrite'/>"
  "    <property type='b' name='ds_enable' access='readwrite'/>"
  "    <property type='i' name='ds_level' access='readwrite'/>"
  "    <property type='b' name='dynsys_enable' access='readwrite'/>"
  "    <property type='i' name='dynsys_bassgain' access='readwrite'/>"
  "    <property type='i' name='dynsys_sidegain1' access='readwrite'/>"
  "    <property type='i' name='dynsys_sidegain2' access='readwrite'/>"
  "    <property type='i' name='dynsys_xcoeff1' access='readwrite'/>"
  "    <property type='i' name='dynsys_xcoeff2' access='readwrite'/>"
  "    <property type='i' name='dynsys_ycoeff1' access='readwrite'/>"
  "    <property type='i' name='dynsys_ycoeff2' access='readwrite'/>"
  "    <property type='b' name='eq_enable' access='readwrite'/>"
  "    <property type='i' name='eq_band1' access='readwrite'/>"
  "    <property type='i' name='eq_band2' access='readwrite'/>"
  "    <property type='i' name='eq_band3' access='readwrite'/>"
  "    <property type='i' name='eq_band4' access='readwrite'/>"
  "    <property type='i' name='eq_band5' access='readwrite'/>"
  "    <property type='i' name='eq_band6' access='readwrite'/>"
  "    <property type='i' name='eq_band7' access='readwrite'/>"
  "    <property type='i' name='eq_band8' access='readwrite'/>"
  "    <property type='i' name='eq_band9' access='readwrite'/>"
  "    <property type='i' name='eq_band10' access='readwrite'/>"
  "    <property type='b' name='fetcomp_enable' access='readwrite'/>"
  "    <property type='b' name='fetcomp_autoattack' access='readwrite'/>"
  "    <property type='b' name='fetcomp_autogain' access='readwrite'/>"
  "    <property type='b' name='fetcomp_autoknee' access='readwrite'/>"
  "    <property type='b' name='fetcomp_autorelease' access='readwrite'/>"
  "    <property type='b' name='fetcomp_noclip' access='readwrite'/>"
  "    <property type='i' name='fetcomp_attack' access='readwrite'/>"
  "    <property type='i' name='fetcomp_gain' access='readwrite'/>"
  "    <property type='i' name='fetcomp_kneewidth' access='readwrite'/>"
  "    <property type='i' name='fetcomp_meta_adapt' access='readwrite'/>"
  "    <property type='i' name='fetcomp_meta_crest' access='readwrite'/>"
  "    <property type='i' name='fetcomp_meta_kneemulti' access='readwrite'/>"
  "    <property type='i' name='fetcomp_meta_maxattack' access='readwrite'/>"
  "    <property type='i' name='fetcomp_meta_maxrelease' access='readwrite'/>"
  "    <property type='i' name='fetcomp_ratio' access='readwrite'/>"
  "    <property type='i' name='fetcomp_release' access='readwrite'/>"
  "    <property type='i' name='fetcomp_threshold' access='readwrite'/>"
  "    <property type='b' name='fx_enable' access='readwrite'/>"
  "    <property type='i' name='lim_threshold' access='readwrite'/>"
  "    <property type='i' name='out_pan' access='readwrite'/>"
  "    <property type='i' name='out_volume' access='readwrite'/>"
  "    <property type='b' name='reverb_enable' access='readwrite'/>"
  "    <property type='i' name='reverb_damp' access='readwrite'/>"
  "    <property type='i' name='reverb_dry' access='readwrite'/>"
  "    <property type='i' name='reverb_roomsize' access='readwrite'/>"
  "    <property type='i' name='reverb_wet' access='readwrite'/>"
  "    <property type='i' name='reverb_width' access='readwrite'/>"
  "    <property type='b' name='tube_enable' access='readwrite'/>"
  "    <property type='b' name='vb_enable' access='readwrite'/>"
  "    <property type='i' name='vb_freq' access='readwrite'/>"
  "    <property type='i' name='vb_gain' access='readwrite'/>"
  "    <property type='i' name='vb_mode' access='readwrite'/>"
  "    <property type='b' name='vc_enable' access='readwrite'/>"
  "    <property type='i' name='vc_level' access='readwrite'/>"
  "    <property type='i' name='vc_mode' access='readwrite'/>"
  "    <property type='b' name='vhe_enable' access='readwrite'/>"
  "    <property type='i' name='vhe_level' access='readwrite'/>"
  "    <property type='b' name='vse_enable' access='readwrite'/>"
  "    <property type='i' name='vse_bark_cons' access='readwrite'/>"
  "    <property type='i' name='vse_ref_bark' access='readwrite'/>"
  "  </interface>"
  "</node>";

/* ---------------------------------------------------------------------------------------------------- */

static void
handle_method_call (GDBusConnection       *connection,
                    const gchar           *sender,
                    const gchar           *object_path,
                    const gchar           *interface_name,
                    const gchar           *method_name,
                    GVariant              *parameters,
                    GDBusMethodInvocation *invocation,
                    gpointer               user_data)
{
  userdata_t *user = user_data;
  Gstviperfx *intf = user->intf;

  if (g_strcmp0 (method_name, "GetAllowedCapabilities") == 0)
  {
    gchar *response;
    response = g_strdup_printf (ALLOWED_CAPS);
    g_dbus_method_invocation_return_value (invocation,
                                           g_variant_new ("(s)", response));
    g_free (response);
  }
  else if (g_strcmp0 (method_name, "GetPackageName") == 0)
  {
    gchar *response;
    response = g_strdup_printf (PACKAGE);
    g_dbus_method_invocation_return_value (invocation,
                                           g_variant_new ("(s)", response));
    g_free (response);
  }
  else if (g_strcmp0 (method_name, "GetVersion") == 0)
  {
    gchar *response;
    response = g_strdup_printf (VERSION);
    g_dbus_method_invocation_return_value (invocation,
                                           g_variant_new ("(s)", response));
    g_free (response);
  }
  else if (g_strcmp0 (method_name, "GetGstVersion") == 0)
  {
    gchar *response;
    response = g_strdup_printf ("%d.%d.%d.%d", GST_VERSION_MAJOR,GST_VERSION_MINOR,GST_VERSION_MICRO,GST_VERSION_NANO);
    g_dbus_method_invocation_return_value (invocation,
                                           g_variant_new ("(s)", response));
    g_free (response);
  }
  else if (g_strcmp0 (method_name, "GetDriverStatus") == 0)
  {
    guint32 id = 0x00;
    g_variant_get (parameters, "(u)", &id);

    switch (id){
      case PARAM_GET_DRIVER_VERSION:
      case PARAM_GET_NEONENABLED:
      case PARAM_GET_ENABLED:
      case PARAM_GET_DRVCANWORK:
      case PARAM_GET_EFFECT_TYPE:
      case PARAM_GET_SAMPLINGRATE:
      case PARAM_GET_CONVKNLID:
        g_mutex_lock (&intf->lock);
        g_dbus_method_invocation_return_value (invocation,
                 g_variant_new ("(i)",
                   viperfx_command_get_px4_vx4x1(intf->vfx,id)));
        g_mutex_unlock (&intf->lock);
        break;
      default:
        g_dbus_method_invocation_return_value (invocation,
                                               g_variant_new ("(i)", -99));
    }

  }
  else if (g_strcmp0 (method_name, "CommitProperties") == 0)
  {
    guint32 ret = 0;
    if(intf->vfx == NULL)
      ret = 1;
    else if(user->sync_all_parameters_fun == NULL)
      ret = 2;
    else
      user->sync_all_parameters_fun(intf,PARAM_GROUP_ALL);

    if(ret == 0) g_dbus_connection_emit_signal (connection,
                                   NULL,
                                   object_path,
                                   interface_name,
                                   "PropertiesCommitted",
                                   g_variant_new ("(u)", PARAM_GROUP_ALL),
                                   NULL);

    g_dbus_method_invocation_return_value (invocation,
                                           g_variant_new ("(u)", ret));
  }
  else if (g_strcmp0 (method_name, "CommitPropertyGroups") == 0)
  {
    guint32 bitmask = 0x0;
    g_variant_get (parameters, "(u)", &bitmask);
    guint32 ret = 0;

    if(intf->vfx == NULL)
      ret = 1;
    else if(user->sync_all_parameters_fun == NULL)
      ret = 2;
    else if(bitmask > 0x1FFFF)
      ret = 3;
    else
      user->sync_all_parameters_fun(intf,(PARAM_GROUP)bitmask);

    if(ret == 0) g_dbus_connection_emit_signal (connection,
                                   NULL,
                                   object_path,
                                   interface_name,
                                   "PropertiesCommitted",
                                   g_variant_new ("(u)", bitmask),
                                   NULL);

    g_dbus_method_invocation_return_value (invocation,
                                           g_variant_new ("(u)", ret));
  }
  else if (g_strcmp0 (method_name, "PlayTestTone") == 0)
  {
    guint32 freq = 0x0;
    guint32 dur = 0x0;
    g_variant_get (parameters, "(uu)", &freq, &dur);
    if(dur > 200000) dur = 200000;
    intf->sine_duration = dur;
    intf->sine_sample_counter = 0;
    intf->sine_frequency = freq;
    g_dbus_method_invocation_return_value (invocation,
                                           g_variant_new ("(u)", 0));

  }
}

static GVariant *
handle_get_property (GDBusConnection  *connection,
                     const gchar      *sender,
                     const gchar      *object_path,
                     const gchar      *interface_name,
                     const gchar      *property_name,
                     GError          **error,
                     gpointer          user_data)
{
  userdata_t *user = user_data;
  Gstviperfx *intf = user->intf;

  GVariant *ret;

  ret = NULL;

  if (g_strcmp0 (property_name, "agc_enable") == 0)
    ret = g_variant_new_boolean (intf->agc_enabled);
  else if (g_strcmp0 (property_name, "agc_maxgain") == 0)
    ret = g_variant_new_int32 (intf->agc_maxgain);
  else if (g_strcmp0 (property_name, "agc_ratio") == 0)
    ret = g_variant_new_int32 (intf->agc_ratio);
  else if (g_strcmp0 (property_name, "agc_volume") == 0)
    ret = g_variant_new_int32 (intf->agc_volume);

  else if (g_strcmp0 (property_name, "ax_enable") == 0)
    ret = g_variant_new_boolean (intf->ax_enabled);
  else if (g_strcmp0 (property_name, "ax_mode") == 0)
    ret = g_variant_new_int32 (intf->ax_mode);

  else if (g_strcmp0 (property_name, "colm_enable") == 0)
    ret = g_variant_new_boolean (intf->colm_enabled);
  else if (g_strcmp0 (property_name, "colm_depth") == 0)
    ret = g_variant_new_int32 (intf->colm_depth);
  else if (g_strcmp0 (property_name, "colm_midimage") == 0)
    ret = g_variant_new_int32 (intf->colm_midimage);
  else if (g_strcmp0 (property_name, "colm_widening") == 0)
    ret = g_variant_new_int32 (intf->colm_widening);

  else if (g_strcmp0 (property_name, "conv_enable") == 0)
    ret = g_variant_new_boolean (intf->conv_enabled);
  else if (g_strcmp0 (property_name, "conv_cc_level") == 0)
    ret = g_variant_new_int32 (intf->conv_cc_level);
  else if (g_strcmp0 (property_name, "conv_ir_path") == 0)
    ret = g_variant_new_string (intf->conv_ir_path);

  else if (g_strcmp0 (property_name, "cure_enable") == 0)
    ret = g_variant_new_boolean (intf->cure_enabled);
  else if (g_strcmp0 (property_name, "cure_level") == 0)
    ret = g_variant_new_int32 (intf->cure_level);

  else if (g_strcmp0 (property_name, "ds_enable") == 0)
    ret = g_variant_new_boolean (intf->ds_enabled);
  else if (g_strcmp0 (property_name, "ds_level") == 0)
    ret = g_variant_new_int32 (intf->ds_level);

  else if (g_strcmp0 (property_name, "dynsys_enable") == 0)
    ret = g_variant_new_boolean (intf->dynsys_enabled);
  else if (g_strcmp0 (property_name, "dynsys_bassgain") == 0)
    ret = g_variant_new_int32 (intf->dynsys_bassgain);
  else if (g_strcmp0 (property_name, "dynsys_sidegain1") == 0)
    ret = g_variant_new_int32 (intf->dynsys_sidegain);
  else if (g_strcmp0 (property_name, "dynsys_sidegain2") == 0)
    ret = g_variant_new_int32 (intf->dynsys_sidegain2);
  else if (g_strcmp0 (property_name, "dynsys_xcoeff1") == 0)
    ret = g_variant_new_int32 (intf->dynsys_xcoeffs);
  else if (g_strcmp0 (property_name, "dynsys_xcoeff2") == 0)
    ret = g_variant_new_int32 (intf->dynsys_xcoeffs2);
  else if (g_strcmp0 (property_name, "dynsys_ycoeff1") == 0)
    ret = g_variant_new_int32 (intf->dynsys_ycoeffs);
  else if (g_strcmp0 (property_name, "dynsys_ycoeff2") == 0)
    ret = g_variant_new_int32 (intf->dynsys_ycoeffs2);

  else if (g_strcmp0 (property_name, "eq_enable") == 0)
    ret = g_variant_new_boolean (intf->eq_enabled);
  else if (g_strcmp0 (property_name, "eq_band1") == 0)
    ret = g_variant_new_int32 (intf->eq_band_level[0]);
  else if (g_strcmp0 (property_name, "eq_band2") == 0)
    ret = g_variant_new_int32 (intf->eq_band_level[1]);
  else if (g_strcmp0 (property_name, "eq_band3") == 0)
    ret = g_variant_new_int32 (intf->eq_band_level[2]);
  else if (g_strcmp0 (property_name, "eq_band4") == 0)
    ret = g_variant_new_int32 (intf->eq_band_level[3]);
  else if (g_strcmp0 (property_name, "eq_band5") == 0)
    ret = g_variant_new_int32 (intf->eq_band_level[4]);
  else if (g_strcmp0 (property_name, "eq_band6") == 0)
    ret = g_variant_new_int32 (intf->eq_band_level[5]);
  else if (g_strcmp0 (property_name, "eq_band7") == 0)
    ret = g_variant_new_int32 (intf->eq_band_level[6]);
  else if (g_strcmp0 (property_name, "eq_band8") == 0)
    ret = g_variant_new_int32 (intf->eq_band_level[7]);
  else if (g_strcmp0 (property_name, "eq_band9") == 0)
    ret = g_variant_new_int32 (intf->eq_band_level[8]);
  else if (g_strcmp0 (property_name, "eq_band10") == 0)
    ret = g_variant_new_int32 (intf->eq_band_level[9]);

  else if (g_strcmp0 (property_name, "fetcomp_enable") == 0)
    ret = g_variant_new_boolean (intf->fetcomp_enabled);
  else if (g_strcmp0 (property_name, "fetcomp_autoattack") == 0)
    ret = g_variant_new_boolean (intf->fetcomp_autoattack);
  else if (g_strcmp0 (property_name, "fetcomp_autogain") == 0)
    ret = g_variant_new_boolean (intf->fetcomp_autogain);
  else if (g_strcmp0 (property_name, "fetcomp_autoknee") == 0)
    ret = g_variant_new_boolean (intf->fetcomp_autoknee);
  else if (g_strcmp0 (property_name, "fetcomp_autorelease") == 0)
    ret = g_variant_new_boolean (intf->fetcomp_autorelease);
  else if (g_strcmp0 (property_name, "fetcomp_noclip") == 0)
    ret = g_variant_new_boolean (intf->fetcomp_noclip);

  else if (g_strcmp0 (property_name, "fetcomp_attack") == 0)
    ret = g_variant_new_int32 (intf->fetcomp_attack);
  else if (g_strcmp0 (property_name, "fetcomp_gain") == 0)
    ret = g_variant_new_int32 (intf->fetcomp_gain);
  else if (g_strcmp0 (property_name, "fetcomp_kneewidth") == 0)
    ret = g_variant_new_int32 (intf->fetcomp_kneewidth);
  else if (g_strcmp0 (property_name, "fetcomp_meta_adapt") == 0)
    ret = g_variant_new_int32 (intf->fetcomp_meta_adapt);
  else if (g_strcmp0 (property_name, "fetcomp_meta_crest") == 0)
    ret = g_variant_new_int32 (intf->fetcomp_meta_crest);
  else if (g_strcmp0 (property_name, "fetcomp_meta_kneemulti") == 0)
    ret = g_variant_new_int32 (intf->fetcomp_meta_kneemulti);
  else if (g_strcmp0 (property_name, "fetcomp_meta_maxattack") == 0)
    ret = g_variant_new_int32 (intf->fetcomp_meta_maxattack);
  else if (g_strcmp0 (property_name, "fetcomp_meta_maxrelease") == 0)
    ret = g_variant_new_int32 (intf->fetcomp_meta_maxrelease);
  else if (g_strcmp0 (property_name, "fetcomp_ratio") == 0)
    ret = g_variant_new_int32 (intf->fetcomp_ratio);
  else if (g_strcmp0 (property_name, "fetcomp_release") == 0)
    ret = g_variant_new_int32 (intf->fetcomp_release);
  else if (g_strcmp0 (property_name, "fetcomp_threshold") == 0)
    ret = g_variant_new_int32 (intf->fetcomp_threshold);

  else if (g_strcmp0 (property_name, "fx_enable") == 0)
    ret = g_variant_new_boolean (intf->fx_enabled);

  else if (g_strcmp0 (property_name, "lim_threshold") == 0)
    ret = g_variant_new_int32 (intf->lim_threshold);
  else if (g_strcmp0 (property_name, "out_pan") == 0)
    ret = g_variant_new_int32 (intf->out_pan);
  else if (g_strcmp0 (property_name, "out_volume") == 0)
    ret = g_variant_new_int32 (intf->out_volume);

  else if (g_strcmp0 (property_name, "reverb_enable") == 0)
    ret = g_variant_new_boolean (intf->reverb_enabled);
  else if (g_strcmp0 (property_name, "reverb_damp") == 0)
    ret = g_variant_new_int32 (intf->reverb_damp);
  else if (g_strcmp0 (property_name, "reverb_dry") == 0)
    ret = g_variant_new_int32 (intf->reverb_dry);
  else if (g_strcmp0 (property_name, "reverb_roomsize") == 0)
    ret = g_variant_new_int32 (intf->reverb_roomsize);
  else if (g_strcmp0 (property_name, "reverb_wet") == 0)
    ret = g_variant_new_int32 (intf->reverb_wet);
  else if (g_strcmp0 (property_name, "reverb_width") == 0)
    ret = g_variant_new_int32 (intf->reverb_width);

  else if (g_strcmp0 (property_name, "tube_enable") == 0)
    ret = g_variant_new_boolean (intf->tube_enabled);

  else if (g_strcmp0 (property_name, "vb_enable") == 0)
    ret = g_variant_new_boolean (intf->vb_enabled);
  else if (g_strcmp0 (property_name, "vb_freq") == 0)
    ret = g_variant_new_int32 (intf->vb_freq);
  else if (g_strcmp0 (property_name, "vb_gain") == 0)
    ret = g_variant_new_int32 (intf->vb_gain);
  else if (g_strcmp0 (property_name, "vb_mode") == 0)
    ret = g_variant_new_int32 (intf->vb_mode);

  else if (g_strcmp0 (property_name, "vc_enable") == 0)
    ret = g_variant_new_boolean (intf->vc_enabled);
  else if (g_strcmp0 (property_name, "vc_level") == 0)
    ret = g_variant_new_int32 (intf->vc_level);
  else if (g_strcmp0 (property_name, "vc_mode") == 0)
    ret = g_variant_new_int32 (intf->vc_mode);

  else if (g_strcmp0 (property_name, "vhe_enable") == 0)
    ret = g_variant_new_boolean (intf->vhe_enabled);
  else if (g_strcmp0 (property_name, "vhe_level") == 0)
    ret = g_variant_new_int32 (intf->vhe_level);

  else if (g_strcmp0 (property_name, "vse_enable") == 0)
    ret = g_variant_new_boolean (intf->vse_enabled);
  else if (g_strcmp0 (property_name, "vse_bark_cons") == 0)
    ret = g_variant_new_int32 (intf->vse_bark_cons);
  else if (g_strcmp0 (property_name, "vse_ref_bark") == 0)
    ret = g_variant_new_int32 (intf->vse_ref_bark);

  return ret;
}

static void set_string_property(GDBusConnection  *connection,
                                const gchar      *object_path,
                                const gchar      *interface_name,
                                const gchar      *property_name,
                                GVariant         *value,
                                const gchar      *propertyToBeSet,
                                gchar           **referenceToProp){
  if (g_strcmp0 (property_name, propertyToBeSet) == 0)
  {
    if (g_strcmp0 (*referenceToProp, g_variant_get_string (value, NULL)) != 0)
    {
      GVariantBuilder *builder;

      *referenceToProp = g_variant_dup_string (value, NULL);
      builder = g_variant_builder_new (G_VARIANT_TYPE_ARRAY);
      g_variant_builder_add (builder,
                             "{sv}",
                             propertyToBeSet,
                             g_variant_new_string (*referenceToProp));
      GError *local_error;
      local_error = NULL;
      g_dbus_connection_emit_signal (connection,
                                     NULL,
                                     object_path,
                                     "org.freedesktop.DBus.Properties",
                                     "PropertiesChanged",
                                     g_variant_new ("(sa{sv}as)",
                                                    interface_name,
                                                    builder,
                                                    NULL),
                                     &local_error);
      g_assert_no_error (local_error);
    }
  }
}

static void set_int32_property(GDBusConnection  *connection,
                               const gchar      *object_path,
                               const gchar      *interface_name,
                               const gchar      *property_name,
                               GVariant         *value,
                               const gchar      *propertyToBeSet,
                               gint32           *referenceToProp){
  if (g_strcmp0 (property_name, propertyToBeSet) == 0)
  {
    if (*referenceToProp != g_variant_get_int32 (value))
    {
      GVariantBuilder *builder;

      *referenceToProp = g_variant_get_int32(value);

      builder = g_variant_builder_new (G_VARIANT_TYPE_ARRAY);
      g_variant_builder_add (builder,
                             "{iv}",
                             propertyToBeSet,
                             g_variant_new_int32 (*referenceToProp));
      GError *local_error;
      local_error = NULL;
      g_dbus_connection_emit_signal (connection,
                                     NULL,
                                     object_path,
                                     "org.freedesktop.DBus.Properties",
                                     "PropertiesChanged",
                                     g_variant_new ("(sa{iv}as)",
                                                    interface_name,
                                                    builder,
                                                    NULL),
                                     &local_error);
      g_assert_no_error (local_error);
    }
  }
}

static void set_bool_property (GDBusConnection  *connection,
                               const gchar      *object_path,
                               const gchar      *interface_name,
                               const gchar      *property_name,
                               GVariant         *value,
                               const gchar      *propertyToBeSet,
                               gboolean         *referenceToProp){
  if (g_strcmp0 (property_name, propertyToBeSet) == 0)
  {
    if (*referenceToProp != g_variant_get_boolean(value))
    {
      GVariantBuilder *builder;

      *referenceToProp = g_variant_get_boolean(value);

      builder = g_variant_builder_new (G_VARIANT_TYPE_ARRAY);
      g_variant_builder_add (builder,
                             "{bv}",
                             propertyToBeSet,
                             g_variant_new_int32 (*referenceToProp));
      GError *local_error;
      local_error = NULL;
      g_dbus_connection_emit_signal (connection,
                                     NULL,
                                     object_path,
                                     "org.freedesktop.DBus.Properties",
                                     "PropertiesChanged",
                                     g_variant_new ("(sa{bv}as)",
                                                    interface_name,
                                                    builder,
                                                    NULL),
                                     &local_error);
      g_assert_no_error (local_error);
    }
  }
}

static gboolean
handle_set_property (GDBusConnection  *connection,
                     const gchar      *sender,
                     const gchar      *object_path,
                     const gchar      *interface_name,
                     const gchar      *property_name,
                     GVariant         *value,
                     GError          **error,
                     gpointer          user_data)
{
  userdata_t *user = user_data;
  Gstviperfx *intf = user->intf;

  set_bool_property(connection, object_path, interface_name
    , property_name, value, "agc_enable", &intf->agc_enabled);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "agc_maxgain", &intf->agc_maxgain);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "agc_ratio", &intf->agc_ratio);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "agc_volume", &intf->agc_volume);

  set_bool_property(connection, object_path, interface_name
    , property_name, value, "ax_enable", &intf->ax_enabled);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "ax_mode", &intf->ax_mode);

  set_bool_property(connection, object_path, interface_name
    , property_name, value, "colm_enable", &intf->colm_enabled);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "colm_depth", &intf->colm_depth);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "colm_midimage", &intf->colm_midimage);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "colm_widening", &intf->colm_widening);

  set_bool_property(connection, object_path, interface_name
    , property_name, value, "conv_enable", &intf->conv_enabled);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "conv_cc_level", &intf->conv_cc_level);

  set_string_property(connection,object_path,interface_name
    ,property_name,value,"conv_ir_path", &intf->conv_ir_path);

  set_bool_property(connection, object_path, interface_name
    , property_name, value, "cure_enable", &intf->cure_enabled);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "cure_level", &intf->cure_level);

  set_bool_property(connection, object_path, interface_name
    , property_name, value, "ds_enable", &intf->ds_enabled);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "ds_level", &intf->ds_level);

  set_bool_property(connection, object_path, interface_name
    , property_name, value, "dynsys_enable", &intf->dynsys_enabled);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "dynsys_bassgain", &intf->dynsys_bassgain);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "dynsys_sidegain1", &intf->dynsys_sidegain);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "dynsys_sidegain2", &intf->dynsys_sidegain2);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "dynsys_xcoeff1", &intf->dynsys_xcoeffs);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "dynsys_xcoeff2", &intf->dynsys_xcoeffs2);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "dynsys_ycoeff1", &intf->dynsys_ycoeffs);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "dynsys_ycoeff2", &intf->dynsys_ycoeffs2);

  set_bool_property(connection, object_path, interface_name
    , property_name, value, "eq_enable", &intf->eq_enabled);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "eq_band1", &intf->eq_band_level[0]);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "eq_band2", &intf->eq_band_level[1]);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "eq_band3", &intf->eq_band_level[2]);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "eq_band4", &intf->eq_band_level[3]);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "eq_band5", &intf->eq_band_level[4]);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "eq_band6", &intf->eq_band_level[5]);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "eq_band7", &intf->eq_band_level[6]);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "eq_band8", &intf->eq_band_level[7]);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "eq_band9", &intf->eq_band_level[8]);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "eq_band10", &intf->eq_band_level[9]);

  set_bool_property(connection, object_path, interface_name
    , property_name, value, "fetcomp_enable", &intf->fetcomp_enabled);
  set_bool_property(connection, object_path, interface_name
    , property_name, value, "fetcomp_autoattack", &intf->fetcomp_autoattack);
  set_bool_property(connection, object_path, interface_name
    , property_name, value, "fetcomp_autogain", &intf->fetcomp_autogain);
  set_bool_property(connection, object_path, interface_name
    , property_name, value, "fetcomp_autoknee", &intf->fetcomp_autoknee);
  set_bool_property(connection, object_path, interface_name
    , property_name, value, "fetcomp_autorelease", &intf->fetcomp_autorelease);
  set_bool_property(connection, object_path, interface_name
    , property_name, value, "fetcomp_noclip", &intf->fetcomp_noclip);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "fetcomp_attack", &intf->fetcomp_attack);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "fetcomp_gain", &intf->fetcomp_gain);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "fetcomp_kneewidth", &intf->fetcomp_kneewidth);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "fetcomp_meta_adapt", &intf->fetcomp_meta_adapt);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "fetcomp_meta_crest", &intf->fetcomp_meta_crest);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "fetcomp_meta_kneemulti", &intf->fetcomp_meta_kneemulti);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "fetcomp_meta_maxattack", &intf->fetcomp_meta_maxattack);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "fetcomp_meta_maxrelease", &intf->fetcomp_meta_maxrelease);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "fetcomp_kneewidth", &intf->fetcomp_kneewidth);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "fetcomp_ratio", &intf->fetcomp_ratio);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "fetcomp_release", &intf->fetcomp_release);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "fetcomp_threshold", &intf->fetcomp_threshold);

  set_bool_property(connection, object_path, interface_name
    , property_name, value, "fx_enable", &intf->fx_enabled);

  set_int32_property(connection, object_path, interface_name
    , property_name, value, "lim_threshold", &intf->lim_threshold);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "out_pan", &intf->out_pan);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "out_volume", &intf->out_volume);

  set_bool_property(connection, object_path, interface_name
    , property_name, value, "reverb_enable", &intf->reverb_enabled);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "reverb_damp", &intf->reverb_damp);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "reverb_dry", &intf->reverb_dry);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "reverb_roomsize", &intf->reverb_roomsize);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "reverb_wet", &intf->reverb_wet);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "reverb_width", &intf->reverb_width);

  set_bool_property(connection, object_path, interface_name
    , property_name, value, "tube_enable", &intf->tube_enabled);

  set_bool_property(connection, object_path, interface_name
    , property_name, value, "vb_enable", &intf->vb_enabled);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "vb_freq", &intf->vb_freq);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "vb_gain", &intf->vb_gain);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "vb_mode", &intf->vb_mode);

  set_bool_property(connection, object_path, interface_name
    , property_name, value, "vc_enable", &intf->vc_enabled);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "vc_level", &intf->vc_level);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "vc_mode", &intf->vc_mode);

  set_bool_property(connection, object_path, interface_name
    , property_name, value, "vhe_enable", &intf->vhe_enabled);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "vhe_level", &intf->vhe_level);

  set_bool_property(connection, object_path, interface_name
    , property_name, value, "vse_enable", &intf->vse_enabled);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "vse_bark_cons", &intf->vse_bark_cons);
  set_int32_property(connection, object_path, interface_name
    , property_name, value, "vse_ref_bark", &intf->vse_ref_bark);

  return *error == NULL;
}

static const GDBusInterfaceVTable interface_vtable =
  {
    handle_method_call,
    handle_get_property,
    handle_set_property
  };

/* ---------------------------------------------------------------------------------------------------- */

static void
on_bus_acquired (GDBusConnection *connection,
                 const gchar     *name,
                 gpointer         user_data)
{
  guint registration_id;

  registration_id = g_dbus_connection_register_object (connection,
                                                       "/me/noahbliss/ViperFx",
                                                       introspection_data->interfaces[0],
                                                       &interface_vtable,
                                                       user_data,  /* user_data */
                                                       NULL,  /* user_data_free_func */
                                                       NULL); /* GError** */
  if(registration_id <= 0)
    printf("[W] DBus server: invalid registration id\n");
}

static void
on_name_acquired (GDBusConnection *connection,
                  const gchar     *name,
                  gpointer         user_data)
{
  printf("[I] DBus server: bus name acquired\n");
}

static void
on_name_lost (GDBusConnection *connection,
              const gchar     *name,
              gpointer         user_data)
{
  printf("[W] DBus server: bus name lost\n");
}

void
init_dbus_server(void *viperfx_ref, void (*sync_all_parameters_fun)()) {
  guint owner_id;
  userdata_t* user =                malloc(sizeof(struct userdata_s));
  user->intf =                      (Gstviperfx*)viperfx_ref;
  user->sync_all_parameters_fun =   sync_all_parameters_fun;

  introspection_data = g_dbus_node_info_new_for_xml(introspection_xml, NULL);
  if (introspection_data == NULL){
    printf("[E] DBus server: introspection data is null\n");
  }

  owner_id = g_bus_own_name(G_BUS_TYPE_SESSION,
                            "me.noahbliss.ViperFx",
                            G_BUS_NAME_OWNER_FLAGS_NONE,
                            on_bus_acquired,
                            on_name_acquired,
                            on_name_lost,
                            user,
                            NULL);

  user->intf->dbus_owner_id = owner_id;
}

void
shutdown_dbus_server(guint owner_id){
  g_bus_unown_name(owner_id);
  g_dbus_node_info_unref(introspection_data);
}