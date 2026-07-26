# ViperFX D-Bus Documentation

Table of Contents

- [Introduction](#introduction)
- [Structure](#structure)
- [Methods](#methods)
  - [CommitProperties()](#commitproperties)
  - [CommitPropertyGroups(UInt32 bitmask)](#commitpropertygroupsuint32-bitmask)
  - [GetAllowedCapabilities()](#getallowedcapabilities)
  - [GetGstVersion()](#getgstversion)
  - [GetVersion()](#getversion)
  - [GetPackageName()](#getpackagename)
  - [GetDriverStatus(UInt32 id)](#getdriverstatusuint32-id)
  - [PlayTestTone(UInt32 freq, UInt32 dur)](#playtesttoneuint32-freq-uint32-dur)
- [Signals](#signals)
  - [PropertiesCommitted(UInt32 bitmask)](#propertiescommitteduint32-bitmask)
- [Shell (Examples)](#shell)
  - [Reading properties](#reading-properties)
  - [Writing properties](#writing-properties)
  - [Calling methods](#calling-methods)

## Introduction

D-BUS is an interprocess communication (IPC) system, providing a simple yet powerful mechanism allowing applications to talk to one another, communicate information and request services.

An overview of D-Bus can be found at http://dbus.freedesktop.org/.

## Structure

A typical D-Bus service consists of interfaces, methods and properties. In order to keep this D-Bus interface as simple as possible, I decided to go with a single interface containing all important methods and properties.

You can find further information about these methods and properties in the next section. The graph below should give you an approximate overview of this interface.

```
me.noahbliss.ViperFx (Interface)
|
+ - + Methods
|   |
|   + CommitProperties()                    -> (UInt32 response)
|   + CommitPropertyGroups(UInt32 bitmask)  -> (UInt32 response)
|   + GetAllowedCapabilities()              -> (String response)
|   + GetGstVersion()                       -> (String response)
|   + GetVersion()                          -> (String response)
|   + GetPackageName()                      -> (String response)
|   + GetDriverStatus(UInt32 id)            -> (Int32  response)
|   L PlayTestTone(UInt32 freq, UInt32 dur) -> (UInt32 response)
|
+ - + Signals
|   |
|   L PropertiesCommitted(UInt32 bitmask)
|
+ - + Properties
    |
    + [Boolean/readwrite] agc_enable
    + [Int32/readwrite] agc_ratio
    + [Int32/readwrite] agc_maxgain
    ...
```

I won't include every property at this point but you should get the idea. Every parameter in the audio.conf file has a corresponding property with the same name and type.

## Methods

#### CommitProperties()

##### Usage

Once this method has been called, ViperFX core will be reloaded using the current values of all properties. You should call this method after you modified one or more properties in order to apply your changes.

##### Return value

Returns always an `UInt32` value.

| Return value | Description                                             |
| ------------ | ------------------------------------------------------- |
| 0            | Successfully updated                                    |
| 1            | Error: ViperFX Core not initialized                     |
| 2            | Error: Function pointer in `userdata_t` not initialized |

#### CommitPropertyGroups(UInt32 bitmask)

##### Usage

Alternative to  [`CommitProperties()`](#commitproperties). Instead of committing all properties, this method allows to select one or more property groups to be updated by providing a bitmask. 

##### Arguments

This method takes one  `UInt32` argument as an input. This value is a bitmask and describes the property group(s) to be reloaded.

| Internal name       | Bits              | Hex-Value | Description            |
| ------------------- | ----------------- | --------- | ---------------------- |
| PARAM_GROUP_NONE    | 00000000000000000 | 0x0000    | None                   |
| PARAM_GROUP_AGC     | 00000000000000001 | 0x0001    | Automatic Gain Control |
| PARAM_GROUP_AX      | 00000000000000010 | 0x0002    | AnalogX                |
| PARAM_GROUP_COLM    | 00000000000000100 | 0x0004    | Colorful Music         |
| PARAM_GROUP_CONV    | 00000000000001000 | 0x0008    | Convolver              |
| PARAM_GROUP_CURE    | 00000000000010000 | 0x0010    | Cure+                  |
| PARAM_GROUP_DS      | 00000000000100000 | 0x0020    | Differential Surround  |
| PARAM_GROUP_DYNSYS  | 00000000001000000 | 0x0040    | Dynamic System         |
| PARAM_GROUP_EQ      | 00000000010000000 | 0x0080    | FIR Equalizer          |
| PARAM_GROUP_FETCOMP | 00000000100000000 | 0x0100    | FET Compressor         |
| PARAM_GROUP_LIM     | 00000001000000000 | 0x0200    | Limiter                |
| PARAM_GROUP_MSWITCH | 00000010000000000 | 0x0400    | Master switch          |
| PARAM_GROUP_REVERB  | 00000100000000000 | 0x0800    | Reverb                 |
| PARAM_GROUP_TUBE    | 00001000000000000 | 0x1000    | Tube simulator         |
| PARAM_GROUP_VB      | 00010000000000000 | 0x2000    | ViPER Bass             |
| PARAM_GROUP_VC      | 00100000000000000 | 0x4000    | ViPER Clarity          |
| PARAM_GROUP_VHE     | 01000000000000000 | 0x8000    | Headphone Engine       |
| PARAM_GROUP_VSE     | 10000000000000000 | 0x10000   | Spectrum Extend        |
| PARAM_GROUP_ALL     | 11111111111111111 | 0x1FFFF   | All groups             |

**Combining two groups**

As an example, I will choose `PARAM_GROUP_EQ` and `PARAM_GROUP_COLM`.  In order to get a bitmask for these groups we will have to perform a bitwise AND operation on it:

```
PARAM_GROUP_COLM         00000000000000100                hex: 0x04
PARAM_GROUP_EQ         & 00000000010000000                hex: 0x80
                      --------------------
RESULT                   00000000010000100   -> dec: 84,  hex: 0x132
```

Now we just need to convert the result to an `UInt32` (in our case 84 or as hex: 0x132) and submit it.

##### Return value

Returns always an `UInt32` value.

| Return value | Description                                             |
| ------------ | ------------------------------------------------------- |
| 0            | Successfully updated                                    |
| 1            | Error: ViperFX Core not initialized                     |
| 2            | Error: Function pointer in `userdata_t` not initialized |
| 3            | Invalid bitmask (>0x1FFFF)                              |

#### GetAllowedCapabilities()

##### Usage

This method returns all audio processing capabilities of the gst plugin as a GStreamer-compatible string.

##### Return value

As described above, this method returns a value of type `String`.

#### GetGstVersion()

##### Usage

This method returns the current version of GStreamer.

##### Return value

Returns a version code formatted as `%d.%d.%d.%d` of type `String`.

#### GetVersion()

##### Usage

This method returns the current version of gst-plugin-viperfx.

##### Return value

Returns a version code formatted as `%d.%d.%d` of type `String`.

#### GetPackageName()

##### Usage

This method returns the internal package name of gst-plugin-viperfx. It is hard-coded and should always return "viperfx-plugin".

##### Return value

Returns a value of type `String`.

#### GetDriverStatus(UInt32 id)

##### Usage

This method provides information about the current driver state. It interacts directly with ViperFX core and can be used for various purposes.

##### Arguments

This method takes one  `UInt32` argument called "id" as an input. This value describes the type of status to be checked. You can submit following ids:

| Internal name            | ID (Hex) | ID (Dec) | Description                            |
| ------------------------ | -------- | -------- | -------------------------------------- |
| PARAM_GET_DRIVER_VERSION | 0x8001   | 32769    | Returns driver version as hex string   |
| PARAM_GET_NEONENABLED    | 0x8002   | 32770    | (Unused on Linux, returns always zero) |
| PARAM_GET_ENABLED        | 0x8003   | 32771    | Driver enabled? Returns 0 or 1         |
| PARAM_GET_DRVCANWORK     | 0x8004   | 32772    | Driver processing? Returns 0 or 1      |
| PARAM_GET_EFFECT_TYPE    | 0x8005   | 32773    | Returns current effect type            |
| PARAM_GET_SAMPLINGRATE   | 0x8006   | 32774    | Returns current samplerate             |
| PARAM_GET_CONVKNLID      | 0x8007   | 32775    | (Unused on Linux, returns always zero) |

##### Notes on *PARAM_GET_NEONENABLED*:

On Android, this would check whether the processor has [NEON capabilities](https://www.arm.com/why-arm/technologies/neon) (audio/video acceleration). However, NEON is only available on ARM platforms and therefore this parameter always returns 0. 

##### Notes on *PARAM_GET_EFFECT_TYPE*:

As you might know, Viper4Android has a special speaker mode. This mode is also available on Linux but was never implemented. `PARAM_GET_EFFECT_TYPE` would return the currently selected effect type (either headphone or speaker mode) but since only headphone mode is available at the moment, it will always return 1.

| Internal name           | Return value | Description     |
| ----------------------- | ------------ | --------------- |
| ViPER_FX_TYPE_NONE      | 0            | Not initialized |
| ViPER_FX_TYPE_HEADPHONE | 1            | Headphone mode  |
| ViPER_FX_TYPE_SPEAKER   | 2            | Speaker mode    |

##### Notes on *PARAM_GET_DRIVER_VERSION*:

This parameter will return the driver version as an oddly formatted hex sequence, so here is a quick example to avoid confusion:

```
Returned value: 0x2050004
Actual version:   2.5.0.4
```

##### Notes on *PARAM_GET_CONVKNLID*:

This parameter (also known as 'convolver kernel id') should return the id of the impulse response which is currently loaded. Normally this id is a hash of the actual convolver data. On Linux, however, it seems to return zero regardless of whether an IRS is loaded or not.

##### Return value

Returns always an `Int32` value. The meaning of this return value can differ, depending on what `id` has been used to call this method.

A negative return value is an error code, in this case please refer to the table below:

| Return value | Error-Description                               |
| ------------ | ----------------------------------------------- |
| -1           | ViperFX Core was unable to process your request |
| -2           | Empty response                                  |
| -3           | Invalid response size                           |
| -99          | Invalid id                                      |

#### PlayTestTone(UInt32 freq, UInt32 dur)

##### Usage

Plays a sine tone at `freq` Hz for `dur` samples, useful for troubleshooting GStreamer pipeline issues. All incoming PCM stream data will be overwritten while this test tone is being played back. Parameter `dur` describes the length of the tone in samples and is limited to a maximum of 200000 samples.

##### Return value

Returns always null of type `UInt32`.

## Signals

#### PropertiesCommitted(UInt32 bitmask)

##### Usage

This signal is emitted once another process has called [`CommitPropertyGroups`](#commitpropertygroupsuint32-bitmask) or [`CommitProperties`](#commitproperties).

##### Return value

Returns a bitmask as `UInt32`  containing information about all property groups which were committed. Refer to [`CommitPropertyGroups`](#commitpropertygroupsuint32-bitmask) for more information about the specifications of this bitmask.

## Shell

In this tutorial, we'll be interacting with the D-Bus interface using `dbus-send` since pretty much every machine should have it preinstalled.

Commands using `dbus-send` are usually structured like this:

```bash
dbus-send --dest=<Destination-interface> --print-reply <Object-path> <Method> [Parameters]
```

In our case:

| Placeholder           | Value                 |
| --------------------- | --------------------- |
| Destination-interface | me.noahbliss.ViperFx  |
| Object-path           | /me/noahbliss/ViperFx |

__Note: __`dbus-send` will not only return the response sent by this dbus interface, but also various technical information about the message transmission. If you want to extract the actual response you could do something like in [this stackoverflow thread](https://stackoverflow.com/a/27001053/11559090).

#### Reading properties

In order to read properties, we'll need to use the predefined `org.freedesktop.DBus.Properties.Get` method. It takes two string arguments: the first one is the target interface (in our case always `me.noahbliss.ViperFx`) and the second one describes the name of the property to be read.

**Example:** Read a 32-bit integer property (`dynsys_bassgain`)

```bash
dbus-send --dest=me.noahbliss.ViperFx --print-reply /me/noahbliss/ViperFx \
 org.freedesktop.DBus.Properties.Get string:me.noahbliss.ViperFx string:dynsys_bassgain
```

#### Writing properties

In order to write properties, we'll need to use the predefined `org.freedesktop.DBus.Properties.Set` method. It takes two string arguments and one "variant" argument: the first string parameter describes the target interface (in our case always `me.noahbliss.ViperFx`) and the second one is the name of the property to be set. The third parameter defines the new value and is a so-called flexible "variant" type. Have a look at the examples below to see how these are defined.

**Example:** Write a 32-bit integer property (set `dynsys_bassgain` to 100%)

```bash
dbus-send --dest=me.noahbliss.ViperFx --print-reply /me/noahbliss/ViperFx \
 org.freedesktop.DBus.Properties.Set string:me.noahbliss.ViperFx string:dynsys_bassgain variant:int32:100
```

**Example:** Write a boolean property (set `fx_enabled` to false)

```bash
dbus-send --dest=me.noahbliss.ViperFx --print-reply /me/noahbliss/ViperFx \
 org.freedesktop.DBus.Properties.Set string:me.noahbliss.ViperFx string:fx_enabled variant:boolean:false
```

**Example:** Write a string property (set `conv_ir_path` to "/home/user/conv.irs")

```bash
dbus-send --dest=me.noahbliss.ViperFx --print-reply /me/noahbliss/ViperFx \
 org.freedesktop.DBus.Properties.Set string:me.noahbliss.ViperFx string:conv_ir_path variant:string:"/home/user/conv.irs"
```

**Note:** Keep in mind that you must call [`CommitProperties()`](#commitproperties) for your changes to take effect.

#### Calling methods

In order to call methods using `dbus-send`, you must structure a command like this:

```bash
dbus-send --dest=me.noahbliss.ViperFx --print-reply /me/noahbliss/ViperFx <Method> [Parameter1] [Parameter2] [Parameter...]
```

The number of parameters depends on the method to be called. Each parameter requires a type identifier as a prefix (unsigned integer: `uint32:10`, string: `string:"text"`).  

**Example:** Get version of gst-viperfx-plugin

```bash
dbus-send --dest=me.noahbliss.ViperFx --print-reply /me/noahbliss/ViperFx me.noahbliss.ViperFx.GetVersion
```

**Example:** Commit all properties

```bash
dbus-send --dest=me.noahbliss.ViperFx --print-reply /me/noahbliss/ViperFx me.noahbliss.ViperFx.CommitProperties
```

**Example:** Get current samplerate

```bash
dbus-send --dest=me.noahbliss.ViperFx --print-reply /me/noahbliss/ViperFx me.noahbliss.ViperFx.GetDriverStatus uint32:0x8006
```

**Example:** Commit `PARAM_GROUP_EQ` and `PARAM_GROUP_COLM` property groups

```bash
dbus-send --dest=me.noahbliss.ViperFx --print-reply /me/noahbliss/ViperFx me.noahbliss.ViperFx.CommitPropertyGroups uint32:0x132
```

Refer to the methods section above for more information about [`GetDriverStatus`](#getdriverstatusuint32-id) and [`CommitPropertyGroups`](#commitpropertygroupsuint32-bitmask).

________

Written by [@ThePBone](https://github.com/ThePBone) *<tim.schneeberger(at)outlook.de>*

