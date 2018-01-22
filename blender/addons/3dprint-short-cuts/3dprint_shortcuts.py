#!/usr/bin/env python


#        Exports selected objects from Blender to various 3D slicing or printing applications or servers
#        Copyright (C) 2017  S0AndS0
#
#        This program is free software: you can redistribute it and/or modify
#        it under the terms of the GNU Affero General Public License as
#        published by the Free Software Foundation, version 3 of the License.
#
#        This program is distributed in the hope that it will be useful,
#        but WITHOUT ANY WARRANTY; without even the implied warranty of
#        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#        GNU Affero General Public License for more details.
#
#        You should have received a copy of the GNU Affero General Public License
#        along with this program.  If not, see <http://www.gnu.org/licenses/>.


bl_info = {
    "name": "3DPrint Short Cuts",
    "author": "S0AndS0",
    "version": (1, 5),
    "blender": (2, 75, 0),
    "location": "View3D > Tools > 3DPrint_Short_Cuts",
    "description": "Enables translation to GCode without leaving Blender & uploading to OctoPrint or Repetier server(s)",
    "warning": "Uses Curl for uploads, and Slic3r or CuraEngine for GCode translations. Untested on Mac & Win. ",
    "wiki_url": "https://s0ands0.github.io/3D_Printing/blender/addons/3dprint-short-cuts/readme.html",
    "category": "Import-Export",
}
## How to access above values latter within this script
#print(bl_info.get('name'))


#-------------------------------------------------------------------------
#    Import useful code
#-------------------------------------------------------------------------
import bpy
import os
import sys
import subprocess
import json

from bpy.types import (
    Operator,
    Panel,
    PropertyGroup)
from bpy.props import (
    BoolProperty,
    EnumProperty,
    StringProperty,
    IntProperty)


# Tip to future self; use 'Ctrl F' then 'Esc` to bring up find menu & exit from search
#  then under 'Properties' select 'Show Margin' & set 'Margin Column' to '120' to
#  ensure line lengths do not exced limits defined by https://wiki.blender.org/index.php/Dev:Doc/Code_Style
# Furthermore, prior to public pushes to any Git server check that code formatting is
#  compliant with PEP 8 https://www.python.org/dev/peps/pep-0008/

#-------------------------------------------------------------------------
#    Global variables for this add-on
#-------------------------------------------------------------------------
this_addons_name = bpy.path.display_name_from_filepath(__file__)

Target_render_engine = 'BLENDER_GAME'
Target_material_mode = 'GLSL'
Target_viewport_shade = 'TEXTURED'

if "lin" in sys.platform:
    slic3r_exec_name = 'slic3r'
    slic3r_exec_dir = ''
    curaengine_exec_dir = ''
    curaengine_exec_name = 'CuraEngine'
    curl_exec_dir = ''
    curl_exec_name = 'curl'
elif "win" in sys.platform:
    slic3r_exec_name = 'slic3r-console.exe'
    slic3r_exec_dir = ''
    curaengine_exec_dir = ''
    curaengine_exec_name = 'CuraEngine'
    curl_exec_dir = ''
    curl_exec_name = 'curl'
else:
    slic3r_exec_name = 'slic3r'
    slic3r_exec_dir = 'Slic3r.app/Contents/MacOS'
    curaengine_exec_dir = ''
    curaengine_exec_name = 'CuraEngine'
    curl_exec_dir = ''
    curl_exec_name = 'curl'


#-------------------------------------------------------------------------
#    Show default properties for active scene & define how the user should configure each
#-------------------------------------------------------------------------
class export_settings(PropertyGroup):
    Scene = bpy.types.Scene
    Scene.export_stl_axis_forward = EnumProperty(
        name='Export STL Axis - Forward',
        description='Which axis should be the relative front of the selected models, default: Y',
        items=(('X', 'X', ''),
               ('Y', 'Y', ''),
               ('Z', 'Z', ''),
               ('-X', '-X', ''),
               ('-Y', '-Y', ''),
               ('-Z', '-Z', '')),
        default='Y',
    )
    Scene.export_stl_axis_up = EnumProperty(
        name='Export STL Axis - Up',
        description='Which axis should be the relative up of the selected models, default: Z',
        items=(('X', 'X', ''),
               ('Y', 'Y', ''),
               ('Z', 'Z', ''),
               ('-X', '-X', ''),
               ('-Y', '-Y', ''),
               ('-Z', '-Z', '')),
        default='Z',
    )
    Scene.export_stl_ascii = BoolProperty(
        name='Export ASCII',
        description='Exports as ASCII text file, default: False',
        default=False
    )
    Scene.export_stl_global_scale = IntProperty(
        name='Export STL Global Scale',
        description='Scale multiplier to apply to objects being exported, default: 1',
        default=1
    )
    Scene.export_stl_use_scene_unit = BoolProperty(
        name='Export STL Use Scene Unit',
        description='Use scene units when exporting objects, default: False',
        default=False
    )
    Scene.export_stl_check_existing = BoolProperty(
        name='Check for Existing STL Files',
        description='Enabled or disables checking for preexisting exported STL files, default: True',
        default=True
    )
    Scene.clean_temp_stl_files = BoolProperty(
        name='Clean-up Temp. STL Files',
        description='Removes temporary STL files after importing or uploading to another application or server, default: True',
        default=True
    )
    Scene.export_as_individual = EnumProperty(
        name='Export individual',
        items=(('Individual', 'Individual', ''),
               ('Batch', 'Batch', ''),
               ('Merge', 'Merge', '')),
        default='Individual',
        description='Individual exports selected objects individually, Merge currently only works with local slicing operations for auto-arranging, Batch will export all selected as a single file for all operations. Default: Individual',
    )
    Scene.temp_stl_directory = StringProperty(
        name='Temporary STL file path',
        default=bpy.app.tempdir,
        description='Directory used for temporary STL files generated by this addon, default: {0}'.format(bpy.app.tempdir),
        subtype='DIR_PATH'
    )


#-------------------------------------------------------------------------
#   
#-------------------------------------------------------------------------
class import_settings(PropertyGroup):
    Scene = bpy.types.Scene
    Scene.import_obj_axis_forward = EnumProperty(
        name='Import OBJ Axis - Forward',
        description='Which axis should be the relative front of the imported OBJ files form Slic3r repair, default: Y',
        items=(('X', 'X', ''),
               ('Y', 'Y', ''),
               ('Z', 'Z', ''),
               ('-X', '-X', ''),
               ('-Y', '-Y', ''),
               ('-Z', '-Z', '')),
        default='Y',
    )
    Scene.import_obj_axis_up = EnumProperty(
        name='Import OBJ Axis - Up',
        description='Which axis should be the relative up of the imported OBJ files form Slic3r repair, default: Z',
        items=(('X', 'X', ''),
               ('Y', 'Y', ''),
               ('Z', 'Z', ''),
               ('-X', '-X', ''),
               ('-Y', '-Y', ''),
               ('-Z', '-Z', '')),
        default='Z',
    )
    Scene.import_obj_use_edges = BoolProperty(
        name='Import OBJ Use Edges',
        description='Use edges when importing OBJ files from Slic3r repair operations, default: True',
        default=True
    )
    Scene.import_obj_use_smooth_groups = BoolProperty(
        name='Import OBJ Use Smooth Groups',
        description='Use smooth groups when importing OBJ files from Slic3r repair operations, default: True',
        default=True
    )
    Scene.import_obj_use_split_objects = BoolProperty(
        name='Import OBJ Use Split Objects',
        description='Use split groups when importing OBJ files from Slic3r repair operations, default: True',
        default=True
    )
    Scene.import_obj_use_split_groups = BoolProperty(
        name='Import OBJ Use Split Groups',
        description='Use split groups when importing OBJ files from Slic3r repair operations, default: True',
        default=True
    )
    Scene.import_obj_use_groups_as_vgroups = BoolProperty(
        name='Import OBJ Use Groups As VGroups',
        description='Use groups as vgroups when importing OBJ files from Slic3r repair operations, default: False',
        default=False
    )
    Scene.import_obj_use_image_search = BoolProperty(
        name='Import OBJ Use Image Search',
        description='Use image search when importing OBJ files from Slic3r repair operations, default: True',
        default=True
    )
    Scene.import_obj_split_mode = EnumProperty(
        name='Import OBJ Split Mode',
        description='Activate split mode when importing OBJ files from Slic3r repair operations, default: On',
        items=(('ON', 'On', ''),
               ('OFF', 'Off', '')),
        default='ON',
    )
    Scene.import_obj_global_clamp_size = IntProperty(
        name='Import OBJ Global Clamp Size',
        description='Global clamp size to use when importing OBJ files from Slic3r repair operations, default: 0',
        default=0
    )
    Scene.clean_temp_obj_files = BoolProperty(
        name='Clean-up Temp. OBJ Files',
        description='Removes temporary OBJ files after importing into current Blender scene has finished, default: True',
        default=True
    )
    Scene.temp_obj_directory = StringProperty(
        name='Temporary OBJ file path',
        default=bpy.app.tempdir,
        description='Directory used for temporary OBJ files generated by calling Slic3r with "--repair" option, default: {0}'.format(bpy.app.tempdir),
        subtype='DIR_PATH'
    )


#-------------------------------------------------------------------------
#   
#-------------------------------------------------------------------------
class slic3r_settings(PropertyGroup):
    Scene = bpy.types.Scene
    if slic3r_exec_dir:
        Scene.slic3r_exec_dir = StringProperty(
            name='Slic3r path',
            default=slic3r_exec_dir,
            description='Slic3r executable directory path',
            subtype='DIR_PATH'
        )
    else:
        Scene.slic3r_exec_dir = StringProperty(
            name='Slic3r path',
            default='',
            description='Slic3r executable directory path',
            subtype='DIR_PATH'
        )

    if slic3r_exec_name:
        Scene.slic3r_exec_name = StringProperty(
            name='Slic3r executable name',
            default=slic3r_exec_name,
            description='Slicer executable name, just in-case addon authors got it wrong, default: {0}'.format(slic3r_exec_name),
        )
    else:
        Scene.slic3r_exec_name = StringProperty(
            name='Slic3r executable name',
            default='',
            description='Slicer executable name, just in-case addon authors got it wrong, default: Unset',
        )

    Scene.slic3r_conf_path = StringProperty(
        name='Slic3r Config',
        default='',
        description='Slic3r config file path. Hint, this should be a file with an ".ini" extension',
        subtype='FILE_PATH'
    )
    Scene.slic3r_post_script = StringProperty(
        name='Slic3r Post Processing Script',
        default='',
        description='File path to GCode post processing script',
        subtype='FILE_PATH'
    )
    Scene.slic3r_extra_args = StringProperty(
        name='Slic3r Extra Arguments',
        default='',
        description='These are applied to the command after any config file is loaded to enable easy & quick edits to an already working config',
    )
    Scene.repaired_parent_name = StringProperty(
        name='Repaired parent name',
        default='Slic3r-Fixed-Meshes',
        description='Imported OBJ files will be parented to this named empty, default: Slic3r-Fixed-Meshes',
    )


#-------------------------------------------------------------------------
#   
#-------------------------------------------------------------------------
class curaengine_settings(PropertyGroup):
    Scene = bpy.types.Scene
    if curaengine_exec_dir:
        Scene.curaengine_exec_dir = StringProperty(
            name='CuraEngine path',
            default=curaengine_exec_dir,
            description='CuraEngine executable directory path',
            subtype='DIR_PATH'
        )
    else:
        Scene.curaengine_exec_dir = StringProperty(
            name='CuraEngine path',
            default='',
            description='CuraEngine executable directory path',
            subtype='DIR_PATH'
        )
    if curaengine_exec_name:
        Scene.curaengine_exec_name = StringProperty(
            name='CuraEngine Executable Name',
            default=curaengine_exec_name,
            description='CuraEngine executable name',
        )
    else:
        Scene.curaengine_exec_name = StringProperty(
            name='CuraEngine path',
            default='',
            description='CuraEngine executable name',
        )

    Scene.curaengine_conf_path = StringProperty(
        name='CuraEngine Config',
        default='',
        description='CuraEngine config file path',
        subtype='FILE_PATH'
    )
    Scene.curaengine_extra_args = StringProperty(
        name='CuraEngine Extra Arguments',
        default='',
        description='This is to allow users of older versions of CuraEngine to define slicing settings via command line arguments',
    )


#-------------------------------------------------------------------------
#   
#-------------------------------------------------------------------------
class curl_settings(PropertyGroup):
    Scene = bpy.types.Scene
    if curl_exec_dir:
        Scene.curl_exec_dir = StringProperty(
            name='Curl path',
            default=curl_exec_dir,
            description='Curl executable directory path',
            subtype='DIR_PATH'
        )
    else:
        Scene.curl_exec_dir = StringProperty(
            name='Curl path',
            default='',
            description='Curl executable directory path',
            subtype='DIR_PATH'
        )
    if curl_exec_name:
        Scene.curl_exec_name = StringProperty(
            name='Curl path',
            default=curl_exec_name,
            description='Curl executable name',
        )
    else:
        Scene.curl_exec_dir = StringProperty(
            name='Curl path',
            default='',
            description='Curl executable name',
        )

    Scene.curl_test_ops = StringProperty(
        name='Curl test arguments',
        default='',
        description='Send Python formatted list of curl arguments from within Blender, for quick testing',
    )


#-------------------------------------------------------------------------
#   
#-------------------------------------------------------------------------
class octoprint_settings(PropertyGroup):
    Scene = bpy.types.Scene
    Scene.octoprint_auto_upload_from_slicers = BoolProperty(
        name='Upload GCode from Slicers',
        description='Uploads selected objects to OctoPrint server automatically after slicing with a local slicer if enabled, default: False',
        default=False
    )
    Scene.octoprint_host = StringProperty(
        name='Octoprint host or URL',
        default='http://localhost',
        description='URL or hostname of Octoprint server, default: http://localhost',
    )
    Scene.octoprint_port = StringProperty(
        name='Octoprint listening port',
        default='5000',
        description='Listening port of OctoPrint server, default: 5000',
    )
    Scene.octoprint_user = StringProperty(
        name='Octoprint user name',
        default='',
        description='Authorized username for connecting through reverse proxy to OctoPrint server',
    )
    Scene.octoprint_pass = StringProperty(
        name='OctoPrint passphrase',
        default='',
        description='Authorized passphrase for connecting through reverse proxy to OctoPrint server',
        subtype='PASSWORD',
    )
    Scene.octoprint_save_gcode_dir = StringProperty(
        name='Octoprint GCode directory',
        default='',
        description='Directory to save GCode file uploads to OctoPrint server',
    )
    Scene.octoprint_save_stl_dir = StringProperty(
        name='Octoprint STL directory',
        default='',
        description='Directory to save STL file uploads to OctoPrint server. Note if slicing server side, this directory is also where OctoPrint will save sliced GCode files',
    )
    Scene.octoprint_api_path = EnumProperty(
        name='OctoPrint upload directory path',
        items=(('/api/files/local', 'local', ''),
               ('/api/files/sdcard', 'sdcard', '')),
        default='/api/files/local',
        description='Mount point to send POST data to OctoPrint server, default: /api/files/local',
    )
    Scene.octoprint_x_api_key = StringProperty(
        name='OctoPrint X-API key',
        default='',
        description='Your client X-API key for interacting with OctoPrint server',
        subtype='PASSWORD',
    )
    Scene.octoprint_new_dir = StringProperty(
        name='OctoPrint new directory',
        default='',
        description='New directory to make on OctoPrint server, just in case someone wanted it in the future, not really necessary at this point though',
    )
    Scene.octoprint_slice_uploaded_stl = BoolProperty(
        name='Slice uploaded STL files with OctoPrint server',
        description='Uploaded STL files will be set to slice into GCode files by OctoPrint server, this is an asynchronous process according to the documentation, default: False',
        default=False
    )
    Scene.octoprint_slice_slicer = StringProperty(
        name='OctoPrint Slicer',
        default='cura',
        description='Slicer to use when slicing uploaded STL files to OctoPrint server, default: cura',
    )
    Scene.octoprint_slice_printerProfile = StringProperty(
        name='Octoprint Slicer Printer Profile',
        default='',
        description='Printer profile to use, if not set the default printer profile will be used. Hint, this is likely your printer model name',
    )
    Scene.octoprint_slice_Profile = StringProperty(
        name='OctoPrint Slicer Profile',
        default='',
        description='Name of the slicing profile to use, if not set the default slicing profile of the slicer will be used',
    )
    Scene.octoprint_slice_Profile_ops = StringProperty(
        name='OctoPrint Slicer Profile Customizations',
        default='',
        description='Any slicing profile customization to append or overwrite from selected profile, if not set the selected or default slicing profile of the slicer will be used',
    )
    Scene.octoprint_slice_position_x = IntProperty(
        name='OctoPrint Slice Position X',
        description='Position along the X axis that objects should be centered to for slicing into GCode, default: 0',
        default=0
    )
    Scene.octoprint_slice_position_y = IntProperty(
        name='OctoPrint Slice Position Y',
        description='Position along the Y axis that objects should be centered to for slicing into GCode, default: 0',
        default=0
    )


#-------------------------------------------------------------------------
#   
#-------------------------------------------------------------------------
class repetier_settings(PropertyGroup):
    Scene = bpy.types.Scene
    Scene.repetier_auto_upload_from_slicers = BoolProperty(
        name='Upload GCode from Slicers',
        description='Uploads selected objects to Repetier server automatically after slicing into GCode files locally has finished if enabled, default: False',
        default=False
    )
    Scene.repetier_host = StringProperty(
        name='Repetier host or URL',
        default='http://localhost',
        description='URL or hostname of Repetier server, default: http://localhost',
    )
    Scene.repetier_port = StringProperty(
        name='Repetier listening port',
        default='3344',
        description='Listening port of Repetier server, default: 3344',
    )
    Scene.repetier_user = StringProperty(
        name='Repetier user name',
        default='',
        description='Authorized username for connecting through reverse proxy to Repetier server',
    )
    Scene.repetier_pass = StringProperty(
        name='Repetier passphrase',
        default='',
        description='Authorized passphrase for connecting through reverse proxy to Repetier server',
        subtype='PASSWORD',
    )
    Scene.repetier_save_gcode_dir = StringProperty(
        name='Repetier GCode directory',
        default='',
        description='Directory to save GCode file uploads to Repetier server. Hint, this is likely your printer model name',
    )
    Scene.repetier_save_stl_dir = StringProperty(
        name='Repetier STL directory',
        default='',
        description='Directory to save STL file uploads to Repetier server',
    )
    Scene.repetier_api_path = StringProperty(
        name='Repetier upload directory path',
        default='/printer/model',
        description='Mount point to send POST data to Repetier server, default: /printer/model',
    )
    Scene.repetier_x_api_key = StringProperty(
        name='Repetier X-API key',
        default='',
        description='Your client X-API key for interacting with Repetier server',
        subtype='PASSWORD',
    )


#-------------------------------------------------------------------------
#   
#-------------------------------------------------------------------------
class misc_settings(PropertyGroup):
    Scene = bpy.types.Scene
    Scene.open_browser_after_upload = BoolProperty(
        name='Open Browser after Upload',
        description='Opens a web browser (or new tab) to the uploaded GCode directory if enabled, default: False',
        default=False
    )
    Scene.preview_gcode = BoolProperty(
        name='Preview locally sliced GCode',
        description='Opens GCode file(s) within Blender Text Editor when local slicers have finished converting selected object into GCode files. Default: False',
        default=False
    )
    Scene.gcode_directory = StringProperty(
        name='Local GCode directory',
        default=bpy.app.tempdir,
        description='Local slicer GCode output directory, default: {0}'.format(bpy.app.tempdir),
        subtype='DIR_PATH'
    )
    Scene.log_level = EnumProperty(
        name='Log Level',
        description='Logging & terminal output level, default: Scrubbed',
        items=(('SCRUBBED', 'Scrubbed', ''),
               ('QUITE', 'Quite', ''),
               ('VERBOSE', 'Verbose', ''),),
        default='SCRUBBED',
    )
    Scene.prefered_local_slicer = EnumProperty(
        name='Preferd Local Slicer',
        items=(('Slic3r', 'Slic3r', ''),
               ('CuraEngine', 'CuraEngine', '')),
        default='Slic3r',
        description='Local slicer to use for translating exported STL files from Blender into GCode files. Default: Slic3r',
    )
    Scene.prefered_print_server = EnumProperty(
        name='Prefered Print Server',
        items=(('OctoPrint', 'OctoPrint', ''),
               ('Repetier', 'Repetier', '')),
        default='OctoPrint',
        description='3D Printer server to conntect to. Default: OctoPrint',
    )
    Scene.button_text_color = bpy.props.FloatVectorProperty(
        name='Button Text Color Picker',
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.1, 0.75, 0.75, 1.0),
        description='',
    )
    Scene.button_background_color = bpy.props.FloatVectorProperty(
        name='Button Background Color Picker',
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0),
        description='',
    )


#-------------------------------------------------------------------------
#   
#-------------------------------------------------------------------------
class octoprint_preview_webcam_settings(PropertyGroup):
    Scene = bpy.types.Scene
    Scene.octoprint_snapshot_dir = StringProperty(
        name='Temporary .jpg file path',
        default=bpy.app.tempdir,
        description='Directory used for temporary JPG files generated by this addon, default: {0}'.format(bpy.app.tempdir),
        subtype='DIR_PATH'
    )
    Scene.octoprint_snapshot_name = StringProperty(
        name='Snapshot Name',
        default='OctoPrint_Preview',
        description='Name to use for Snapshot & Video related things that have to be setup within Blender: OctoPrint_Preview',
    )
    Scene.octoprint_camera_port = StringProperty(
        name='Webcam Port',
        default='8080',
        description='Webcam port, set if different than OctoPrint server API port, default: 8080',
    )
    Scene.octoprint_preview_xy_scale = IntProperty(
        name='OctoPrint Preview XY Scale',
        description='Scale divider to apply to preview image plane object based off image pixel size, default: 10',
        default=10,
        min=1,
    )
    Scene.octoprint_snapshot_action = StringProperty(
        name='Snapshot Action',
        default='?action=snapshot',
        description='The URL path to request a snapshot from the server, default: ?action=snapshot',
    )
    Scene.octoprint_stream_action = StringProperty(
        name='Stream Action',
        default='?action=stream',
        description='The URL path to request stream from the server, default: ?action=stream',
    )
    Scene.octoprint_preview_placement = EnumProperty(
        name='Preview Placement',
        description='Where the preview plane will be moved to in relation to global origin, default: Center',
        items=(('CENTER', 'Center', ''),
               ('NORTH', 'North', ''),
               ('EAST', 'East', ''),
               ('SOUTH', 'South', ''),
               ('WEST', 'West', '')),
        default='CENTER',
    )
    Scene.octoprint_preview_layer = IntProperty(
        name='Preview Layer',
        description='What layer within the 3D View will have the preview plane added to, default: 0',
        default=0,
        min=0,
        max=19,
    )
    Scene.octoprint_target_screen = StringProperty(
        name='Target Screen',
        default='Default',
        description='What named screen will have the 3D View ports modified for build plate preview operations, default: Default, hint: bpy.context.screen.name',
    )
    Scene.octoprint_target_3dview = IntProperty(
        name='Target 3D View',
        description='What 3D View will have rendering settings modified, default: 0',
        default=0,
        min=0,
        max=9,
    )


#-------------------------------------------------------------------------
#   
#-------------------------------------------------------------------------
class repetier_preview_webcam_settings(PropertyGroup):
    Scene = bpy.types.Scene
    Scene.repetier_snapshot_dir = StringProperty(
        name='Temporary .jpg file path',
        default=bpy.app.tempdir,
        description='Directory used for temporary JPG files generated by this addon, default: {0}'.format(bpy.app.tempdir),
        subtype='DIR_PATH'
    )
    Scene.repetier_snapshot_name = StringProperty(
        name='Snapshot Name',
        default='Repetier_Preview',
        description='Name to use for Snapshot & Video related things that have to be setup within Blender: Repetier_Preview',
    )
    Scene.repetier_camera_port = StringProperty(
        name='Webcam Port',
        default='8080',
        description='Webcam port, set if different than Repetier server API port, default: 8080',
    )
    Scene.repetier_preview_xy_scale = IntProperty(
        name='Repetier Preview XY Scale',
        description='Scale divider to apply to preview image plane object based off image pixel size, default: 10',
        default=10,
        min=1,
    )
    Scene.repetier_snapshot_action = StringProperty(
        name='Snapshot Action',
        default='?action=snapshot',
        description='The URL path to request a snapshot from the server, default: ?action=snapshot',
    )
    Scene.repetier_stream_action = StringProperty(
        name='Stream Action',
        default='?action=stream',
        description='The URL path to request stream from the server, default: ?action=stream',
    )
    Scene.repetier_preview_placement = EnumProperty(
        name='Preview Placement',
        description='Where the preview plane will be moved to in relation to global origin, default: Center',
        items=(('CENTER', 'Center', ''),
               ('NORTH', 'North', ''),
               ('EAST', 'East', ''),
               ('SOUTH', 'South', ''),
               ('WEST', 'West', '')),
        default='CENTER',
    )
    # TO-DO - write a function that takes only (self, context) as args, returns nothing
    #  And updates preexisting object placement if the above or bellow settings change
    #  by using: update=function_name(self, context)
    #  within above and bellow property blocks.
    Scene.repetier_preview_layer = IntProperty(
        name='Preview Layer',
        description='What layer within the 3D View will have the preview plane added to, default: 0',
        default=0,
        min=0,
        max=19,
    )
    Scene.repetier_target_screen = StringProperty(
        name='Target Screen',
        default='Default',
        description='What screen name will have the 3D View ports modified for build plate preview operations, default: Default, hint: bpy.context.screen.name',
    )
    Scene.repetier_target_3dview = IntProperty(
        name='Target 3D View',
        description='What 3D View will have rendering settings modified, default: 0',
        default=0,
        min=0,
        max=9,
    )


#-------------------------------------------------------------------------
#    Panel configurations
#-------------------------------------------------------------------------
class quick_slicer_tools_buttons_panel(Panel):
    bl_space_type = 'VIEW_3D'                              # What view this panel will be visible to users
    bl_region_type = 'TOOLS'                               # The region the panel will be used in
    bl_context = 'objectmode'                              # The context that this panel belongs to
    bl_category = this_addons_name                                # What tab this add-on will be under
    bl_label = 'Quick Slicer Tools'                        # Display name in the interface
    bl_idname = 'object.quick_slicer_tools_buttons_panel'  # Unique ID for buttons & menu items

    def draw(self, context):
        scene = context.scene
        layout = self.layout
        col = layout.column(align=True)

        col.operator('object.slic3r_repair_button', text='Slic3r Repair Selected')
        col.prop(scene, 'repaired_parent_name', text='Repaired Parent Name')
        col.prop(scene, 'prefered_local_slicer', text='Prefered Local Slicer')
        if 'Slic3r' in scene.prefered_local_slicer:
            col.operator('object.slic3r_slice_button', text='Slic3r Slice Selected')
        elif 'CuraEngine' in scene.prefered_local_slicer:
            col.operator('object.curaengine_slice_button', text='CuraEngine Slice Selected')
        layout.prop(scene, 'export_as_individual', text='Export as Individual Files')
        layout.prop(scene, 'gcode_directory', text='GCode Save Directory')
        layout.prop(scene, 'preview_gcode', text='Preview GCode')
        col.prop(scene, 'prefered_print_server', text='Prefered Printer Server')
        if 'OctoPrint' in scene.prefered_print_server:
            layout.prop(scene, 'octoprint_auto_upload_from_slicers', text='OctoPrint Upload GCode')
        if 'Repetier' in scene.prefered_print_server:
            layout.prop(scene, 'repetier_auto_upload_from_slicers', text='Repetier Upload GCode')
        layout.prop(scene, 'open_browser_after_upload', text='Open Browser After GCode Upload')
        layout.prop(scene, 'log_level', text='Logging Level')


#-------------------------------------------------------------------------
#   
#-------------------------------------------------------------------------
class print_server_buttons_panel(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_context = 'objectmode'
    bl_category = this_addons_name
    bl_label = 'Print Server Actions'
    bl_idname = 'object.print_server_buttons_panel'

    def draw(self, context):
        scene = context.scene
        layout = self.layout
        col = layout.column(align=True)

        layout.prop(scene, 'prefered_print_server', text='Prefered Printer Server')
        if 'OctoPrint' in scene.prefered_print_server:
            layout.operator('object.octoprint_preview_webcam_button', text='Preview Build Plate')
            layout.operator('object.octoprint_stream_webcam_button', text='Stream Build Plate')
            layout.prop(scene, 'octoprint_api_path', text='POST Directory')
            layout.prop(scene, 'octoprint_new_dir', text='New Directory Path')
            layout.operator('object.octoprint_mkdir_button', text='Make New Directory')
            layout.prop(scene, 'octoprint_save_stl_dir', text='STL Directory')
            layout.operator('object.octoprint_upload_stl_button', text='Upload Selected as STL')
            layout.prop(scene, 'octoprint_slice_uploaded_stl', text='Slice Uploaded STL(s)')
            layout.operator('object.octoprint_download_file_list', text='Parse OctoPrint File list')
        if 'Repetier' in scene.prefered_print_server:
            layout.operator('object.repetier_preview_webcam_button', text='Preview Build Plate')
            layout.operator('object.repetier_stream_webcam_button', text='Stream Build Plate')
            # TO-DO - see about making functions & classes to handle the following features
#            layout.prop(scene, 'repetier_api_path', text='POST Directory')
#            layout.prop(scene, 'repetier_new_dir', text='New Directory Path')
#            layout.operator('object.repetier_mkdir_button', text='Make New Directory')
#            layout.prop(scene, 'repetier_save_stl_dir', text='STL Directory')
#            layout.operator('object.repetier_upload_stl_button', text='Upload Selected as STL')
#            layout.prop(scene, 'repetier_slice_uploaded_stl', text='Slice Uploaded STL(s)')


#-------------------------------------------------------------------------
#   
#-------------------------------------------------------------------------
class curl_test_panel(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_context = 'objectmode'
    bl_category = this_addons_name
    bl_label = 'Curl Test Command'
    bl_idname = 'object.curl_test_panel'

    def draw(self, context):
        scene = context.scene
        layout = self.layout

        layout.prop(scene, 'curl_test_ops', text='Arguments to send curl, comma separated please')
        layout.operator('object.curl_test_button', text='Run Curl')


#-------------------------------------------------------------------------
#   Settings panel for OctoPrint slicer interactions
#-------------------------------------------------------------------------
class print_server_slicer_config_panel(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_context = 'objectmode'
    bl_category = this_addons_name
    bl_label = 'Server Slicer Settings'
    bl_idname = 'object.print_server_slicer_config_panel'

    def draw(self, context):
        scene = context.scene
        layout = self.layout
        col = layout.column(align=True)

        layout.prop(scene, 'prefered_print_server', text='Prefered Printer Server')
        if 'OctoPrint' in scene.prefered_print_server:
            layout.prop(scene, 'octoprint_slice_uploaded_stl', text='Slice Uploaded STL(s)')
            layout.prop(scene, 'octoprint_slice_slicer', text='Slicer Name')
            layout.prop(scene, 'octoprint_slice_printerProfile', text='Printer Profile')
            layout.prop(scene, 'octoprint_slice_Profile', text='Slicer Profile')
            layout.prop(scene, 'octoprint_slice_Profile_ops', text='Slicer Profile Customizations')
            layout.prop(scene, 'octoprint_slice_position_x', text='Slicer X Position')
            layout.prop(scene, 'octoprint_slice_position_y', text='Slicer Y Position')
        if 'Repetier' in scene.prefered_print_server:
            col.label(text="One day maybe")


#-------------------------------------------------------------------------
#   Settings panel for Exporting STL files from Blender
#-------------------------------------------------------------------------
class export_stl_config_panel(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_context = 'objectmode'
    bl_category = this_addons_name
    bl_label = 'Export STL Settings'
    bl_idname = 'object.export_stl_config_panel'

    def draw(self, context):
        scene = context.scene
        layout = self.layout

        layout.prop(scene, 'clean_temp_stl_files', text='Remove Temporary STL Files')
        layout.prop(scene, 'export_as_individual', text='Export as individual Files')
        layout.prop(scene, 'temp_stl_directory', text='STL Temp Directory')
        layout.prop(scene, 'export_stl_global_scale', text='Global Scale')
        layout.prop(scene, 'export_stl_axis_forward', text='Forward Axis')
        layout.prop(scene, 'export_stl_axis_up', text='Up Axis')
        layout.prop(scene, 'export_stl_ascii', text='ASCII Format')
        layout.prop(scene, 'export_stl_use_scene_unit', text='Use Scene Unit')
        layout.prop(scene, 'export_stl_check_existing', text='Check Existing Prior to Export')


#-------------------------------------------------------------------------
#   Settings panel for Exporting STL files from Blender
#-------------------------------------------------------------------------
class import_obj_config_panel(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_context = 'objectmode'
    bl_category = this_addons_name
    bl_label = 'Import OBJ Settings'
    bl_idname = 'object.import_obj_config_panel'

    def draw(self, context):
        scene = context.scene
        layout = self.layout

        layout.prop(scene, 'clean_temp_obj_files', text='Remove Temporary OBJ Files')
        layout.prop(scene, 'temp_obj_directory', text='OBJ Temp Directory')
        layout.prop(scene, 'import_obj_global_clamp_size', text='OBJ Global Clamp Size')
        layout.prop(scene, 'import_obj_axis_forward', text='OBJ Axis Forward')
        layout.prop(scene, 'import_obj_axis_up', text='OBJ Axis Up')
        layout.prop(scene, 'import_obj_use_edges', text='OBJ Use Edges')
        layout.prop(scene, 'import_obj_use_smooth_groups', text='OBJ Use Smooth Groups')
        layout.prop(scene, 'import_obj_use_split_objects', text='OBJ Use Split Objects')
        layout.prop(scene, 'import_obj_use_split_groups', text='OBJ Use Split Groups')
        layout.prop(scene, 'import_obj_use_groups_as_vgroups', text='OBJ Use Groups as VGroups')
        layout.prop(scene, 'import_obj_use_image_search', text='OBJ Use Image Search')
        layout.prop(scene, 'import_obj_split_mode', text='OBJ Split Mode')


#-------------------------------------------------------------------------
#   Settings panel for Slic3r & CuraEngin interactions
#-------------------------------------------------------------------------
class slicer_config_panel(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_context = 'objectmode'
    bl_category = this_addons_name
    bl_label = 'Local Slicer Settings'
    bl_idname = 'object.slicer_config_panel'

    def draw(self, context):
        scene = context.scene
        layout = self.layout

        layout.prop(scene, 'prefered_local_slicer', text='Prefered Local Slicer')
        if 'Slic3r' in scene.prefered_local_slicer:
            layout.prop(scene, 'slic3r_exec_dir', text='Directory of Executable')
            layout.prop(scene, 'slic3r_exec_name', text='Name of Executable')
            layout.prop(scene, 'slic3r_conf_path', text='Slic3r Configuration File')
            layout.prop(scene, 'slic3r_post_script', text='Post Processing Script')
            layout.prop(scene, 'slic3r_extra_args', text='Extra Arguments')
        elif 'CuraEngine' in scene.prefered_local_slicer:
            layout.prop(scene, 'curaengine_exec_dir', text='Directory of Executable')
            layout.prop(scene, 'curaengine_exec_name', text='Name of Executable')
            layout.prop(scene, 'curaengine_conf_path', text='Configuration File')
            layout.prop(scene, 'curaengine_extra_args', text='Extra Arguments')
        layout.prop(scene, 'gcode_directory', text='GCode Save Directory')


#-------------------------------------------------------------------------
#   
#-------------------------------------------------------------------------
class curl_config_panel(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_context = 'objectmode'
    bl_category = this_addons_name
    bl_label = 'Curl Settings'
    bl_idname = 'object.curl_config_panel'

    def draw(self, context):
        scene = context.scene
        layout = self.layout

        layout.prop(scene, 'curl_exec_dir', text='Directory of Executable')
        layout.prop(scene, 'curl_exec_name', text='Name of Executable')


#-------------------------------------------------------------------------
#   
#-------------------------------------------------------------------------
class print_server_connection_config_panel(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_context = 'objectmode'
    bl_category = this_addons_name
    bl_label = 'Server Connection Settings'
    bl_idname = 'object.print_server_connection_config_panel'

    def draw(self, context):
        scene = context.scene
        layout = self.layout
        col = layout.column(align=True)

        layout.prop(scene, 'prefered_print_server', text='Prefered Printer Server')
        if 'OctoPrint' in scene.prefered_print_server:
            layout.prop(scene, 'octoprint_auto_upload_from_slicers', text='Upload GCode from Slicers')
            layout.prop(scene, 'open_browser_after_upload', text='Open Browser After Upload')
            layout.prop(scene, 'octoprint_host', text='Host URL')
            layout.prop(scene, 'octoprint_port', text='Host Port')
            layout.prop(scene, 'octoprint_user', text='User Name')
            layout.prop(scene, 'octoprint_pass', text='Passphrase')
            layout.prop(scene, 'octoprint_api_path', text='POST Directory')
            layout.prop(scene, 'octoprint_save_gcode_dir', text='GCode Directory')
            layout.prop(scene, 'octoprint_save_stl_dir', text='STL Directory')
            layout.prop(scene, 'octoprint_x_api_key', text='X-API Key')
        elif 'Repetier' in scene.prefered_print_server:
            layout.prop(scene, 'repetier_auto_upload_from_slicers', text='Upload GCode from Slicers')
            layout.prop(scene, 'open_browser_after_upload', text='Open Browser After Upload')
            layout.prop(scene, 'repetier_host', text='Host URL')
            layout.prop(scene, 'repetier_port', text='Host Port')
            layout.prop(scene, 'repetier_user', text='User Name')
            layout.prop(scene, 'repetier_pass', text='Passphrase')
            layout.prop(scene, 'repetier_api_path', text='POST Directory')
            layout.prop(scene, 'repetier_save_gcode_dir', text='GCode Directory')
            layout.prop(scene, 'repetier_save_stl_dir', text='STL Directory')
            layout.prop(scene, 'repetier_x_api_key', text='X-API Key')


#-------------------------------------------------------------------------
#   
#-------------------------------------------------------------------------
class preview_webcam_config_panel(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_context = 'objectmode'
    bl_category = this_addons_name
    bl_label = 'Server Webcam Settings'
    bl_idname = 'object.preview_webcam_config_panel'

    def draw(self, context):
        scene = context.scene
        layout = self.layout
        col = layout.column(align=True)

        col.prop(scene, 'prefered_print_server', text='Prefered Printer Server')
        if 'OctoPrint' in scene.prefered_print_server:
            layout.prop(scene, 'octoprint_target_screen', text='Target Screen Name')
            layout.prop(scene, 'octoprint_target_3dview', text='Target 3D View')
            layout.prop(scene, 'octoprint_snapshot_dir', text='JPG Directory')
            layout.prop(scene, 'octoprint_snapshot_name', text='Snapshot Name')
            layout.prop(scene, 'octoprint_camera_port', text='Webcam Port')
            layout.prop(scene, 'octoprint_snapshot_action', text='Snapshot Action')
            layout.prop(scene, 'octoprint_stream_action', text='Stream Action')
            layout.prop(scene, 'octoprint_preview_placement', text='Preview Placement')
            layout.prop(scene, 'octoprint_preview_layer', text='Layer to Place Preview')
            layout.prop(scene, 'octoprint_preview_xy_scale', text='XY Scale')
        elif 'Repetier' in scene.prefered_print_server:
            layout.prop(scene, 'repetier_target_screen', text='Target Screen Name')
            layout.prop(scene, 'repetier_target_3dview', text='Target 3D View')
            layout.prop(scene, 'repetier_snapshot_dir', text='JPG Directory')
            layout.prop(scene, 'repetier_snapshot_name', text='Snapshot Name')
            layout.prop(scene, 'repetier_camera_port', text='Webcam Port')
            layout.prop(scene, 'repetier_snapshot_action', text='Snapshot Action')
            layout.prop(scene, 'repetier_stream_action', text='Stream Action')
            layout.prop(scene, 'repetier_preview_placement', text='Preview Placement')
            layout.prop(scene, 'repetier_preview_layer', text='Layer to Place Preview')
            layout.prop(scene, 'repetier_preview_xy_scale', text='XY Scale')
        layout.prop(scene, 'button_background_color', text='Button Background Color')
        layout.prop(scene, 'button_text_color', text='Button Text Color')


#-------------------------------------------------------------------------
#    Actions to take when "Export & Re-import" button is pressed
#-------------------------------------------------------------------------
class slic3r_repair_button(Operator):
    """Export as STL then import to Slic3r running with --repair and import repaired objects back into Blender"""
    bl_idname = 'object.slic3r_repair_button'
    bl_label = 'Slic3r Repair Selected'
    bl_options = {'REGISTER', 'UNDO'}

    # execute() is called by blender when running the operator
    def execute(self, context):
        if not context.selected_objects:
            raise Exception('Please select some objects first.')

        Scene = context.scene
        slic3r_repair_operations(
            selected_objects = context.selected_objects,
            temp_stl_directory = Scene.temp_stl_directory,
            temp_obj_directory = Scene.temp_obj_directory,
            repaired_parent_name = Scene.repaired_parent_name,
            export_as_individual = Scene.export_as_individual,
            slic3r_exec_dir = Scene.slic3r_exec_dir,
            slic3r_exec_name = Scene.slic3r_exec_name,
            export_stl_axis_forward = Scene.export_stl_axis_forward,
            export_stl_axis_up = Scene.export_stl_axis_up,
            export_stl_ascii = Scene.export_stl_ascii,
            export_stl_check_existing = Scene.export_stl_check_existing,
            export_stl_global_scale = Scene.export_stl_global_scale,
            export_stl_use_scene_unit = Scene.export_stl_use_scene_unit,
            import_obj_axis_forward = Scene.import_obj_axis_forward,
            import_obj_axis_up = Scene.import_obj_axis_up,
            import_obj_use_edges = Scene.import_obj_use_edges,
            import_obj_use_smooth_groups = Scene.import_obj_use_smooth_groups,
            import_obj_use_split_objects = Scene.import_obj_use_split_objects,
            import_obj_use_split_groups = Scene.import_obj_use_split_groups,
            import_obj_use_groups_as_vgroups = Scene.import_obj_use_groups_as_vgroups,
            import_obj_use_image_search = Scene.import_obj_use_image_search,
            import_obj_split_mode = Scene.import_obj_split_mode,
            import_obj_global_clamp_size = Scene.import_obj_global_clamp_size)

        obj_names = []
        for obj in context.selected_objects:
            obj_names += [obj.name]


        info = ('Finished with "slic3r --repair {0}"'.format(obj_names))
        self.report({'INFO'}, info)
        return {'FINISHED'}


#-------------------------------------------------------------------------
#    Actions to take when "Slice with Slic3r" button is pressed
#-------------------------------------------------------------------------
class slic3r_slice_button(Operator):
    """Export STL to Slic3r, generate GCODE and if configured upload to print server"""
    bl_idname = 'object.slic3r_slice_button'
    bl_label = 'Slice with Slic3r'

    def execute(self, context):
        if not context.selected_objects:
            raise Exception('Please select some objects first.')

        Scene = context.scene
        slic3r_slice_operations(
            selected_objects = context.selected_objects,
            stl_dir = Scene.temp_stl_directory,
            gcode_dir = Scene.gcode_directory,
            export_as_individual = Scene.export_as_individual,
            export_stl_axis_forward = Scene.export_stl_axis_forward,
            export_stl_axis_up = Scene.export_stl_axis_up,
            export_stl_ascii = Scene.export_stl_ascii,
            export_stl_check_existing = Scene.export_stl_check_existing,
            export_stl_global_scale = Scene.export_stl_global_scale,
            export_stl_use_scene_unit = Scene.export_stl_use_scene_unit,
            slic3r_conf = Scene.slic3r_conf_path,
            slic3r_post_script = Scene.slic3r_post_script,
            slic3r_extra_args = Scene.slic3r_extra_args,
            slic3r_exec_dir = Scene.slic3r_exec_dir,
            slic3r_exec_name = Scene.slic3r_exec_name,
            octoprint_auto_upload_from_slicers = Scene.octoprint_auto_upload_from_slicers,
            octoprint_host = Scene.octoprint_host,
            octoprint_api_path = Scene.octoprint_api_path,
            octoprint_x_api_key = Scene.octoprint_x_api_key,
            octoprint_port = Scene.octoprint_port,
            octoprint_user = Scene.octoprint_user,
            octoprint_pass = Scene.octoprint_pass,
            octoprint_save_gcode_dir = Scene.octoprint_save_gcode_dir,
            repetier_auto_upload_from_slicers = Scene.repetier_auto_upload_from_slicers,
            repetier_host = Scene.repetier_host,
            repetier_api_path = Scene.repetier_api_path,
            repetier_x_api_key = Scene.repetier_x_api_key,
            repetier_port = Scene.repetier_port,
            repetier_user = Scene.repetier_user,
            repetier_pass = Scene.repetier_pass,
            repetier_save_gcode_dir = Scene.repetier_save_gcode_dir,
            open_browser_after_upload = Scene.open_browser_after_upload,
            curl_exec_dir = Scene.curl_exec_dir,
            curl_exec_name = Scene.curl_exec_name,
            log_level = Scene.log_level)

        obj_names = []
        for obj in context.selected_objects:
            obj_names += [obj.name]

        info = ('Finished slicing selected objects: {0}'.format(obj_names))
        self.report({'INFO'}, info)
        return {'FINISHED'}


#-------------------------------------------------------------------------
#    Actions to take when "Slice with CuraEngine" button is pressed
#-------------------------------------------------------------------------
class curaengine_slice_button(Operator):
    """Export STL to CuraEngine, generate GCODE and if configured upload to print server"""
    bl_idname = 'object.curaengine_slice_button'
    bl_label = 'Slice with CuraEngine'

    def execute(self, context):
        if not context.selected_objects:
            raise Exception('Please select some objects first.')

        Scene = context.scene
        curaengine_slice_operations(
            selected_objects = context.selected_objects,
            stl_dir = Scene.temp_stl_directory,
            gcode_dir = Scene.gcode_directory,
            export_as_individual = Scene.export_as_individual,
            export_stl_axis_forward = Scene.export_stl_axis_forward,
            export_stl_axis_up = Scene.export_stl_axis_up,
            export_stl_ascii = Scene.export_stl_ascii,
            export_stl_check_existing = Scene.export_stl_check_existing,
            export_stl_global_scale = Scene.export_stl_global_scale,
            export_stl_use_scene_unit = Scene.export_stl_use_scene_unit,
            curaengine_conf = Scene.curaengine_conf_path,
            curaengine_extra_args = Scene.curaengine_extra_args,
            curaengine_exec_dir = Scene.curaengine_exec_dir,
            curaengine_exec_name = curaengine_exec_name,
            octoprint_auto_upload_from_slicers = Scene.octoprint_auto_upload_from_slicers,
            octoprint_host = Scene.octoprint_host,
            octoprint_api_path = Scene.octoprint_api_path,
            octoprint_x_api_key = Scene.octoprint_x_api_key,
            octoprint_port = Scene.octoprint_port,
            octoprint_user = Scene.octoprint_user,
            octoprint_pass = Scene.octoprint_pass,
            octoprint_save_gcode_dir = Scene.octoprint_save_gcode_dir,
            repetier_auto_upload_from_slicers = Scene.repetier_auto_upload_from_slicers,
            repetier_host = Scene.repetier_host,
            repetier_api_path = Scene.repetier_api_path,
            repetier_x_api_key = Scene.repetier_x_api_key,
            repetier_port = Scene.repetier_port,
            repetier_user = Scene.repetier_user,
            repetier_pass = Scene.repetier_pass,
            repetier_save_gcode_dir = Scene.repetier_save_gcode_dir,
            open_browser_after_upload = Scene.open_browser_after_upload,
            curl_exec_dir = Scene.curl_exec_dir,
            curl_exec_name = Scene.curl_exec_name,
            log_level = Scene.log_level)

        obj_names = []
        for obj in context.selected_objects:
            obj_names += [obj.name]

        info = ('Finished slicing selected objects: {0}'.format(obj_names))
        self.report({'INFO'}, info)
        return {'FINISHED'}


#-------------------------------------------------------------------------
#    Actions to take when "Make Directory" button is pressed
#-------------------------------------------------------------------------
class octoprint_mkdir_button(Operator):
    """Make a directory path on OctoPrint server"""
    bl_idname = 'object.octoprint_mkdir_button'
    bl_label = 'OctoPrint mkdir'

    def execute(self, context):
        Scene = context.scene
        octoprint_mkdir(
            check_path = Scene.octoprint_new_dir,
            host_url = Scene.octoprint_host,
            api_path = Scene.octoprint_api_path,
            xapi_key = Scene.octoprint_x_api_key,
            host_port = Scene.octoprint_port,
            user_name = Scene.octoprint_user,
            passphrase = Scene.octoprint_pass,
            curl_exec_dir = Scene.curl_exec_dir,
            curl_exec_name = Scene.curl_exec_name,
            log_level = Scene.log_level)

        info = ('Finished making new directory: {0} on host: {1}'.format(Scene.octoprint_new_dir, Scene.octoprint_host))
        self.report({'INFO'}, info)
        return {'FINISHED'}


#-------------------------------------------------------------------------
#    Actions to take when "Upload Selected as STL" button is pressed
#-------------------------------------------------------------------------
class octoprint_upload_stl_button(Operator):
    """Upload selected as STL to on OctoPrint server"""
    bl_idname = 'object.octoprint_upload_stl_button'
    bl_label = 'OctoPrint Upload STL'

    def execute(self, context):
        if not context.selected_objects:
            raise Exception('Please select some objects first.')

        Scene = context.scene
        octoprint_upload_stl_operations(
            selected_objects = context.selected_objects,
            temp_stl_directory = Scene.temp_stl_directory,
            export_as_individual = Scene.export_as_individual,
            export_stl_axis_forward = Scene.export_stl_axis_forward,
            export_stl_axis_up = Scene.export_stl_axis_up,
            export_stl_ascii = Scene.export_stl_ascii,
            export_stl_check_existing = Scene.export_stl_check_existing,
            export_stl_global_scale = Scene.export_stl_global_scale,
            export_stl_use_scene_unit = Scene.export_stl_use_scene_unit,
            clean_temp_stl_files = Scene.clean_temp_stl_files,
            sliceOnServer = Scene.octoprint_slice_uploaded_stl,
            octoprint_host = Scene.octoprint_host,
            octoprint_api_path = Scene.octoprint_api_path,
            octoprint_x_api_key = Scene.octoprint_x_api_key,
            octoprint_port = Scene.octoprint_port,
            octoprint_user = Scene.octoprint_user,
            octoprint_pass = Scene.octoprint_pass,
            octoprint_save_stl_dir = Scene.octoprint_save_stl_dir,
            octoprint_slice_slicer = Scene.octoprint_slice_slicer,
            octoprint_slice_printerProfile = Scene.octoprint_slice_printerProfile,
            octoprint_slice_Profile = Scene.octoprint_slice_Profile,
            octoprint_slice_Profile_ops = Scene.octoprint_slice_Profile_ops,
            octoprint_slice_position_x = Scene.octoprint_slice_position_x,
            octoprint_slice_position_y = Scene.octoprint_slice_position_y,
            curl_exec_dir = Scene.curl_exec_dir,
            curl_exec_name = Scene.curl_exec_name,
            log_level = Scene.log_level)

        obj_names = []
        for obj in context.selected_objects:
            obj_names += [obj.name]

        info = ('Finished uploading selected objects: {0} to OctoPrint server'.format(obj_names))
        self.report({'INFO'}, info)
        return {'FINISHED'}


class octoprint_preview_webcam_button(Operator):
    """Preform some magic so users can see snapshot of build plate of thier printer without leaving Blender"""
    bl_idname = 'object.octoprint_preview_webcam_button'
    bl_label = 'Preview Build Plate'

    def execute(self, context):
        Scene = context.scene
        preview_webcam_operations(
            action = 'snapshot',
            host = Scene.octoprint_host,
            port = Scene.octoprint_camera_port,
            user = Scene.octoprint_user,
            passphrase = Scene.octoprint_pass,
            snapshot_dir = Scene.octoprint_snapshot_dir,
            snapshot_name = Scene.octoprint_snapshot_name,
            preview_xy_scale = Scene.octoprint_preview_xy_scale,
            snapshot_action = Scene.octoprint_snapshot_action,
            stream_action = Scene.octoprint_stream_action,
            preview_placement = Scene.octoprint_preview_placement,
            preview_layer = Scene.octoprint_preview_layer,
            target_screen = Scene.octoprint_target_screen,
            target_3dview = Scene.octoprint_target_3dview,
            curl_exec_dir = Scene.curl_exec_dir,
            curl_exec_name = Scene.curl_exec_name,
            log_level = Scene.log_level)

        info = ('Finished')
        self.report({'INFO'}, info)
        return {'FINISHED'}


class octoprint_stream_webcam_button(Operator):
    """Preform some more magic so users can see stream of build plate of their printer without leaving Blender"""
    bl_idname = 'object.octoprint_stream_webcam_button'
    bl_label = 'Preview Build Plate'

    def execute(self, context):
        Scene = context.scene
        preview_webcam_operations(
            action = 'stream',
            host = Scene.octoprint_host,
            port = Scene.octoprint_camera_port,
            user = Scene.octoprint_user,
            passphrase = Scene.octoprint_pass,
            snapshot_dir = Scene.octoprint_snapshot_dir,
            snapshot_name = Scene.octoprint_snapshot_name,
            preview_xy_scale = Scene.octoprint_preview_xy_scale,
            snapshot_action = Scene.octoprint_snapshot_action,
            stream_action = Scene.octoprint_stream_action,
            preview_placement = Scene.octoprint_preview_placement,
            preview_layer = Scene.octoprint_preview_layer,
            target_screen = Scene.octoprint_target_screen,
            target_3dview = Scene.octoprint_target_3dview,
            curl_exec_dir = Scene.curl_exec_dir,
            curl_exec_name = Scene.curl_exec_name,
            log_level = Scene.log_level,
            button_background_color = Scene.button_background_color,
            button_text_color = Scene.button_text_color)

        info = ('Finished')
        self.report({'INFO'}, info)
        return {'FINISHED'}


class repetier_preview_webcam_button(Operator):
    """Preform some magic so users can see snapshot of build plate of their printer without leaving Blender"""
    bl_idname = 'object.repetier_preview_webcam_button'
    bl_label = 'Preview Build Plate'

    def execute(self, context):
        Scene = context.scene
        preview_webcam_operations(
            action = 'snapshot',
            host = Scene.repetier_host,
            port = Scene.repetier_camera_port,
            user = Scene.repetier_user,
            passphrase = Scene.repetier_pass,
            snapshot_dir = Scene.repetier_snapshot_dir,
            snapshot_name = Scene.repetier_snapshot_name,
            preview_xy_scale = Scene.repetier_preview_xy_scale,
            snapshot_action = Scene.repetier_snapshot_action,
            stream_action = Scene.repetier_stream_action,
            preview_placement = Scene.repetier_preview_placement,
            preview_layer = Scene.repetier_preview_layer,
            target_screen = Scene.repetier_target_screen,
            target_3dview = Scene.repetier_target_3dview,
            curl_exec_dir = Scene.curl_exec_dir,
            curl_exec_name = Scene.curl_exec_name,
            log_level = Scene.log_level)

        info = ('Finished')
        self.report({'INFO'}, info)
        return {'FINISHED'}


class repetier_stream_webcam_button(Operator):
    """Preform some more magic so users can see stream of build plate of their printer without leaving Blender"""
    bl_idname = 'object.repetier_stream_webcam_button'
    bl_label = 'Preview Build Plate'

    def execute(self, context):
        Scene = context.scene
        preview_webcam_operations(
            action = 'stream',
            host = Scene.repetier_host,
            port = Scene.repetier_camera_port,
            user = Scene.repetier_user,
            passphrase = Scene.repetier_pass,
            snapshot_dir = Scene.repetier_snapshot_dir,
            snapshot_name = Scene.repetier_snapshot_name,
            preview_xy_scale = Scene.repetier_preview_xy_scale,
            snapshot_action = Scene.repetier_snapshot_action,
            stream_action = Scene.repetier_stream_action,
            preview_placement = Scene.repetier_preview_placement,
            preview_layer = Scene.repetier_preview_layer,
            target_screen = Scene.repetier_target_screen,
            target_3dview = Scene.repetier_target_3dview,
            curl_exec_dir = Scene.curl_exec_dir,
            curl_exec_name = Scene.curl_exec_name,
            log_level = Scene.log_level,
            button_background_color = Scene.button_background_color,
            button_text_color = Scene.button_text_color)

        info = ('Finished')
        self.report({'INFO'}, info)
        return {'FINISHED'}


#-------------------------------------------------------------------------
#    Actions to take when "Upload Selected as STL" button is pressed
#-------------------------------------------------------------------------
class curl_test_button(Operator):
    """Test a curl command from within Blender"""
    bl_idname = 'object.curl_test_button'
    bl_label = 'Curl test command'

    def execute(self, context):
        Scene = context.scene
        curl_test_operations(
            curl_ops = Scene.curl_test_ops,
            curl_exec_dir = Scene.curl_exec_dir,
            curl_exec_name = Scene.curl_exec_name,
            log_level = Scene.log_level)

        info = ('Finished sending the following to curl: {0}'.format(Scene.curl_test_ops))
        self.report({'INFO'}, info)
        return {'FINISHED'}


#-------------------------------------------------------------------------
#   
#-------------------------------------------------------------------------
class octoprint_download_file_list_button(Operator):
    """Download a list of files from OctoPrint server"""
    bl_idname = 'object.octoprint_download_file_list'
    bl_label = 'OctoPrint Download File List'

    def execute(self, context):
        if not context.selected_objects:
            raise Exception('Please select some objects first.')

        Scene = context.scene

        parsed_json = octoprint_return_json_file_listing(
            octoprint_host=Scene.octoprint_host,
            octoprint_x_api_key=Scene.octoprint_x_api_key,
            octoprint_port=Scene.octoprint_port,
            octoprint_user=Scene.octoprint_user,
            octoprint_pass=Scene.octoprint_pass,
            curl_exec_dir = Scene.curl_exec_dir,
            curl_exec_name = Scene.curl_exec_name,
            log_level = Scene.log_level,
            tmp_dir = Scene.octoprint_snapshot_dir)

        for dir in parsed_json['files']:
            for file in dir['children']:
                print('#########')
    #            print('# File:', file)
    #            print('## Refs:', file['refs'])
                print('## Refs Resource:', file['refs']['resource'])
                if file['type'] != 'folder':
                    print('## Refs Download:', file['refs']['download'])

                print('## Mount:', file['origin'])
                print('## Type:', file['type'])
                print('## Size:', file['size'])
                print('## Name:', file['name'])
                if file['type'] == 'machinecode':
    #                print('### GCode Analysis:', file['gcodeAnalysis'])
                    print('### GCode Analysis Filament:', file['gcodeAnalysis']['filament'])
                    for count, tool in enumerate(file['gcodeAnalysis']['filament']):
                        print('#### Tool #{0}'.format(count))
                        print('#### Length:', file['gcodeAnalysis']['filament'][tool]['length'])
                        print('#### Volume:', file['gcodeAnalysis']['filament'][tool]['volume'])

                    print('#### Dimensions Depth:', file['gcodeAnalysis']['dimensions']['depth'])
                    print('#### Dimensions Height:', file['gcodeAnalysis']['dimensions']['height'])
                    print('#### Dimensions Width:', file['gcodeAnalysis']['dimensions']['width'])
                    print('#### Printing Area Max Y:', file['gcodeAnalysis']['printingArea']['maxY'])
                    print('#### Printing Area Min Y:', file['gcodeAnalysis']['printingArea']['minY'])
                    print('#### Printing Area Max X:', file['gcodeAnalysis']['printingArea']['maxX'])
                    print('#### Printing Area Min X:', file['gcodeAnalysis']['printingArea']['minX'])
                    print('#### Printing Area Max Z:', file['gcodeAnalysis']['printingArea']['maxZ'])
                    print('#### Printing Area Min Z:', file['gcodeAnalysis']['printingArea']['minZ'])
                    print('#### Estimated Print Time:', file['gcodeAnalysis']['estimatedPrintTime'])
                elif file['type'] == 'model':
                    print('## Hash:', file['hash'])
                    print('## Date:', file['date'])

                print('## Display', file['display'])
                print('## Path:', file['path'])
                print('## Type Path:', file['typePath'])


        info = ('Finished')
        self.report({'INFO'}, info)
        return {'FINISHED'}


#-------------------------------------------------------------------------
#    Register & un-register configs, note order determines initial layout of panels
#-------------------------------------------------------------------------
classes = (
    import_settings,
    export_settings,
    slic3r_settings,
    curl_settings,
    curaengine_settings,
    octoprint_settings,
    repetier_settings,
    misc_settings,
    octoprint_preview_webcam_settings,
    repetier_preview_webcam_settings,

    slic3r_repair_button,
    slic3r_slice_button,
    curaengine_slice_button,
    octoprint_mkdir_button,
    octoprint_upload_stl_button,
    curl_test_button,
    octoprint_preview_webcam_button,
    octoprint_stream_webcam_button,
    repetier_stream_webcam_button,
    repetier_preview_webcam_button,
    octoprint_download_file_list_button,

    quick_slicer_tools_buttons_panel,
    print_server_buttons_panel,
    export_stl_config_panel,
    import_obj_config_panel,
    slicer_config_panel,
    curl_config_panel,
    print_server_connection_config_panel,
    print_server_slicer_config_panel,
    preview_webcam_config_panel)

#    curl_test_panel,

#-------------------------------------------------------------------------
#   Register classes and other UI stuff
#-------------------------------------------------------------------------
def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.utils.register_manual_map(swiftTo3Dprint_manual_map)


#-------------------------------------------------------------------------
#   Un-register classes and other UI stuff
#-------------------------------------------------------------------------
def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    bpy.utils.unregister_manual_map(swiftTo3Dprint_manual_map)


#-------------------------------------------------------------------------
#    Registration configuration
#-------------------------------------------------------------------------
def menu_func(self, context):
    layout = self.layout
    layout.operator(quick_slicer_tools_buttons_panel.bl_idname)
    layout.operator(export_stl_config_panel.bl_idname)
    layout.operator(import_obj_config_panel.bl_idname)
    layout.operator(slicer_config_panel.bl_idname)
    layout.operator(curl_config_panel.bl_idname)
    layout.operator(curl_test_panel.bl_idname)
    layout.operator(print_server_buttons_panel.bl_idname)
    layout.operator(print_server_connection_config_panel.bl_idname)
    layout.operator(print_server_slicer_config_panel.bl_idname)
    layout.operator(preview_webcam_config_panel.bl_idname)


#-------------------------------------------------------------------------
#    Configs & user UI layout above, addon scripted logics bellow
#-------------------------------------------------------------------------


#-------------------------------------------------------------------------
#   Makes a named parent if none is present and parents selected object to empty
#-------------------------------------------------------------------------
def blender_parent_to_named_empty(empty_name=''):
    """
    # empty_name should be a string and is set by the user in the
    #  Quick Slicer Tools panel of this addon by editing the
    #  Repaired Parent Name text box.
    # This fancyness of a named empty parent requires the
    #  addon 'Add Mesh: Extra Objects'
    """
    if bpy.data.objects.get(empty_name) is None:
        bpy.ops.object.parent_to_empty(nombre=empty_name)
    else:
        bpy.context.scene.objects.active = bpy.data.objects[empty_name]
        bpy.ops.object.parent_set(type='OBJECT')

    bpy.data.objects[empty_name].select = False


#-------------------------------------------------------------------------
#   Exports selected objects in STL format
#-------------------------------------------------------------------------
def blender_export_stl(
        stl_path='',
        axis_forward='',
        axis_up='',
        export_stl_ascii='',
        export_stl_check_existing='',
        export_stl_global_scale='',
        export_stl_use_scene_unit=''):

    blender_version_main = bpy.app.version[0]
    blender_version_sub = bpy.app.version[1]

    if blender_version_main is 2 and blender_version_sub >= 77:
        bpy.ops.export_mesh.stl(
            filepath=stl_path, check_existing=export_stl_check_existing,
            axis_forward=axis_forward, axis_up=axis_up,
            filter_glob='*.stl', use_selection=True, global_scale=export_stl_global_scale,
            use_scene_unit=export_stl_use_scene_unit, ascii=export_stl_ascii,
            use_mesh_modifiers=True, batch_mode='OFF')

    elif blender_version_main is 2 and blender_version_sub <= 76:
        bpy.ops.export_mesh.stl(
            filepath=stl_path, check_existing=export_stl_check_existing,
            axis_forward=axis_forward, axis_up=axis_up,
            filter_glob='*.stl', global_scale=export_stl_global_scale,
            use_scene_unit=export_stl_use_scene_unit, ascii=export_stl_ascii,
            use_mesh_modifiers=True)


#-------------------------------------------------------------------------
#   Imports OBJ file at given 'obj_path'
#-------------------------------------------------------------------------
def blender_import_obj(
        obj_path='',
        axis_forward='',
        axis_up='',
        useEdges='',
        useSmoothGroups='',
        useSplitObjects='',
        useSplitGroups='',
        useGroupsAsVgroups='',
        useImageSearch='',
        splitMode='',
        globalClampSize=''):

    if os.path.exists(obj_path):
        bpy.ops.import_scene.obj(
            filepath=obj_path, axis_forward=axis_forward,
            axis_up=axis_up, filter_glob="*.obj;*.mtl",
            use_edges=useEdges, use_smooth_groups=useSmoothGroups,
            use_split_objects=useSplitObjects, use_split_groups=useSplitGroups,
            use_groups_as_vgroups=useGroupsAsVgroups, use_image_search=useImageSearch,
            split_mode=splitMode, global_clamp_size=globalClampSize)


#-------------------------------------------------------------------------
#   
#-------------------------------------------------------------------------
def blender_import_gcode_text(filepath=''):
    if os.path.exists(filepath):
        filename = bpy.path.basename(filepath)
    else:
        raise Exception('Function: blender_import_text needs a file path to import text from.')

    text_block = bpy.data.texts.get(filename)
    if text_block is None:
        bpy.ops.text.open(filepath=filepath)
        bpy.data.texts[-1].name = filename
        text_block = bpy.data.texts[filename]
    else:
        bpy.data.texts[filename].clear()
        bpy.data.texts.remove(text_block)
        bpy.ops.text.open(filepath=filepath)


#-------------------------------------------------------------------------
#   
#-------------------------------------------------------------------------
def blender_webcam_import_local_image(filename='', directory=''):
    """
    # This will be simplified as "img_file_path='/some/path.some.jpg'"
    # For now know the order of operations if a preview image are nesisary
    #  to avoid over complicating the linking processes called by parent functions.
    """
    img = bpy.data.images.get(filename)
    if img is None:
        bpy.data.images.load(os.path.join(directory, filename))
        bpy.data.images[-1].name = filename
    else:
        # Note the object still must reload for this to work
        bpy.data.images[filename].reload()


#-------------------------------------------------------------------------
#   
#-------------------------------------------------------------------------
def blender_materialize_object(material_name='', object_name='', diffuse_color=None, use_shadeless=True):
    obj = bpy.data.objects.get(object_name)

    # Setup new material if none exists for button text
    mat = bpy.data.materials.get(material_name)
    if mat is None:
        mat = bpy.data.materials.new(name=material_name)

    if diffuse_color is not None:
        # Note by addressing the first three this avoides errors with feeding longer lists
        #  while this will mean that collors between BGE & Textured Object mode
        #  it also means that there will be buttons with visable & customizable colors
        mat.diffuse_color = (diffuse_color[0], diffuse_color[1], diffuse_color[2])

    # Assign or update material on button plane
    obj_mat = obj.data.materials.get(material_name)
    if obj_mat is None:
        obj.data.materials.append(mat)
        obj_mat = obj.data.materials.get(material_name)
    else:
        obj.data.materials[0] = mat

    obj.active_material.use_shadeless = use_shadeless


#-------------------------------------------------------------------------
#   
#-------------------------------------------------------------------------
def blender_webcam_add_view_plane(
        image_name='',
        video_object_name='',
        video_material_name='',
        video_texture_name='',
        x_dimension='',
        y_dimension='',
        xy_scale='',
        preview_placement='',
        preview_layer=''):

    obj = bpy.data.objects.get(video_object_name)
    if obj is None:
        layers = []
        for count in range(0, 20):
            if count != preview_layer:
                layers += [False]
            else:
                layers += [True]
        bpy.ops.mesh.primitive_plane_add(layers=layers)
        bpy.context.object.name = video_object_name
        ## The above seems to work but will fail if this addon is called from the command line instead of UI
        ## The following would fail to target at all
#        bpy.data.meshes[-1].name = video_object_name
        ## The following would target Suzanne & other objects
#        bpy.data.objects[-1].name = video_object_name
        obj = bpy.data.objects.get(video_object_name)
    if obj is None:
        raise Exception('Could not create/target correct preview plane')

    obj_dims = obj.dimensions
    obj.dimensions = x_dimension/xy_scale, y_dimension/xy_scale, obj_dims[2]
    
    if 'NORTH' in preview_placement:
        obj.location[1] = obj.dimensions[1]/2
    elif 'EAST' in preview_placement:
        obj.location[0] = obj.dimensions[0]/2
    elif 'SOUTH' in preview_placement:
        obj.location[1] = -obj.dimensions[1]/2
    elif 'WEST' in preview_placement:
        obj.location[0] = -obj.dimensions[0]/2

    blender_materialize_object(material_name=video_material_name, object_name=video_object_name, diffuse_color=[0, 0, 0], use_shadeless=True)
    mat = bpy.data.materials.get(video_material_name)
    obj_mat = obj.data.materials.get(video_material_name)

    tex = bpy.data.textures.get(video_texture_name)
    if tex is None:
        tex = bpy.data.textures.new(video_texture_name, 'IMAGE')

    mat_slots = mat.texture_slots.get(video_texture_name)
    if mat_slots is None:
        mat_slots = mat.texture_slots.add()

    mat_slots.texture = tex

    tex.image = bpy.data.images[image_name]
    obj.data.materials[video_material_name].texture_slots[video_texture_name].texture_coords = 'ORCO'

#    obj.active_material.use_shadeless = True
    ## Following is to update object if this is not the first time the preview/stream button has been pressed
    bpy.data.objects[video_object_name].data.update()
    ## Following is to update the scene to all the changes required to view an image on a plane within Blender
    bpy.context.scene.update()


#-------------------------------------------------------------------------
#   
#-------------------------------------------------------------------------
def blender_webcam_setup_script_text_block(
        controller_script_name='',
        default_image='',
        video_path=''):

    text_block = bpy.data.texts.get(controller_script_name)
    if text_block is None:
        bpy.ops.text.new()
        bpy.data.texts[-1].name = controller_script_name
        text_block = bpy.data.texts[controller_script_name]
    bpy.data.texts[controller_script_name].clear()

    # Now we can write line by line what should be in here
    #  note, new-line feeds are not assumed, eg "\n" is required
    #text_block.write('some text with a new line\n')
    # In this case we are going to write a script for playing
    # video sources onto an object texture in with Blender Game Engine
    ## Note the following seems to work on Blender version 2.76 or lower
    text_block.write('#!/usr/bin/env python\n')
    text_block.write('import bge\n')
    text_block.write('cont = bge.logic.getCurrentController()\n')
    text_block.write('obj = cont.owner\n')
    text_block.write('def main():\n')
    text_block.write('    if not hasattr(bge.logic, "video"):\n')
    text_block.write('        bge.render.showMouse(True)\n')
    text_block.write('        ID = bge.texture.materialID(obj, "IM{0}")\n'.format(default_image))
    text_block.write('        bge.logic.video = bge.texture.Texture(obj, ID)\n')
#    if camera_addr:
#        text_block.write("        bge.logic.video.source = bge.texture.VideoFFmpeg('{0}', 0)\n".format(camera_addr))
#    elif video_path:
    text_block.write("        bge.logic.video.source = bge.texture.VideoFFmpeg('{0}')\n".format(video_path))
    text_block.write('        bge.logic.video.source.play()\n')
    text_block.write('    bge.logic.video.refresh(True)\n')
    text_block.write('main()')


#-------------------------------------------------------------------------
#   
#-------------------------------------------------------------------------
def blender_webcam_setup_game_logic(
        video_object_name='',
        sensor_name='',
        controller_name='',
        controller_script_name=''):

    # Set-up game Sensor for object
    vid_obj_sensor = bpy.data.objects[video_object_name].game.sensors.get(sensor_name)
    if vid_obj_sensor is None:
        bpy.ops.logic.sensor_add(type='ALWAYS', name=sensor_name, object=video_object_name)
        vid_obj_sensor = bpy.data.objects[video_object_name].game.sensors.get(sensor_name)
    vid_obj_sensor.use_pulse_true_level = True

    # Set-up game Controller for object
    vid_obj_controller = bpy.data.objects[video_object_name].game.controllers.get(controller_name)
    if vid_obj_controller is None:
        bpy.ops.logic.controller_add(type='PYTHON', name = controller_name, object = video_object_name)
        vid_obj_controller = bpy.data.objects[video_object_name].game.controllers.get(controller_name)
    vid_obj_controller.text = bpy.data.texts[controller_script_name]

    # Link things together
    vid_obj_sensor.link(vid_obj_controller)


#-------------------------------------------------------------------------
#   
#-------------------------------------------------------------------------
def blender_button_setup_game_logic(
        object_name='',
        actuator_type='GAME',
        actuator_mode='QUIT'):

    sensor_click_name = object_name + '_Sensor_Click'
    sensor_mouseover_name = object_name + '_Sensor_Mouse_Over'
    controller_name = object_name + '_Controller'
    actuator_name = object_name + '_Actuator'

    # Make two sensors for mouse events
    click_sensor = bpy.data.objects[object_name].game.sensors.get(sensor_click_name)
    if click_sensor is None:
        bpy.ops.logic.sensor_add(type='MOUSE', name = sensor_click_name, object = object_name)
        click_sensor = bpy.data.objects[object_name].game.sensors.get(sensor_click_name)

    click_sensor.mouse_event = 'LEFTCLICK'

    mouseover_sensor = bpy.data.objects[object_name].game.sensors.get(sensor_mouseover_name)
    if mouseover_sensor is None:
        bpy.ops.logic.sensor_add(type='MOUSE', name = sensor_mouseover_name, object = object_name)
        mouseover_sensor = bpy.data.objects[object_name].game.sensors.get(sensor_mouseover_name)

    mouseover_sensor.mouse_event = 'MOUSEOVER'

    # Make an AND controller
    controller = bpy.data.objects[object_name].game.controllers.get(controller_name)
    if controller is None:
        bpy.ops.logic.controller_add(type='LOGIC_AND', name = controller_name, object = object_name)
        controller = bpy.data.objects[object_name].game.controllers.get(controller_name)

    # Link the sensors to controller
    click_sensor.link(controller)
    mouseover_sensor.link(controller)

    # Make an actuator
    actuator = bpy.data.objects[object_name].game.actuators.get(actuator_name)
    if actuator is None:
        bpy.ops.logic.actuator_add(type = actuator_type, name = actuator_name, object = object_name)
        actuator = bpy.data.objects[object_name].game.actuators.get(actuator_name)

    actuator.mode = actuator_mode

    # Link controller to actuator
    actuator.link(controller)

#-------------------------------------------------------------------------
#   
#-------------------------------------------------------------------------
def blender_webcam_add_button_text(
        text_name='',
        text_body='',
        preview_layer='',
        location='',
        button_background_color='',
        button_text_color=''):

    plane_name = text_name + '_Plane'
    plane_material_name = text_name + '_Plane_Material'
    text_material_name = text_name + '_Text_Material'

    # Deselect all meshes
    bpy.ops.object.select_all(action='DESELECT')
    text_obj = bpy.data.objects.get(text_name)
    if text_obj is None:
        layers = []
        for count in range(0, 20):
            if count != preview_layer:
                layers += [False]
            else:
                layers += [True]
        bpy.ops.object.text_add(layers=layers)
        bpy.data.objects[-1].name = text_name
        text_obj = bpy.data.objects.get(text_name)

    text_obj.data.body = text_body
    # Set origin to geometry
    bpy.ops.object.origin_set(type='GEOMETRY_ORIGIN', center='MEDIAN')
    text_obj.location = (text_obj.location[0], text_obj.location[1], location[2])
    text_dimensions = text_obj.dimensions

    # Deselect all meshes
    bpy.ops.object.select_all(action='DESELECT')
    # Add plane under & size it
    plane_obj = bpy.data.objects.get(plane_name)
    if plane_obj is None:
        layers = []
        for count in range(0, 20):
            if count != preview_layer:
                layers += [False]
            else:
                layers += [True]
        bpy.ops.mesh.primitive_plane_add(layers=layers)
        bpy.context.object.name = plane_name
        plane_obj = bpy.data.objects.get(plane_name)

    # Lower left
    plane_obj.data.vertices[0].co = (-text_dimensions[0]/2, -text_dimensions[1]/2, text_obj.location[2])
    # Lower right
    plane_obj.data.vertices[1].co = (text_dimensions[0]/2, -text_dimensions[1]/2, text_obj.location[2])
    # Upper left
    plane_obj.data.vertices[2].co = (-text_dimensions[0]/2, text_dimensions[1]/2, text_obj.location[2])
    # Upper right
    plane_obj.data.vertices[3].co = (text_dimensions[0]/2, text_dimensions[1]/2, text_obj.location[2])

    # Parent text to plane
    text_obj.parent = plane_obj
    plane_obj.location = (location[0], location[1], location[2]/2)
    text_obj.location = (text_obj.location[0], text_obj.location[1], text_obj.location[2]+0.5)

    # Colorize text & background for while in BGE
    text_obj.color = button_text_color
    plane_obj.color = button_background_color

    # Assign material to text & background plane for while in textured object mode
    blender_materialize_object(material_name=text_material_name, object_name=text_name, diffuse_color = button_text_color, use_shadeless=True)
    blender_materialize_object(material_name=plane_material_name, object_name=plane_name, diffuse_color = button_background_color, use_shadeless=True)


#-------------------------------------------------------------------------
#   
#-------------------------------------------------------------------------
def blender_3dview_modify_viewport(
        animate='',
        preview_layer='',
        target_screen='',
        target_3dview=''):

    viewport_shade='TEXTURED'
    bpy.context.scene.render.engine = Target_render_engine
    bpy.context.scene.game_settings.material_mode = Target_material_mode
    areas = bpy.data.screens[target_screen].areas
    for area in areas:
        if area.type == 'VIEW_3D':
            bpy.ops.object.mode_set(mode='OBJECT')
            override = bpy.context.copy()
            override['area'] = area
            for counter, space in enumerate(area.spaces):
                if space.type == 'VIEW_3D' and target_3dview == counter:
                    space.viewport_shade = Target_viewport_shade
                    for count, layer in enumerate(space.layers):
                        if count != preview_layer:
                            layer = False
                        else:
                            layer = True

            if animate == True:
                bpy.ops.view3d.game_start()
                break


#-------------------------------------------------------------------------
#    Makes directories at a given 'path'
#-------------------------------------------------------------------------
def mkdir(dir_path=''):
    if not os.path.exists(dir_path):

        blender_version_main = bpy.app.version[0]
        blender_version_sub = bpy.app.version[1]

        #if blender_version_main is 2 and blender_version_sub >= 77:
        #    print('# Using bpy.ops.file.directory_new to make the following directory path #')
        #    print(dir_path)
        #    bpy.ops.file.directory_new(dir_path)
        #elif blender_version_main is 2 and blender_version_sub <= 76:
        print('# Using os.makedirs to make the following directory path #')
        print(dir_path)
        os.makedirs(dir_path)


#-------------------------------------------------------------------------
#   Removes temp files at a given 'path'
#-------------------------------------------------------------------------
def rm(path=''):
    if os.path.exists(path):
        print('# Using os.remove to remove the following path #')
        print(path)
        os.remove(path)


#-------------------------------------------------------------------------
#   Curl is used for most of the OctoPrint features at this point, side note; this trick does **not** work with slci3r
#-------------------------------------------------------------------------
def curl(ops=[], log_ops=[], exec_dir='', exec_name=''):
    if os.path.exists(exec_dir):
        curl_array = [os.path.join(exec_dir, curl_exec_name)]
    else:
        curl_array = [curl_exec_name]
    if ops:
        curl_array.extend(ops)
        # Comment the next two lines to silence curl command preview
        if log_ops:
            print('# Using subprocess.checkcall to call Curl with the following options #')
            print(log_ops)
        subprocess.check_call(curl_array)
    else:
        raise Exception('No options supplied for curl')


#-------------------------------------------------------------------------
#   Slic3r is used for local slicing of exported STL files from Blender selected objects
#-------------------------------------------------------------------------
def slic3r(ops=[], exec_dir='', exec_name=''):
    if os.path.exists(exec_dir):
        slic3r_array = [os.path.join(exec_dir, exec_name)]
    else:
        slic3r_array = [exec_name]
    if ops:
        slic3r_array.extend(ops)
        print('# Using subprocess.checkcall to call Slic3r with the following options #')
        print(slic3r_array)
        subprocess.check_call(slic3r_array)
    else:
        raise Exception('No options supplied for slic3r')


#-------------------------------------------------------------------------
#   CuraEngine is used for local slicing of exported STL files from Blender selected objects
#-------------------------------------------------------------------------
def curaengine(ops=[], exec_dir='', exec_name=''):
    if os.path.exists(exec_dir):
        curaEngine_array = [os.path.join(exec_dir, curaengine_exec_name)]
    else:
        curaEngine_array = [curaengine_exec_name]
    if ops:
        curaEngine_array.extend(ops)
        print('# Using subprocess.checkcall to call CuraEngine with the following options #')
        print(curaEngine_array)
        subprocess.check_call(curaEngine_array)
    else:
        raise Exception('No options supplied for CuraEngine')


#-------------------------------------------------------------------------
#   Executes 'slci3r --repair' on STL file at given 'stl_path'
#-------------------------------------------------------------------------
def slic3r_repair_stl(stl_path='', exec_dir='', exec_name=''):
    if os.path.exists(stl_path):
        slic3r(exec_dir = exec_dir, exec_name = exec_name, ops = ['--repair', stl_path])
    else:
        raise Exception('No STL file supplied for Slic3r to repair')


def curl_download_snapshot(
        url='',
        download_path='',
        auth_user='',
        auth_pass='',
        curl_exec_dir='',
        curl_exec_name='',
        log_level=''):

    curl_ops = ['-k', '--connect-timeout', '15']
    curl_log = []
    if log_level != 'QUITE':
        curl_log.extend(curl_ops)

    if auth_user and auth_pass:
        curl_ops += ['-u', '{0}:{1}'.format(auth_user, auth_pass)]
        if log_level == 'VERBOSE':
            curl_log += ['-u', '{0}:{1}'.format(auth_user, auth_pass)]
        elif log_level == 'SCRUBBED':
            curl_log += ['-u', 'USER:PASS']

    curl_ops += ['-o', download_path, url]
    if log_level == 'VERBOSE':
        curl_log += ['-o', download_path, url]
    elif log_level == 'SCRUBBED':
        curl_log += ['-o', 'DOWNLOAD_PATH', 'URL']

    curl(
        exec_dir = curl_exec_dir,
        exec_name = curl_exec_name,
        ops = curl_ops,
        log_ops = curl_log)


def octoprint_return_json_file_listing(
        octoprint_host='',
        octoprint_x_api_key='',
        octoprint_port='',
        octoprint_user='',
        octoprint_pass='',
        curl_exec_dir='',
        curl_exec_name='',
        log_level='',
        tmp_dir=''):

    json_file_path = os.path.join(tmp_dir, 'file_list.json')

    if octoprint_port:
        host_url = octoprint_host + ':' + octoprint_port

    curl_ops = ['-k', '--connect-timeout', '15']
    curl_log = []
    if log_level != 'QUITE':
        curl_log.extend(curl_ops)

    if octoprint_x_api_key:
        curl_ops += ['-H', 'X-Api-Key: {0}'.format(octoprint_x_api_key)]
        if log_level == 'VERBOSE':
            curl_log += ['-H', 'X-Api-Key: {0}'.format(octoprint_x_api_key)]
        elif log_level == 'SCRUBBED':
            curl_log += ['-H', 'X-Api-Key: X-API-KEY']

    if octoprint_user and octoprint_pass:
        curl_ops += ['-u', '{0}:{1}'.format(octoprint_user, octoprint_pass)]
        if log_level == 'VERBOSE':
            curl_log += ['-u', '{0}:{1}'.format(octoprint_user, octoprint_pass)]
        elif log_level == 'SCRUBBED':
            curl_log += ['-u', 'USER:PASS']

    curl_ops += ['{0}/api/files?recursive=true'.format(host_url), '-o', json_file_path]
    if log_level != 'QUITE':
        curl_log += ['{0}/api/files?recursive=true'.format(host_url), '-o', json_file_path]

    curl(exec_dir = curl_exec_dir, exec_name = curl_exec_name, ops = curl_ops, log_ops = curl_log)
    if os.path.exists(json_file_path):
        with open(json_file_path) as json_file:
            parsed_json = json.load(json_file)
        return parsed_json
    else:
        raise Exception('Could not find json file: {0}'.format(json_file_path))


#-------------------------------------------------------------------------
#   Slices local STL files into GCODE file(s) vie Slic3r or CuraEngine
#-------------------------------------------------------------------------
def slice_stl_to_gcode_locally(
        stl_path = [],
        gcode_dir='',
        export_as_individual='',
        slicer='',
        curaengine_conf='',
        curaengine_extra_args='',
        curaengine_exec_dir='',
        curaengine_exec_name='',
        slic3r_conf='',
        slic3r_post_script='',
        slic3r_extra_args='',
        slic3r_exec_dir='',
        slic3r_exec_name=''):

    if 'Merge' in export_as_individual:
        stl_dir = os.path.dirname(stl_path[0])
        if bpy.data.is_saved is True:
            gcode_name = str((bpy.path.basename(bpy.context.blend_data.filepath) + '.gcode'))
        else:
            gcode_name = str(('Untitled' + '.gcode'))
    else:
        stl_dir = os.path.dirname(stl_path)
        stl_name = bpy.path.display_name_from_filepath(stl_path)
        gcode_name = '{0}.gcode'.format(stl_name)

    if gcode_dir != stl_dir:
        gcode_path = os.path.join(gcode_dir, gcode_name)
    else:
        gcode_path = os.path.join(stl_dir, gcode_name)

    if 'CuraEngine' in slicer:
        args = []
        if os.path.exists(curaengine_conf):
            args += ['-j', curaengine_conf]
        if curaengine_extra_args:
            extra_args = []
            for arg in enumerate(curaengine_extra_args.split(' ')):
                extra_args += [arg[1]]
            print('# CuraEngine extra_args: {0}'.format(extra_args))
            args.extend(extra_args)
        if 'Merge' in export_as_individual:
            for stl in stl_path:
                args += ['-l']
                args += [stl]
        else:
            args += [stl_path]
        args += ['-o', gcode_path]
        curaengine(exec_dir = curaengine_exec_dir, exec_name = curaengine_exec_name, ops = args)

    elif 'Slic3r' in slicer:
        args = []
        if os.path.exists(slic3r_conf):
            args += ['--load', slic3r_conf]
        args += ['--output', gcode_path]
        if os.path.exists(slic3r_post_script):
            args += ['--post-process', slic3r_post_script]
        if slic3r_extra_args:
            extra_args = []
            for arg in enumerate(slic3r_extra_args.split(' ')):
                extra_args += [arg[1]]
            print('# Slic3r extra args: {0}'.format(extra_args))
            args.extend(extra_args)
        if 'Merge' in export_as_individual:
            args += ['--merge']
            args.extend(stl_path)
        else:
            args += [stl_path]
        slic3r(exec_dir = slic3r_exec_dir, exec_name = slic3r_exec_name, ops = args)


#-------------------------------------------------------------------------
#   Uploads GCode to an OctoPrint server
#-------------------------------------------------------------------------
def octoprint_upload_file(
        gcode_path='',
        stl_path='',
        host_url='',
        api_path='',
        xapi_key='',
        host_port='',
        user_name='',
        passphrase='',
        gcode_dir='',
        stl_dir='',
        curl_exec_dir='',
        curl_exec_name='',
        log_level=''):

    if gcode_path:
        file_name = bpy.path.basename(gcode_path)
    elif stl_path:
        file_name = bpy.path.basename(stl_path)

    if host_port:
        host_url = host_url + ':' + host_port
    # Build an array of options to send to curl command
    curl_ops = ['-k', '--connect-timeout', '15', '-H', 'Content-Type: multipart/form-data']
    curl_log = []
    if log_level != 'QUITE':
        curl_log.extend(curl_ops)

    if xapi_key:
        curl_ops += ['-H', 'X-Api-Key: {0}'.format(xapi_key)]
        if log_level == 'VERBOSE':
            curl_log += ['-H', 'X-Api-Key: {0}'.format(xapi_key)]
        elif log_level == 'SCRUBBED':
            curl_log += ['-H', 'X-Api-Key: X-API-KEY']

    if user_name and passphrase:
        curl_ops += ['-u', '{0}:{1}'.format(user_name, passphrase)]
        if log_level == 'VERBOSE':
            curl_log += ['-u', '{0}:{1}'.format(user_name, passphrase)]
        elif log_level == 'SCRUBBED':
            curl_log += ['-u', 'USER:PASS']

    if gcode_path:
        if gcode_dir:
            curl_ops += ['-F', 'path={0}/{1}'.format(gcode_dir, file_name)]
            if log_level != 'QUITE':
                curl_log += ['-F', 'path={0}/{1}'.format(gcode_dir, file_name)]
    elif stl_path:
        if stl_dir:
            curl_ops += ['-F', 'path={0}/'.format(stl_dir)]
            if log_level != 'QUITE':
                curl_log += ['-F', 'path={0}/'.format(stl_dir)]

    if gcode_path:
        curl_ops += ['-F', 'file=@{0}'.format(gcode_path), '{0}{1}'.format(host_url, api_path),]
        if log_level == 'VERBOSE':
            curl_log += ['-F', 'file=@{0}'.format(gcode_path), '{0}{1}'.format(host_url, api_path),]
        elif log_level == 'SCRUBBED':
            curl_log += ['-F', 'file=@{0}'.format(gcode_path), 'HOST{0}'.format(api_path),]
    elif stl_path:
        curl_ops += ['-F', 'file=@{0}'.format(stl_path), '{0}{1}'.format(host_url, api_path),]
        if log_level == 'VERBOSE':
            curl_log += ['-F', 'file=@{0}'.format(stl_path), '{0}{1}'.format(host_url, api_path),]
        elif log_level == 'SCRUBBED':
            curl_log += ['-F', 'file=@{0}'.format(stl_path), 'HOST{0}'.format(api_path),]


    # Attempt to use options with curl
    curl(exec_dir = curl_exec_dir, exec_name = curl_exec_name, ops = curl_ops, log_ops = curl_log)


#-------------------------------------------------------------------------
#   Uploaded selected as STL files to an OctoPrint server
#-------------------------------------------------------------------------
def octoprint_slice_stl(
        stl_path='',
        host_url='',
        api_path='',
        xapi_key='',
        host_port='',
        user_name='',
        passphrase='',
        stl_dir='',
        slice_slicer='',
        slice_printerProfile='',
        slice_Profile='',
        slice_Profile_ops='',
        slice_position_x='',
        slice_position_y='',
        curl_exec_dir = '',
        curl_exec_name = '',
        log_level=''):

#    info = ('Starting OctoPrint Slice STL function')
#    self.report({'INFO'}, info)

    stl_name = bpy.path.basename(stl_path)
    stl_file_name = stl_name.split('.')
    slice_gcode_name = '{0}.gcode'.format(stl_file_name[0])

    if host_port:
        host_url = host_url + ':' + host_port

    # Build an array of options to send to curl command
    # Note: Windows users may need back slashes prior to double quotes bellow, eg: \"
    curl_ops = ['-k', '--connect-timeout', '15', '-X', 'POST', '-H', 'Content-Type: application/json']
    curl_log = []
    if log_level != 'QUITE':
        curl_log.extend(curl_ops)

    if xapi_key:
        curl_ops += ['-H', 'X-Api-Key: {0}'.format(xapi_key)]
        if log_level == 'VERBOSE':
            curl_log += ['-H', 'X-Api-Key: {0}'.format(xapi_key)]
        elif log_level == 'SCRUBBED':
            curl_log += ['-H', 'X-Api-Key: X-API-KEY']

    if user_name and passphrase:
        curl_ops += ['-u', '{0}:{1}'.format(user_name, passphrase)]
        if log_level == 'VERBOSE':
            curl_log += ['-u', '{0}:{1}'.format(user_name, passphrase)]
        elif log_level == 'SCRUBBED':
            curl_log += ['-u', 'USER:PASS']

    # Build slicer json data to send with: curl -d '<key1:val1,key2:val2>' ...
    slicer_ops = ['"command": "{0}", '.format('slice')]
    slicer_ops += ['"slicer": "{0}", '.format(slice_slicer)]
    slicer_ops += ['"gcode": "{0}", '.format(slice_gcode_name)]
    if slice_printerProfile:
        slicer_ops += ['"printerProfile": "{0}", '.format(slice_printerProfile)]
    if slice_Profile:
        slicer_ops += ['"profile": "{0}", '.format(slice_Profile)]
    if slice_Profile_ops:
        profile_ops = []
        for profile_op in enumerate(slice_Profile_ops.split(', ')):
            split_profile_op = profile_op[1].split(':')
            if split_profile_op[0] and split_profile_op[1]:
                # Format and add to main slicer_ops list
                slicer_ops += ['"profile.{0}": {1}, '.format(split_profile_op[0], split_profile_op[1])]
    if slice_position_x and slice_position_y:
        slicer_ops += ['"position": {"x": {0}, "y": {1}}, '.format(slice_position_x, slice_position_y)]
    else:
        slicer_ops += ['"position": {"x": 0, "y": 0}, ']
    slicer_ops += ['"print": false'.format(slicer_ops)]
    # Convert slicer_ops list to string before adding to curl_ops list
    slicer_string = ''.join(slicer_ops)
    curl_ops += ['-d', '{'+slicer_string+'}']
    if log_level != 'QUITE':
        curl_log += ['-d', '{'+slicer_string+'}']

    # Finalize curl options with the URL to the uploaded STL file
    if stl_dir:
        curl_ops += ['{0}{1}/{2}/{3}'.format(host_url, api_path, stl_dir, stl_name)]
        if log_level == 'VERBOSE':
            curl_log += ['{0}{1}/{2}/{3}'.format(host_url, api_path, stl_dir, stl_name)]
        elif log_level == 'SCRUBBED':
            curl_log += ['HOST/{0}/{1}/{2}'.format(api_path, stl_dir, stl_name)]
    else:
        curl_ops += ['{0}{1}/{2}'.format(host_url, api_path, stl_name)]
        if log_level == 'VERBOSE':
            curl_log += ['{0}{1}/{2}'.format(host_url, api_path, stl_name)]
        elif log_level == 'SCRUBBED':
            curl_log += ['HOST/{0}/{1}'.format(api_path, stl_name)]


    # Attempt to use options with curl
    curl(exec_dir=curl_exec_dir, exec_name=curl_exec_name, ops=curl_ops, log_ops=curl_log)


#-------------------------------------------------------------------------
#   Makes a directory or sub-directories on an OctoPrint server
#-------------------------------------------------------------------------
def octoprint_mkdir(
        check_path='',
        host_url='',
        api_path='',
        xapi_key='',
        host_port='',
        user_name='',
        passphrase=''):

    if host_port:
        host_url = host_url + ':' + host_port

    exsistent_dirs = ''
    for dir in enumerate(check_path.split('/')):
        if exsistent_dirs:
            print('# Existent dirs #', exsistent_dirs)
            check_dir = exsistent_dirs + '/' + dir[1]
        else:
            check_dir = dir[1]

        try:
            subprocess.check_output([
                'curl', '-G', '-f', '-k',
                '--connect-timeout', '15',
                '-H', 'X-Api-Key: {0}'.format(xapi_key),
                '-H', 'recursive=true',
                '{0}{1}/{2}'.format(host_url, api_path, check_dir),
            ])
        except subprocess.CalledProcessError as process_error:
            print('# Directory does NOT exist #', dir[1])
            if exsistent_dirs:
                dir_path = exsistent_dirs
                new_dir = dir[1]
                subprocess.check_call([
                    'curl', '-k', '--connect-timeout', '15',
                    '-H', 'Content-Type: multipart/form-data',
                    '-H', 'X-Api-Key: {0}'.format(xapi_key),
                    '-F', 'foldername={0}'.format(new_dir),
                    '-F', 'path={0}'.format(dir_path),
                    '{0}{1}'.format(host_url, api_path),
                ])
            else:
                dir_path = ''
                new_dir = dir[1]
                subprocess.check_call([
                    'curl', '-k', '--connect-timeout', '15',
                    '-H', 'Content-Type: multipart/form-data',
                    '-H', 'X-Api-Key: {0}'.format(xapi_key),
                    '-F', 'foldername={0}'.format(new_dir),
                    '{0}{1}'.format(host_url, api_path),
                ])

        exsistent_dirs += check_dir


#-------------------------------------------------------------------------
#   Uploads GCode to an Repetier server
#-------------------------------------------------------------------------
def repetier_upload_gcode(
        gcode_path='',
        host_url='',
        api_path='',
        xapi_key='',
        host_port='',
        user_name='',
        passphrase='',
        gcode_dir='',
        curl_exec_dir='',
        curl_exec_name='',
        log_level=''):

    file_name = bpy.path.basename(gcode_path)

    if host_port:
        host_url = host_url + ':' + host_port

    # Build an array of options to send to curl command
    curl_ops = ['-i', '-X', 'POST', '--connect-timeout', '15', '-H', 'Content-Type: multipart/form-data']
    curl_log = []
    if log_level != 'QUITE':
        curl_log.extend(curl_ops)

    if xapi_key:
        curl_ops += ['-H', 'x-api-key: {0}'.format(xapi_key)]
        if log_level == 'VERBOSE':
            curl_log += ['-H', 'x-api-key: {0}'.format(xapi_key)]
        elif log_level == 'SCRUBBED':
            curl_log += ['-H', 'x-api-key: X-API-KEY']

    if user_name and passphrase:
        curl_ops += ['-u', '{0}:{1}'.format(user_name, passphrase)]
        if log_level == 'VERBOSE':
            curl_log += ['-u', '{0}:{1}'.format(user_name, passphrase)]
        elif log_level == 'SCRUBBED':
            curl_log += ['-u', 'USER:PASS']

    curl_ops += ['-F', '"a=upload"', '-F', 'filename=@{0}'.format(gcode_path), '{0}{1}/{2}'.format(host_url, api_path, gcode_dir),]
    if log_level == 'VERBOSE':
        curl_log += ['-F', '"a=upload"', '-F', 'filename=@{0}'.format(gcode_path), '{0}{1}/{2}'.format(host_url, api_path, gcode_dir),]
    elif log_level == 'SCRUBBED':
        curl_log += ['-F', '"a=upload"', '-F', 'filename=@{0}'.format(gcode_path), 'HOST/{0}/{1}'.format(api_path, gcode_dir),]

    # Attempt to use options with curl
    curl(exec_dir=curl_exec_dir, exec_name=curl_exec_name, ops=curl_ops, log_ops=curl_log)


#-------------------------------------------------------------------------
#   Loops through selected objects and calls functions for repairing & re-importing
#-------------------------------------------------------------------------
def slic3r_repair_loop(
        selected_objects=[],
        temp_stl_directory='',
        temp_obj_directory='',
        repaired_parent_name='',
        slic3r_exec_dir='',
        slic3r_exec_name='',
        export_stl_axis_forward='',
        export_stl_axis_up='',
        export_stl_ascii='',
        export_stl_check_existing='',
        export_stl_global_scale='',
        export_stl_use_scene_unit='',
        import_obj_axis_forward='',
        import_obj_axis_up='',
        import_obj_use_edges='',
        import_obj_use_smooth_groups='',
        import_obj_use_split_objects='',
        import_obj_use_split_groups='',
        import_obj_use_groups_as_vgroups='',
        import_obj_use_image_search='',
        import_obj_split_mode='',
        import_obj_global_clamp_size=''):

    for object in selected_objects:
        stl_path = os.path.join(temp_stl_directory, object.name + '.stl')
        obj_path = os.path.join(temp_obj_directory, object.name + '_fixed.obj')

        # Deselect all meshes
        bpy.ops.object.select_all(action='DESELECT')
        # Select current object in for loop
        object.select = True
        blender_export_stl(stl_path = stl_path,
            axis_forward = export_stl_axis_forward,
            axis_up = export_stl_axis_up,
            export_stl_ascii = export_stl_ascii,
            export_stl_check_existing = export_stl_check_existing,
            export_stl_global_scale = export_stl_global_scale,
            export_stl_use_scene_unit = export_stl_use_scene_unit)

        # Repair exported STL & import results
        slic3r_repair_stl(exec_dir = slic3r_exec_dir,
            exec_name = slic3r_exec_name,
            stl_path = stl_path)

        blender_import_obj(obj_path = obj_path,
            axis_forward = import_obj_axis_forward,
            axis_up = import_obj_axis_up,
            useEdges = import_obj_use_edges,
            useSmoothGroups = import_obj_use_smooth_groups,
            useSplitObjects = import_obj_use_split_objects,
            useSplitGroups = import_obj_use_split_groups,
            useGroupsAsVgroups = import_obj_use_groups_as_vgroups,
            useImageSearch = import_obj_use_image_search,
            splitMode = import_obj_split_mode,
            globalClampSize = import_obj_global_clamp_size)

        # Hide original object & parent imported object to named empty
        object.hide = True
        blender_parent_to_named_empty(empty_name=repaired_parent_name)

    # Clean up temp STL & OBJ files if enabled.
    for object in selected_objects:
        stl_path = os.path.join(temp_stl_directory, object.name + '.stl')
        obj_path = os.path.join(temp_obj_directory, object.name + '_fixed.obj')

        if bpy.context.scene.clean_temp_stl_files is True:
            rm(path=stl_path)

        if bpy.context.scene.clean_temp_obj_files is True:
            rm(path=obj_path)


#-------------------------------------------------------------------------
#   Much like the loop function of a similar name this function operates on selected objects as a whole
#-------------------------------------------------------------------------
def slic3r_repair_bulk(
        selected_objects=[],
        temp_stl_directory='',
        temp_obj_directory='',
        repaired_parent_name='',
        slic3r_exec_dir='',
        slic3r_exec_name='',
        export_stl_axis_forward='',
        export_stl_axis_up='',
        export_stl_ascii='',
        export_stl_check_existing='',
        export_stl_global_scale='',
        export_stl_use_scene_unit='',
        import_obj_axis_forward='',
        import_obj_axis_up='',
        import_obj_use_edges='',
        import_obj_use_smooth_groups='',
        import_obj_use_split_objects='',
        import_obj_use_split_groups='',
        import_obj_use_groups_as_vgroups='',
        import_obj_use_image_search='',
        import_obj_split_mode='',
        import_obj_global_clamp_size=''):

    if bpy.data.is_saved is True:
        stl_path = os.path.join(temp_stl_directory, bpy.path.basename(bpy.context.blend_data.filepath) + '.stl')
        obj_path = os.path.join(temp_obj_directory, bpy.path.basename(bpy.context.blend_data.filepath) + '_fixed.obj')
    else:
	    stl_path = os.path.join(temp_stl_directory, 'Untitled' + '.stl')
	    obj_path = os.path.join(temp_obj_directory, 'Untitled' + '_fixed.obj')

    blender_export_stl(stl_path = stl_path,
        axis_forward = export_stl_axis_forward,
        axis_up = export_stl_axis_up,
        export_stl_ascii = export_stl_ascii,
        export_stl_check_existing = export_stl_check_existing,
        export_stl_global_scale = export_stl_global_scale,
        export_stl_use_scene_unit = export_stl_use_scene_unit)

    slic3r_repair_stl(exec_dir = slic3r_exec_dir, exec_name = slic3r_exec_name, stl_path = stl_path)

    blender_import_obj(obj_path = obj_path,
        axis_forward = import_obj_axis_forward,
        axis_up = import_obj_axis_up,
        useEdges = import_obj_use_edges,
        useSmoothGroups = import_obj_use_smooth_groups,
        useSplitObjects = import_obj_use_split_objects,
        useSplitGroups = import_obj_use_split_groups,
        useGroupsAsVgroups = import_obj_use_groups_as_vgroups,
        useImageSearch = import_obj_use_image_search,
        splitMode = import_obj_split_mode,
        globalClampSize = import_obj_global_clamp_size)

    for object in selected_objects:
        object.hide = True

    blender_parent_to_named_empty(empty_name = repaired_parent_name)

    if bpy.context.scene.clean_temp_stl_files is True:
        rm(path = stl_path)

    if bpy.context.scene.clean_temp_obj_files is True:
        rm(path = obj_path)


#-------------------------------------------------------------------------
#   Loops through functions to slice selected objects into GCode files via Slic3r
#-------------------------------------------------------------------------
def slice_loop_locally(
        slicer='',
        selected_objects=[],
        stl_dir='',
        gcode_dir='',
        export_as_individual='',
        export_stl_axis_forward='',
        export_stl_axis_up='',
        export_stl_ascii='',
        export_stl_check_existing='',
        export_stl_global_scale='',
        export_stl_use_scene_unit='',
        slic3r_conf='',
        slic3r_post_script='',
        slic3r_extra_args='',
        slic3r_exec_dir='',
        slic3r_exec_name='',
        curaengine_conf='',
        curaengine_extra_args='',
        curaengine_exec_dir='',
        curaengine_exec_name='',
        octoprint_auto_upload_from_slicers='',
        octoprint_host='',
        octoprint_api_path='',
        octoprint_x_api_key='',
        octoprint_port='',
        octoprint_user='',
        octoprint_pass='',
        octoprint_save_gcode_dir='',
        repetier_auto_upload_from_slicers='',
        repetier_host='',
        repetier_api_path='',
        repetier_x_api_key='',
        repetier_port='',
        repetier_user='',
        repetier_pass='',
        repetier_save_gcode_dir='',
        open_browser_after_upload='',
        curl_exec_dir='',
        curl_exec_name='',
        log_level=''):

    stl_path_list = []
    for object in selected_objects:
        stl_path = os.path.join(stl_dir, object.name + '.stl')
        gcode_path = os.path.join(gcode_dir, object.name + '.gcode')

        bpy.ops.object.select_all(action='DESELECT')
        object.select = True

        blender_export_stl(stl_path=stl_path,
            axis_forward = export_stl_axis_forward,
            axis_up = export_stl_axis_up,
            export_stl_ascii = export_stl_ascii,
            export_stl_check_existing = export_stl_check_existing,
            export_stl_global_scale = export_stl_global_scale,
            export_stl_use_scene_unit = export_stl_use_scene_unit)

        # If merge append to stl_path_list, we will handle STL slicing &/or uploading after
        #  this for loop
        if 'Merge' in export_as_individual:
            stl_path_list.append(stl_path)
        else:
            slice_stl_to_gcode_locally(
                slicer = slicer,
                stl_path = stl_path,
                gcode_dir = gcode_dir,
                export_as_individual = export_as_individual,
                slic3r_exec_dir = slic3r_exec_dir,
                slic3r_exec_name = slic3r_exec_name,
                slic3r_conf = slic3r_conf,
                slic3r_post_script = slic3r_post_script,
                slic3r_extra_args = slic3r_extra_args,
                curaengine_exec_dir = curaengine_exec_dir,
                curaengine_exec_name = curaengine_exec_name,
                curaengine_conf = curaengine_conf,
                curaengine_extra_args = curaengine_conf)

            if octoprint_auto_upload_from_slicers is True:
                octoprint_upload_file(gcode_path = gcode_path,
                    host_url = octoprint_host,
                    api_path = octoprint_api_path,
                    xapi_key = octoprint_x_api_key,
                    host_port = octoprint_port,
                    user_name = octoprint_user,
                    passphrase = octoprint_pass,
                    gcode_dir = octoprint_save_gcode_dir,
                    curl_exec_dir = curl_exec_dir,
                    curl_exec_name = curl_exec_name,
                    log_level = log_level)

            if repetier_auto_upload_from_slicers is True:
                repetier_upload_gcode(gcode_path = gcode_path,
                    host_url = repetier_host,
                    api_path = repetier_api_path,
                    xapi_key = repetier_x_api_key,
                    host_port = repetier_port,
                    user_name = repetier_user,
                    passphrase = repetier_pass,
                    gcode_dir = repetier_save_gcode_dir,
                    curl_exec_dir = curl_exec_dir,
                    curl_exec_name = curl_exec_name,
                    log_level = log_level)

            if bpy.context.scene.preview_gcode:
                blender_import_gcode_text(filepath=gcode_path)

        object.hide = True

    # If list exsist we are importing individual STL files for a singular GCODE file, think of it
    #  like an *auto-arange* from the command line.
    if stl_path_list:
        if bpy.data.is_saved is True:
            gcode_path = os.path.join(gcode_dir, bpy.path.basename(bpy.context.blend_data.filepath) + '.gcode')
        else:
            gcode_path = os.path.join(gcode_dir, 'Untitled' + '.gcode')

        slice_stl_to_gcode_locally(
            slicer = slicer,
            stl_path = stl_path_list,
            gcode_dir = gcode_dir,
            export_as_individual = export_as_individual,
            slic3r_exec_dir = slic3r_exec_dir,
            slic3r_exec_name = slic3r_exec_name,
            slic3r_conf = slic3r_conf,
            slic3r_post_script = slic3r_post_script,
            slic3r_extra_args = slic3r_extra_args,
            curaengine_exec_dir = curaengine_exec_dir,
            curaengine_exec_name = curaengine_exec_name,
            curaengine_conf = curaengine_conf,
            curaengine_extra_args = curaengine_extra_args)

        if octoprint_auto_upload_from_slicers is True:
            octoprint_upload_file(gcode_path = gcode_path,
                host_url = octoprint_host,
                api_path = octoprint_api_path,
                xapi_key = octoprint_x_api_key,
                host_port = octoprint_port,
                user_name = octoprint_user,
                passphrase = octoprint_pass,
                gcode_dir = octoprint_save_gcode_dir,
                curl_exec_dir = curl_exec_dir,
                curl_exec_name = curl_exec_name,
                log_level = log_level)

        if repetier_auto_upload_from_slicers is True:
            repetier_upload_gcode(gcode_path = gcode_path,
                host_url = repetier_host,
                api_path = repetier_api_path,
                xapi_key = repetier_x_api_key,
                host_port = repetier_port,
                user_name = repetier_user,
                passphrase = repetier_pass,
                gcode_dir = repetier_save_gcode_dir,
                curl_exec_dir = curl_exec_dir,
                curl_exec_name = curl_exec_name,
                log_level = log_level)

        if bpy.context.scene.preview_gcode:
            blender_import_gcode_text(filepath = gcode_path)

    # Clean-up temp files
    for object in selected_objects:
        stl_path = os.path.join(stl_dir, object.name + '.stl')
        if bpy.context.scene.clean_temp_stl_files is True:
            rm(path = stl_path)

    if octoprint_auto_upload_from_slicers and open_browser_after_upload is True:
        host_url = octoprint_host
        host_port = octoprint_port
        if host_port:
            bpy.ops.wm.url_open(url='{0}:{1}'.format(host_url, host_port))
        else:
            bpy.ops.wm.url_open(url='{0}'.format(host_url))

    if repetier_auto_upload_from_slicers and open_browser_after_upload is True:
        host_url = repetier_host
        host_port = repetier_port
        if host_port:
            bpy.ops.wm.url_open(url='{0}:{1}'.format(host_url, host_port))
        else:
            bpy.ops.wm.url_open(url='{0}'.format(host_url))


#-------------------------------------------------------------------------
#   Similar to the looping function this operates on selected objects as a whole
#-------------------------------------------------------------------------
def slice_bulk_locally(
        slicer='',
        selected_objects=[],
        stl_dir='',
        gcode_dir='',
        export_as_individual='',
        export_stl_axis_forward='',
        export_stl_axis_up='',
        export_stl_ascii='',
        export_stl_check_existing='',
        export_stl_global_scale='',
        export_stl_use_scene_unit='',
        slic3r_conf='',
        slic3r_post_script='',
        slic3r_extra_args='',
        slic3r_exec_dir='',
        slic3r_exec_name='',
        curaengine_conf='',
        curaengine_extra_args='',
        curaengine_exec_dir='',
        curaengine_exec_name='',
        octoprint_auto_upload_from_slicers='',
        octoprint_host='',
        octoprint_api_path='',
        octoprint_x_api_key='',
        octoprint_port='',
        octoprint_user='',
        octoprint_pass='',
        octoprint_save_gcode_dir='',
        repetier_auto_upload_from_slicers='',
        repetier_host='',
        repetier_api_path='',
        repetier_x_api_key='',
        repetier_port='',
        repetier_user='',
        repetier_pass='',
        repetier_save_gcode_dir='',
        open_browser_after_upload='',
        curl_exec_dir='',
        curl_exec_name='',
        log_level=''):

    if bpy.data.is_saved is True:
        stl_path = os.path.join(stl_dir, bpy.path.basename(bpy.context.blend_data.filepath) + '.stl')
        gcode_path = os.path.join(gcode_dir, bpy.path.basename(bpy.context.blend_data.filepath) + '.gcode')
    else:
	    stl_path = os.path.join(stl_dir, 'Untitled' + '.stl')
	    gcode_path = os.path.join(gcode_dir, 'Untitled' + '.gcode')

    blender_export_stl(
        stl_path = stl_path,
        axis_forward = export_stl_axis_forward,
        axis_up = export_stl_axis_up,
        export_stl_ascii = export_stl_ascii,
        export_stl_check_existing = export_stl_check_existing,
        export_stl_global_scale = export_stl_global_scale,
        export_stl_use_scene_unit = export_stl_use_scene_unit)

    slice_stl_to_gcode_locally(
        slicer = slicer,
        stl_path = stl_path,
        gcode_dir = gcode_dir,
        export_as_individual = export_as_individual,
        slic3r_exec_dir = slic3r_exec_dir,
        slic3r_exec_name = slic3r_exec_name,
        slic3r_conf = slic3r_conf,
        slic3r_post_script = slic3r_post_script,
        slic3r_extra_args = slic3r_extra_args,
        curaengine_exec_dir = curaengine_exec_dir,
        curaengine_exec_name = curaengine_exec_name,
        curaengine_conf = curaengine_conf,
        curaengine_extra_args = curaengine_extra_args)

    for object in selected_objects:
        object.hide = True

    if bpy.context.scene.clean_temp_stl_files is True:
        rm(path=stl_path)

    if octoprint_auto_upload_from_slicers is True:
        octoprint_upload_file(
            gcode_path = gcode_path,
            host_url = octoprint_host,
            api_path = octoprint_api_path,
            xapi_key = octoprint_x_api_key,
            host_port = octoprint_port,
            user_name = octoprint_user,
            passphrase = octoprint_pass,
            gcode_dir = octoprint_save_gcode_dir,
            curl_exec_dir = curl_exec_dir,
            curl_exec_name = curl_exec_name,
            log_level=log_level)

        if open_browser_after_upload is True:
            if host_port:
                bpy.ops.wm.url_open(url='{0}:{1}'.format(octoprint_host, octoprint_port))
            else:
                bpy.ops.wm.url_open(url='{0}'.format(octoprint_host))

    if repetier_auto_upload_from_slicers is True:
        repetier_upload_gcode(
            gcode_path = gcode_path,
            host_url = repetier_host,
            api_path = repetier_api_path,
            xapi_key = repetier_x_api_key,
            host_port = repetier_port,
            user_name = repetier_user,
            passphrase = repetier_pass,
            gcode_dir = repetier_save_gcode_dir,
            curl_exec_dir = curl_exec_dir,
            curl_exec_name = curl_exec_name,
            log_level = log_level)

        if open_browser_after_upload is True:
            if host_port:
                bpy.ops.wm.url_open(url='{0}:{1}'.format(repetier_host, repetier_port))
            else:
                bpy.ops.wm.url_open(url='{0}'.format(repetier_host))

    if bpy.context.scene.preview_gcode:
        blender_import_gcode_text(filepath = gcode_path)


#-------------------------------------------------------------------------
#   Main logic for running Slic3r repair operations when button is pressed
#-------------------------------------------------------------------------
def slic3r_repair_operations(
        selected_objects=[],
        temp_stl_directory='',
        temp_obj_directory='',
        repaired_parent_name='',
        export_as_individual='',
        slic3r_exec_dir='',
        slic3r_exec_name='',
        export_stl_axis_forward='',
        export_stl_axis_up='',
        export_stl_ascii='',
        export_stl_check_existing='',
        export_stl_global_scale='',
        export_stl_use_scene_unit='',
        import_obj_axis_forward='',
        import_obj_axis_up='',
        import_obj_use_edges='',
        import_obj_use_smooth_groups='',
        import_obj_use_split_objects='',
        import_obj_use_split_groups='',
        import_obj_use_groups_as_vgroups='',
        import_obj_use_image_search='',
        import_obj_split_mode='',
        import_obj_global_clamp_size=''):

    if not selected_objects:
        raise Exception('Please select some objects first.')

    if not os.path.exists(temp_stl_directory):
        mkdir(dir_path = temp_stl_directory)

    if not os.path.exists(temp_obj_directory):
        mkdir(dir_path = temp_obj_directory)

    if 'Individual' in export_as_individual or 'Merge' in export_as_individual:
        slic3r_repair_loop(
            selected_objects = selected_objects,
            temp_stl_directory = temp_stl_directory,
            temp_obj_directory = temp_obj_directory,
            repaired_parent_name = repaired_parent_name,
            slic3r_exec_dir = slic3r_exec_dir,
            slic3r_exec_name = slic3r_exec_name,
            export_stl_axis_forward = export_stl_axis_forward,
            export_stl_axis_up = export_stl_axis_up,
            export_stl_ascii = export_stl_ascii,
            export_stl_check_existing = export_stl_check_existing,
            export_stl_global_scale = export_stl_global_scale,
            export_stl_use_scene_unit = export_stl_use_scene_unit,
            import_obj_axis_forward = import_obj_axis_forward,
            import_obj_axis_up = import_obj_axis_up,
            import_obj_use_edges = import_obj_use_edges,
            import_obj_use_smooth_groups = import_obj_use_smooth_groups,
            import_obj_use_split_objects = import_obj_use_split_objects,
            import_obj_use_split_groups = import_obj_use_split_groups,
            import_obj_use_groups_as_vgroups = import_obj_use_groups_as_vgroups,
            import_obj_use_image_search = import_obj_use_image_search,
            import_obj_split_mode = import_obj_split_mode,
            import_obj_global_clamp_size = import_obj_global_clamp_size)

    elif 'Batch' in export_as_individual:
        slic3r_repair_bulk(
            selected_objects = selected_objects,
            temp_stl_directory = temp_stl_directory,
            temp_obj_directory = temp_obj_directory,
            repaired_parent_name = repaired_parent_name,
            slic3r_exec_dir = slic3r_exec_dir,
            slic3r_exec_name = slic3r_exec_name,
            export_stl_axis_forward = export_stl_axis_forward,
            export_stl_axis_up = export_stl_axis_up,
            export_stl_ascii = export_stl_ascii,
            export_stl_check_existing = export_stl_check_existing,
            export_stl_global_scale = export_stl_global_scale,
            export_stl_use_scene_unit = export_stl_use_scene_unit,
            import_obj_axis_forward = import_obj_axis_forward,
            import_obj_axis_up = import_obj_axis_up,
            import_obj_use_edges = import_obj_use_edges,
            import_obj_use_smooth_groups = import_obj_use_smooth_groups,
            import_obj_use_split_objects = import_obj_use_split_objects,
            import_obj_use_split_groups = import_obj_use_split_groups,
            import_obj_use_groups_as_vgroups = import_obj_use_groups_as_vgroups,
            import_obj_use_image_search = import_obj_use_image_search,
            import_obj_split_mode = import_obj_split_mode,
            import_obj_global_clamp_size = import_obj_global_clamp_size)


#-------------------------------------------------------------------------
#   Loads user customization and calls functions required for slicing via Slic3r
#-------------------------------------------------------------------------
def slic3r_slice_operations(
        selected_objects=[],
        stl_dir='',
        gcode_dir='',
        export_as_individual='',
        export_stl_axis_forward='',
        export_stl_axis_up='',
        export_stl_ascii='',
        export_stl_check_existing='',
        export_stl_global_scale='',
        export_stl_use_scene_unit='',
        slic3r_conf='',
        slic3r_post_script='',
        slic3r_extra_args='',
        slic3r_exec_dir='',
        slic3r_exec_name='',
        octoprint_auto_upload_from_slicers='',
        octoprint_host='',
        octoprint_api_path='',
        octoprint_x_api_key='',
        octoprint_port='',
        octoprint_user='',
        octoprint_pass='',
        octoprint_save_gcode_dir='',
        repetier_auto_upload_from_slicers='',
        repetier_host='',
        repetier_api_path='',
        repetier_x_api_key='',
        repetier_port='',
        repetier_user='',
        repetier_pass='',
        repetier_save_gcode_dir='',
        open_browser_after_upload='',
        curl_exec_dir='',
        curl_exec_name='',
        log_level=''):

    if not selected_objects:
        raise Exception('Please select some objects first.')

    if not os.path.exists(stl_dir):
        mkdir(dir_path = stl_dir)
    if not os.path.exists(gcode_dir):
        mkdir(dir_path = gcode_dir)

    if 'Individual' in export_as_individual or 'Merge' in export_as_individual:
        slice_loop_locally(
            slicer = 'Slic3r',
            selected_objects = selected_objects,
            stl_dir = stl_dir,
            gcode_dir = gcode_dir,
            export_as_individual = export_as_individual,
            export_stl_axis_forward = export_stl_axis_forward,
            export_stl_axis_up = export_stl_axis_up,
            export_stl_ascii = export_stl_ascii,
            export_stl_check_existing = export_stl_check_existing,
            export_stl_global_scale = export_stl_global_scale,
            export_stl_use_scene_unit = export_stl_use_scene_unit,
            slic3r_conf = slic3r_conf,
            slic3r_post_script = slic3r_post_script,
            slic3r_extra_args = slic3r_extra_args,
            slic3r_exec_dir = slic3r_exec_dir,
            slic3r_exec_name = slic3r_exec_name,
            octoprint_auto_upload_from_slicers = octoprint_auto_upload_from_slicers,
            octoprint_host = octoprint_host,
            octoprint_api_path = octoprint_api_path,
            octoprint_x_api_key = octoprint_x_api_key,
            octoprint_port = octoprint_port,
            octoprint_user = octoprint_user,
            octoprint_pass = octoprint_pass,
            octoprint_save_gcode_dir = octoprint_save_gcode_dir,
            repetier_auto_upload_from_slicers = repetier_auto_upload_from_slicers,
            repetier_host = repetier_host,
            repetier_api_path = repetier_api_path,
            repetier_x_api_key = repetier_x_api_key,
            repetier_port = repetier_port,
            repetier_user = repetier_user,
            repetier_pass = repetier_pass,
            repetier_save_gcode_dir = repetier_save_gcode_dir,
            open_browser_after_upload = open_browser_after_upload,
            curl_exec_dir = curl_exec_dir,
            curl_exec_name = curl_exec_name,
            log_level = log_level)

    elif 'Batch' in export_as_individual:
        slice_bulk_locally(
            slicer = 'Slic3r',
            selected_objects = selected_objects,
            stl_dir = stl_dir,
            gcode_dir=gcode_dir,
            export_as_individual = export_as_individual,
            export_stl_axis_forward = export_stl_axis_forward,
            export_stl_axis_up = export_stl_axis_up,
            export_stl_ascii = export_stl_ascii,
            export_stl_check_existing = export_stl_check_existing,
            export_stl_global_scale = export_stl_global_scale,
            export_stl_use_scene_unit = export_stl_use_scene_unit,
            slic3r_conf = slic3r_conf,
            slic3r_post_script = slic3r_post_script,
            slic3r_extra_args = slic3r_extra_args,
            slic3r_exec_dir = slic3r_exec_dir,
            slic3r_exec_name = slic3r_exec_name,
            octoprint_auto_upload_from_slicers = octoprint_auto_upload_from_slicers,
            octoprint_host = octoprint_host,
            octoprint_api_path = octoprint_api_path,
            octoprint_x_api_key = octoprint_x_api_key,
            octoprint_port = octoprint_port,
            octoprint_user = octoprint_user,
            octoprint_pass = octoprint_pass,
            octoprint_save_gcode_dir = octoprint_save_gcode_dir,
            repetier_auto_upload_from_slicers = repetier_auto_upload_from_slicers,
            repetier_host = repetier_host,
            repetier_api_path = repetier_api_path,
            repetier_x_api_key = repetier_x_api_key,
            repetier_port = repetier_port,
            repetier_user = repetier_user,
            repetier_pass = repetier_pass,
            repetier_save_gcode_dir = repetier_save_gcode_dir,
            open_browser_after_upload = open_browser_after_upload,
            curl_exec_dir = curl_exec_dir,
            curl_exec_name = curl_exec_name,
            log_level = log_level)


#-------------------------------------------------------------------------
#   Loads user customization and calls functions required for slicing via Slic3r
#-------------------------------------------------------------------------
def curaengine_slice_operations(
        selected_objects=[],
        stl_dir='',
        gcode_dir='',
        export_as_individual='',
        export_stl_axis_forward='',
        export_stl_axis_up='',
        export_stl_ascii='',
        export_stl_check_existing='',
        export_stl_global_scale='',
        export_stl_use_scene_unit='',
        curaengine_conf='',
        curaengine_extra_args='',
        curaengine_exec_dir='',
        curaengine_exec_name='',
        octoprint_auto_upload_from_slicers='',
        octoprint_host='',
        octoprint_api_path='',
        octoprint_x_api_key='',
        octoprint_port='',
        octoprint_user='',
        octoprint_pass='',
        octoprint_save_gcode_dir='',
        repetier_auto_upload_from_slicers='',
        repetier_host='',
        repetier_api_path='',
        repetier_x_api_key='',
        repetier_port='',
        repetier_user='',
        repetier_pass='',
        repetier_save_gcode_dir='',
        open_browser_after_upload='',
        curl_exec_dir='',
        curl_exec_name='',
        log_level=''):

    if not selected_objects:
        raise Exception('Please select some objects first.')

    if not os.path.exists(stl_dir):
        mkdir(dir_path = stl_dir)
    if not os.path.exists(gcode_dir):
        mkdir(dir_path = gcode_dir)

    if 'Individual' in export_as_individual or 'Merge' in export_as_individual:
        slice_loop_locally(
            slicer = 'CuraEngine',
            selected_objects = selected_objects,
            stl_dir = stl_dir,
            gcode_dir=gcode_dir,
            export_as_individual = export_as_individual,
            export_stl_axis_forward = export_stl_axis_forward,
            export_stl_axis_up = export_stl_axis_up,
            export_stl_ascii = export_stl_ascii,
            export_stl_check_existing = export_stl_check_existing,
            export_stl_global_scale = export_stl_global_scale,
            export_stl_use_scene_unit = export_stl_use_scene_unit,
            curaengine_conf = curaengine_conf,
            curaengine_extra_args = curaengine_extra_args,
            curaengine_exec_dir = curaengine_exec_dir,
            curaengine_exec_name = curaengine_exec_name,
            octoprint_auto_upload_from_slicers = octoprint_auto_upload_from_slicers,
            octoprint_host = octoprint_host,
            octoprint_api_path = octoprint_api_path,
            octoprint_x_api_key = octoprint_x_api_key,
            octoprint_port = octoprint_port,
            octoprint_user = octoprint_user,
            octoprint_pass = octoprint_pass,
            octoprint_save_gcode_dir = octoprint_save_gcode_dir,
            repetier_auto_upload_from_slicers = repetier_auto_upload_from_slicers,
            repetier_host = repetier_host,
            repetier_api_path = repetier_api_path,
            repetier_x_api_key = repetier_x_api_key,
            repetier_port = repetier_port,
            repetier_user = repetier_user,
            repetier_pass = repetier_pass,
            repetier_save_gcode_dir = repetier_save_gcode_dir,
            open_browser_after_upload = open_browser_after_upload,
            curl_exec_dir = curl_exec_dir,
            curl_exec_name = curl_exec_name,
            log_level = log_level)

    elif 'Batch' in export_as_individual:
        slice_bulk_locally(
            slicer = 'CuraEngine',
            selected_objects = selected_objects,
            stl_dir = stl_dir,
            gcode_dir=gcode_dir,
            export_as_individual = export_as_individual,
            export_stl_axis_forward = export_stl_axis_forward,
            export_stl_axis_up = export_stl_axis_up,
            export_stl_ascii = export_stl_ascii,
            export_stl_check_existing = export_stl_check_existing,
            export_stl_global_scale = export_stl_global_scale,
            export_stl_use_scene_unit = export_stl_use_scene_unit,
            curaengine_conf = curaengine_conf,
            curaengine_extra_args = curaengine_extra_args,
            curaengine_exec_dir = curaengine_exec_dir,
            octoprint_auto_upload_from_slicers = octoprint_auto_upload_from_slicers,
            octoprint_host = octoprint_host,
            octoprint_api_path = octoprint_api_path,
            octoprint_x_api_key = octoprint_x_api_key,
            octoprint_port = octoprint_port,
            octoprint_user = octoprint_user,
            octoprint_pass = octoprint_pass,
            octoprint_save_gcode_dir = octoprint_save_gcode_dir,
            repetier_auto_upload_from_slicers = repetier_auto_upload_from_slicers,
            repetier_host = repetier_host,
            repetier_api_path = repetier_api_path,
            repetier_x_api_key = repetier_x_api_key,
            repetier_port = repetier_port,
            repetier_user = repetier_user,
            repetier_pass = repetier_pass,
            repetier_save_gcode_dir = repetier_save_gcode_dir,
            open_browser_after_upload = open_browser_after_upload,
            curl_exec_dir = curl_exec_dir,
            curl_exec_name = curl_exec_name,
            log_level = log_level)


#-------------------------------------------------------------------------
#   Loads user customizations and calls functions required to upload STL files to OctoPrint server
#-------------------------------------------------------------------------
def octoprint_upload_stl_operations(
        selected_objects=[],
        temp_stl_directory='',
        export_as_individual='',
        export_stl_axis_forward='',
        export_stl_axis_up='',
        export_stl_ascii='',
        export_stl_check_existing='',
        export_stl_global_scale='',
        export_stl_use_scene_unit='',
        clean_temp_stl_files='',
        sliceOnServer='',
        octoprint_host='',
        octoprint_api_path='',
        octoprint_x_api_key='',
        octoprint_port='',
        octoprint_user='',
        octoprint_pass='',
        octoprint_save_stl_dir='',
        octoprint_slice_slicer='',
        octoprint_slice_printerProfile='',
        octoprint_slice_Profile='',
        octoprint_slice_Profile_ops='',
        octoprint_slice_position_x='',
        octoprint_slice_position_y='',
        curl_exec_dir='',
        curl_exec_name='',
        log_level=''):

    if not selected_objects:
        raise Exception('Please select some objects first.')

    if 'Individual' in export_as_individual or 'Merge' in export_as_individual:
        for object in selected_objects:
            stl_path = os.path.join(temp_stl_directory, object.name + '.stl')
            bpy.ops.object.select_all(action='DESELECT')
            object.select = True

            blender_export_stl(
                stl_path = stl_path,
                axis_forward = export_stl_axis_forward,
                axis_up = export_stl_axis_up,
                export_stl_ascii = export_stl_ascii,
                export_stl_check_existing = export_stl_check_existing,
                export_stl_global_scale = export_stl_global_scale,
                export_stl_use_scene_unit = export_stl_use_scene_unit)

            octoprint_upload_file(
                stl_path = stl_path,
                host_url = octoprint_host,
                api_path = octoprint_api_path,
                xapi_key = octoprint_x_api_key,
                host_port = octoprint_port,
                user_name = octoprint_user,
                passphrase = octoprint_pass,
                stl_dir = octoprint_save_stl_dir,
                curl_exec_dir = curl_exec_dir,
                curl_exec_name = curl_exec_name,
                log_level = log_level)

            if sliceOnServer:
                octoprint_slice_stl(
                    stl_path = stl_path,
                    host_url = octoprint_host,
                    api_path = octoprint_api_path,
                    xapi_key = octoprint_x_api_key,
                    host_port = octoprint_port,
                    user_name = octoprint_user,
                    passphrase = octoprint_pass,
                    stl_dir = octoprint_save_stl_dir,
                    slice_slicer = octoprint_slice_slicer,
                    slice_printerProfile = octoprint_slice_printerProfile,
                    slice_Profile = octoprint_slice_Profile,
                    slice_Profile_ops = octoprint_slice_Profile_ops,
                    slice_position_x = octoprint_slice_position_x,
                    slice_position_y = octoprint_slice_position_y,
                    curl_exec_dir = curl_exec_dir,
                    curl_exec_name = curl_exec_name,
                    log_level = log_level)

            object.hide = True
            if clean_temp_stl_files is True:
                for object in selected_objects:
                    stl_path = os.path.join(temp_stl_directory, object.name + '.stl')
                    rm(path = stl_path)
    elif 'Batch' in export_as_individual:
        if bpy.data.is_saved is True:
            stl_path = os.path.join(temp_stl_directory, bpy.path.basename(bpy.context.blend_data.filepath) + '.stl')
        else:
	        stl_path = os.path.join(temp_stl_directory, 'Untitled' + '.stl')

        blender_export_stl(
            stl_path = stl_path,
            axis_forward = export_stl_axis_forward,
            axis_up = export_stl_axis_up,
            export_stl_ascii = export_stl_ascii,
            export_stl_check_existing = export_stl_check_existing,
            export_stl_global_scale = export_stl_global_scale,
            export_stl_use_scene_unit = export_stl_use_scene_unit)

        octoprint_upload_file(
            stl_path=stl_path,
            host_url = octoprint_host,
            api_path = octoprint_api_path,
            xapi_key = octoprint_x_api_key,
            host_port = octoprint_port,
            user_name = octoprint_user,
            passphrase = scene.octoprint_pass,
            stl_dir = octoprint_save_stl_dir,
            curl_exec_dir = curl_exec_dir,
            curl_exec_name = curl_exec_name,
            log_level = log_level)

        if sliceOnServer:
            octoprint_slice_stl(
                stl_path = stl_path,
                host_url = octoprint_host,
                api_path = octoprint_api_path,
                xapi_key = octoprint_x_api_key,
                host_port = octoprint_port,
                user_name = octoprint_user,
                passphrase = octoprint_pass,
                stl_dir = octoprint_save_stl_dir,
                slice_slicer = octoprint_slice_slicer,
                slice_printerProfile = octoprint_slice_printerProfile,
                slice_Profile = octoprint_slice_Profile,
                slice_Profile_ops = octoprint_slice_Profile_ops,
                slice_position_x = octoprint_slice_position_x,
                slice_position_y = octoprint_slice_position_y,
                curl_exec_dir = curl_exec_dir,
                curl_exec_name = curl_exec_name,
                log_level = log_level)

        for object in selected_objects:
            object.hide = True

        if bpy.context.scene.clean_temp_stl_files is True:
            rm(stl_path)

#-------------------------------------------------------------------------
#   Setup snapshot or streaming view of print server webcam
#-------------------------------------------------------------------------
def preview_webcam_operations(
        action='',
        host='',
        port='',
        user='',
        passphrase='',
        snapshot_dir='',
        snapshot_name='',
        preview_xy_scale='',
        snapshot_action='',
        stream_action='',
        preview_placement='',
        preview_layer='',
        target_screen='',
        target_3dview='',
        curl_exec_dir='',
        curl_exec_name='',
        log_level='',
        button_background_color='',
        button_text_color=''):

    # Deselect all meshes, perhaps that will keep new textures off pre-exsisting meshes
    bpy.ops.object.select_all(action='DESELECT')

    image_file_name = snapshot_name + '.jpg'
    image_plane_name = snapshot_name + '_Plane'
    bge_sensor_name = snapshot_name + '_Sensor'
    bge_controller_name = snapshot_name + '_Controller'
    bge_material_name = snapshot_name + '_Material'
    bge_texture_name = snapshot_name + '_Texture'
    bge_controller_script_name = snapshot_name + '_Script.py'

    if port:
        snapshot_url = host + ':' + port + '/' + snapshot_action
        stream_url = host + ':' + port + '/' + stream_action
    else:
        snapshot_url = host + '/' + snapshot_action
        stream_url = host + '/' + stream_action

    # Take a picture of 3D Printer to use as a static texture,
    #  this will allow users to see their print bed without playing
    #  the Blender Game Renderer
    curl_download_snapshot(
        url = snapshot_url,
        download_path = os.path.join(snapshot_dir,image_file_name),
        auth_user = user,
        auth_pass = passphrase,
        curl_exec_dir = curl_exec_dir,
        curl_exec_name = curl_exec_name,
        log_level = log_level)

    # Pull in the downloaded picture into current Blender file/scene
    blender_webcam_import_local_image(filename = image_file_name, directory = snapshot_dir)

    image_X_size = bpy.data.images[image_file_name].size[0]
    image_Y_size = bpy.data.images[image_file_name].size[1]

    if image_X_size is None:
        raise Exception('Could not read image X size')
    if image_Y_size is None:
        raise Exception('Could not read image Y size')

    # Add & scale a Plane object, then add the picture from OctoPrint
    #  server as a texture
    blender_webcam_add_view_plane(
        image_name = image_file_name,
        video_object_name = image_plane_name,
        video_material_name = bge_material_name,
        video_texture_name = bge_texture_name,
        x_dimension = image_X_size,
        y_dimension = image_Y_size,
        xy_scale = preview_xy_scale,
        preview_placement = preview_placement,
        preview_layer = preview_layer)
    webcam_obj = bpy.data.objects.get(image_plane_name)

    # Write a customized Blender Game Engine script for updating the
    #  texture of the Plane with a video source, in this case the
    #  address of the OctoPrint server.
    blender_webcam_setup_script_text_block(
        controller_script_name = bge_controller_script_name,
        default_image = image_file_name,
        video_path = stream_url)

    # Link together objects, scripts, and Blender Game Engine blocks
    #  such that the user need only use the default keyboard short-cut
    #  'P' within a 3D window to play a live stream from the server.
    blender_webcam_setup_game_logic(
        video_object_name = image_plane_name,
        sensor_name = bge_sensor_name,
        controller_name = bge_controller_name,
        controller_script_name = bge_controller_script_name)

    if action == 'snapshot':
        blender_3dview_modify_viewport(
            animate = False,
            preview_layer = preview_layer,
            target_screen = target_screen,
            target_3dview = target_3dview)
    elif action == 'stream':
        # Add exit button in upper left corner of preview plane
        text_location = (-webcam_obj.dimensions[0]/2, webcam_obj.dimensions[1]/2, webcam_obj.dimensions[2]+1)
        blender_webcam_add_button_text(
            text_name='Exit_Button',
            text_body='[ESC]',
            button_background_color = button_background_color,
            button_text_color = button_text_color,
            preview_layer = preview_layer,
            location = text_location)
        # Note we are assuming that naming of background plane will not change from previous function call
        blender_button_setup_game_logic(
            object_name='Exit_Button_Plane',
            actuator_type='GAME',
            actuator_mode='QUIT')

        blender_3dview_modify_viewport(
            animate = True,
            preview_layer = preview_layer,
            target_screen = target_screen,
            target_3dview = target_3dview)


def curl_test_operations(
        curl_ops='',
        curl_exec_dir='',
        curl_exec_name='',
        log_level=''):

    if curl_ops:
        args = []
        extra_args = []
        for arg in enumerate(curl_ops.split(', ')):
            extra_args += [arg[1]]
        args.extend(extra_args)

        curl(exec_dir=curl_exec_dir, exec_name=curl_exec_name, ops=args, log_ops=args)


#-------------------------------------------------------------------------
#    This allows you to right click on a button and link to the manual
#-------------------------------------------------------------------------
def swiftTo3Dprint_manual_map():
    url_manual_prefix = 'https://docs.blender.org/manual/en/dev/'
    url_manual_mapping = (
        ('bpy.object.3DPrint_Short_Cuts', 'to-be-decided'),
    )
    return url_manual_prefix, url_manual_mapping


# Uncomment the following two lines to allow add-on to run from text editor
#  without having to install via user preferences
if __name__ == '__main__':
    __name__ = this_addons_name
    register()


# Credits
# Author: S0AndS0
# URL: https://github.com/S0AndS0
# Resources used:--
# https://blender.stackexchange.com/questions/33755/batch-exporting-of-multiple-objects-into-separate-stl-files
# http://manual.slic3r.org/getting-slic3r/getting-slic3r
# https://docs.blender.org/api/blender_python_api_2_65_5/info_tutorial_addon.html
# https://stackoverflow.com/questions/6190776/what-is-the-best-way-to-exit-a-function-which-has-no-return-value-in-python-be
# https://en.wikibooks.org/w/index.php?title=Blender_3D:_Noob_to_Pro/Advanced_Tutorials/Python_Scripting/Addon_User_Interface&stable=0#Put_It_All_Together
# https://michelanders.blogspot.com/p/creating-blender-26-python-add-on.html
# https://blenderartists.org/forum/showthread.php?283468-How-to-test-if-an-object-exists
# https://blender.stackexchange.com/questions/2382/how-to-add-a-select-path-input-in-a-ui-addon-script
# https://blender.stackexchange.com/questions/3219/how-to-show-to-the-user-a-progression-in-a-script
# https://docs.blender.org/api/blender_python_api_current/bpy.types.PropertyGroup.html
# https://blender.stackexchange.com/questions/35007/how-can-i-add-a-checkbox-in-the-tools-ui
# https://donjajo.com/how-to-send-post-request-using-urllib-only-in-python3/
# https://pythonprogramming.net/urllib-tutorial-python-3/
# https://www.pythoncentral.io/reading-and-writing-to-files-in-python/
# http://docs.octoprint.org/en/master/api/files.html#upload-file-or-create-folder
# https://stackoverflow.com/questions/15767785/python-http-multipart-form-data-post-request
# https://github.com/MoonshineSG/Simplify3D-to-OctoPrint/blob/master/toctoprint.py
# https://stackoverflow.com/questions/3751900/create-file-path-from-variables
# https://blender.stackexchange.com/questions/6842/how-to-get-the-directory-of-open-blend-file-from-python
# https://stackoverflow.com/questions/8214519/appending-two-arrays-together-in-python
# https://blenderartists.org/forum/archive/index.php/t-224328.html
# https://www.repetier-server.com/using-simplify-3d-repetier-server/
# https://blender.stackexchange.com/questions/8702/attributeerror-restrictdata-object-has-no-attribute-filepath
# https://stackoverflow.com/questions/7172784/how-to-post-json-data-with-curl-from-terminal-commandline-to-test-spring-rest
# https://stackoverflow.com/questions/5618878/how-to-convert-list-to-string
# https://blender.stackexchange.com/questions/45528/how-to-get-blenders-version-number-from-python
# https://docs.blender.org/api/blender_python_api_2_61_0/info_tips_and_tricks.html
# https://blenderartists.org/forum/showthread.php?254880-Show-mouse-script
# https://stackoverflow.com/questions/17388912/blender-script-how-to-write-to-text-object
# https://blender.stackexchange.com/questions/9200/make-object-a-a-parent-of-object-b-via-python
# https://blender.stackexchange.com/questions/94998/start-and-exit-buttons-are-not-working-properly-in-blender-game

# TO-DO - Add progress bar support?
#https://github.com/meta-androcto/blenderpython/blob/master/scripts/addons_extern/io_scene_obj1/export_obj.py
#...
#from progress_report import ProgressReport, ProgressReportSubstep
#...
#with ProgressReportSubstep(progress, 2, "OBJ Export path: %r" % filepath, "OBJ Export Finished") as subprogress1
#   #do stuff

# TO-DO - Add GUI user output of progress other than just hiding objects
