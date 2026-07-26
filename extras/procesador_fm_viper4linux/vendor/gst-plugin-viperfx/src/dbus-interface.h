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
#ifndef DBUS_INTERFACE_H
#define DBUS_INTERFACE_H
#include <gio/gio.h>
#include <stdlib.h>
#include <unistd.h>
#include "gstviperfx.h"

typedef struct userdata_s {
  Gstviperfx *intf;
  void (*sync_all_parameters_fun)(Gstviperfx*,PARAM_GROUP);
} userdata_t;

void init_dbus_server(void *viperfx_ref, void (*saf_fun_ref)());
void shutdown_dbus_server (guint  owner_id);

#endif //DBUS_INTERFACE_H
