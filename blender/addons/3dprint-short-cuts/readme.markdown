---
layout: page
title: Blender 3DPrint Short-Cuts
date: 2017-12-28 17:32:35 -0800
#categories: blender addons
---
{% include base.html %}
This add-on makes use of [`curl`][Curl-GitHub] & [`slic3r`][Slic3r-GitHub]
 or [`CuraEngine`][CuraEngine-GitHub] command line programs, please install
 these prior to testing features. Optionally install & configure an
 [OctoPrint][OctoPrint-GitHub] or [Repetier][Repetier-Docs] server on the same
 local network to make full use of all features. Additionally this addon makes use
 of the `Extra Objects` addon already available within Blender User Preferences,
 though users should manually enable it if not already enabled.


## TLDR


This add-on allows for turning a selection of object within Blender into either
 a single or multiple GCode files and auto-uploading of results to an OctoPrint
 or Repetier server.


## How To Playlist


<iframe width="560" height="315" src="https://www.youtube-nocookie.com/embed/videoseries?list=PLNK2xp3jRnJWgBBLHAg5iP8AUJfZp_jbv" frameborder="0" allow="autoplay; encrypted-media" allowfullscreen></iframe>


## Installation


0. Download the Python file [3DPrint Short-Cuts]({{ base }}/blender/addons/3dprint-short-cuts/3dprint_shortcuts.py)

0. Within Blender select 'File', then `User Preferences` or use the keyboard
 short-cut `Ctrl Alt U`

0. Within `Blender User Preferences` select the `Add-ons` tab, then search for
 the `Extra Objects` addon within `Blender User Preferences` and select the
 `Add Mesh: Extra Objects` addon for activation

0. Within `Blender User Preferences` select the `Add-ons` tab, then the
 `Install Add-on from File...` button

0. Within the `File Browser` Blender has now opened navigate to where your web
 browser downloaded the `3dprint_shortcuts.py` file, and either double-click the
 file or highlight it & select the `Install Add-on from file` button.

0. Within `Blender User Preferences` select the `User` (under the `Categories`
 tab) button and check the check-box for `Import-Export: 3DPrint Short-Cuts` addon.

0. Select the `Save User Settings` button if having this addon is of any use.

0. Within the main Blender window navigate to `Object Mode` within a `3D View`

0. With mouse pointer within the `3D View` area press `T` to open the `Tool Shelf`

0. Scroll allong the tabs within the `Tool Shelf` to find the one labled
 `3dprint_shortcuts` and select it

0. Customize various settings available, then use the `Quick Slicer Tools`,
 and if configured for a server such as OctoPrint or Repetier the
 `3D Print Server Actions` panels to direct Blender to take the prescribed actions;
 see the next section for more details.


## Configuration Options


### Local Slicer Settings


Under `Local Slicer Settings` panel, chose a preferred slicer then add a config file
 (`.ini` or `.json` respectively) for the type of printer available. Additional
 options for configurations will become available such as for Slic3r it is now
 possible to define a `Post Processing Script` to run immediately after generating
 GCode file(s) from selected objects exported by Blender.

> Note for Cura users; Cura & CuraEngine are separate applications with separate
> configuration file formats, in short if you've not already experienced the
> joys of writing/editing your own CuraEngine `.json` file then sticking with
> Slic3r for slicer options with this Blender addon is easier.
> That stated a generic [config file - fdmprinter.def.json](https://github.com/Ultimaker/Cura/blob/master/resources/definitions/fdmprinter.def.json)
> has been made available by the Cura team and depending upon source install
> options used there maybe more specific configs under
> `/usr/share/cura/CuraEngine` directory.

> Note for CuraEngine version 1 users, the `Extra Arguments` text field should allow
> for sending `key1=value1 key2=value2` formatted configurations, however, line-lengths
> within Python running within Blender are un-tested.

Select what directory GCode files will be save to if the Blender temporary directory
 is not desired as an output location.


### Export STL Settings


Under `Export STL Settings` panel choose weather selected objects are
 to be treated as `Individual`, or a `Batch` job, or if to `Merge` selected
 object with slicers locally.

> `Merge` is can be thought of as requesting the slicer to auto-arrange objects,
> where as `Batch` will cause Blender to export all selected objects as one file
> prior to slicing, and `Individual` treats each selected object as a separate
> print job.

Select an output directory and weather or not to keep temporary STL files after
 slicing &/or uploading operations if defaults are not satisfactory.


### Import OBJ Settings


Under `Import OBJ Settings` panel choose weather temporary OBJ files should be
 removed automatically & output directory if defaults are insufficient.


## Using addon's features


### Quick Slicer Tools


- The `Slic3r Repair Selected` button will export selected Blender objects
 to Slic3r and re-import *repaired* object files parented to named empty. This
 is to allow for previewing how the selected objects where interpreted, if
 results checkout then click the next button down to export the repaired object
 back into Slic3r for translating into GCode.

- `Prefered Local Slicer` menu allows for choosing if selected objects within Blender
 should be sent to either Slic3r or CuraEngine for translating into GCode files, and
 toggles visibility of the following two buttons

- The `Slic3r Slice Selected` button will export selected Blender objects to
 Slic3r for translating into GCode file(s). Note users should provide a config
 (`.ini`) file path to Blender under the `Slic3r Settings` panel if not using
 the original RepRap 3D printer.

- The `CuraEngine Slice Selected` button will export selected Blender objects
 to CuraEngine for translating into GCode file(s) and much like with Slic3r
 users should load in their config (`.json`) file within the related Settings
 panel.

- The `<OctoPrint/Repetier> Upload GCode` check-box controls if exporting selected
 objects through slicers for generating GCode will also be automatically uploaded
 to the configured server or not.

- The `View Raw GCode` check-box if checked will open generated GCode files within
 Blender's `Text Editor` (hint; the `Scripting` layout under `Choose Screen layout`
 menu is a handy way of getting to an open text editor pain) and is intended to
 allow users to verify that settings from slicer configurations are in use.

- The `Open Browser After Upload` check-box under if checked will open a web browser
 pointed at the server uploaded to after operations have finished.


### Print Server Actions


- The `Preview Build Plate` & `Stream Build Plate` button do as advertised so long
 as Blender's game engine is not broken, and so long as configurations withing the
 `Webcam Settings` panel are correct.

- Currently OctoPrint server users will find more features available for interacting
 with a printer from within Blender, however, this may not be true in the future.


## Notes & tips


- Saving customization of session settings maybe achieved via `Ctrl U` keyboard
 short-cut or `File > Save Startup File`, however, this is not advisable if
 on a shared device.

- Hover over any tool or configuration to see default values (if any) and a
 description of what that portion of this addon maybe used for

- Use the buttons with `Quick Slicer Tools` panel to take actions on selected
 objects within Blender

- Note for OctoPrint & Repetier users; this add-on does **not** automatically
 print selected objects (yet) after uploading, please use a web browser or another
 option for interacting with the server for selecting which uploaded model
 should be printed & when.

- Note for OctoPrint users specifically; the `Server Slicer Settings` panel
 maybe used to upload selected objects from Blender as STL files for slicing server
 side, however, sending multiple files for slicing is not supported just yet.


## Other Blender addons that maybe of interest to users of this addon

> Note the following are only what could be found via web searching for 3rd
> party Blender addons related to 3D printing & GCode, and have not been tested
> by the authors of the above documented addon.


- [Blender GCode Reader](https://github.com/zignig/blender-gcode-reader)

- [BlenderCAM](https://blendercam.blogspot.com/p/blender-cam-description.html)

- [OctoBlend](https://github.com/CreativeTools/octoblend)


[CuraEngine-GitHub]: https://github.com/Ultimaker/CuraEngine
[Slic3r-GitHub]: https://github.com/alexrj/Slic3r
[Curl-GitHub]: https://github.com/curl/curl
[OctoPrint-GitHub]: https://github.com/foosel/OctoPrint
[Repetier-Docs]: https://www.repetier.com/#documantation
