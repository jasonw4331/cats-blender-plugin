# GPL License

import os
import bpy
import json
import copy
import time
import pathlib
import collections
from threading import Thread
from datetime import datetime, timezone
from collections import OrderedDict

from .. import globs
from ..tools.register import register_wrap
# from ..googletrans import Translator  # Todo Remove this
from ..extern_tools.google_trans_new.google_trans_new import google_translator
from . import translate as Translate
from .translations import t

main_dir = pathlib.Path(os.path.dirname(__file__)).parent.resolve()
resources_dir = os.path.join(str(main_dir), "resources")
settings_file = os.path.join(resources_dir, "settings.json")

settings_data = None
settings_data_unchanged = None
settings_threads = []

# Settings name = [Default Value, Require Blender Restart]
settings_default = OrderedDict()
settings_default['show_mmd_tabs'] = [True, False]
settings_default['embed_textures'] = [False, False]
settings_default['ui_lang'] = ["auto", False]
# settings_default['use_custom_mmd_tools'] = [False, True]

lock_settings = False


@register_wrap
class RevertChangesButton(bpy.types.Operator):
    bl_idname = 'cats_settings.revert'
    bl_label = t('RevertChangesButton.label')
    bl_description = t('RevertChangesButton.desc')
    bl_options = {'INTERNAL'}

    def execute(self, context):
        for setting in settings_default.keys():
            setattr(bpy.context.scene, setting, settings_data_unchanged.get(setting))
        save_settings()
        self.report({'INFO'}, t('RevertChangesButton.success'))
        return {'FINISHED'}


@register_wrap
class ResetGoogleDictButton(bpy.types.Operator):
    bl_idname = 'cats_settings.reset_google_dict'
    bl_label = t('ResetGoogleDictButton.label')
    bl_description = t('ResetGoogleDictButton.desc')
    bl_options = {'INTERNAL'}

    def execute(self, context):
        Translate.reset_google_dict()
        Translate.load_translations()
        self.report({'INFO'}, t('ResetGoogleDictButton.resetInfo'))
        return {'FINISHED'}


@register_wrap
class DebugTranslations(bpy.types.Operator):
    bl_idname = 'cats_settings.debug_translations'
    bl_label = t('DebugTranslations.label')
    bl_description = t('DebugTranslations.desc')
    bl_options = {'INTERNAL'}

    def execute(self, context):
        bpy.context.scene.debug_translations = True
        translator = google_translator()
        try:
            translator.translate('猫')
        except:
            self.report({'INFO'}, t('DebugTranslations.error'))

        bpy.context.scene.debug_translations = False
        self.report({'INFO'}, t('DebugTranslations.success'))
        return {'FINISHED'}


def load_settings():
    # print('READING SETTINGS FILE')
    global settings_data, settings_data_unchanged

    # Load settings file and reset it if errors are found
    try:
        with open(settings_file, encoding="utf8") as file:
            settings_data = json.load(file, object_pairs_hook=collections.OrderedDict)
            # print('SETTINGS LOADED!')
    except FileNotFoundError:
        print("SETTINGS FILE NOT FOUND!")
        reset_settings(full_reset=True)
        return
    except json.decoder.JSONDecodeError:
        print("ERROR FOUND IN SETTINGS FILE")
        reset_settings(full_reset=True)
        return

    if not settings_data:
        print("NO DATA IN SETTINGS FILE")
        reset_settings(full_reset=True)
        return

    to_reset_settings = []

    # Check for missing entries, reset if necessary
    for setting in ['last_supporter_update']:
        if setting not in settings_data and setting not in to_reset_settings:
            to_reset_settings.append(setting)
            print('RESET SETTING', setting)

    # Check for other missing entries, reset if necessary
    for setting in settings_default.keys():
        if setting not in settings_data and setting not in to_reset_settings:
            to_reset_settings.append(setting)
            print('RESET SETTING', setting)

    # Check if timestamps are correct
    utc_now = datetime.strptime(datetime.now(timezone.utc).strftime(globs.time_format), globs.time_format)
    for setting in ['last_supporter_update']:
        if setting not in to_reset_settings and settings_data.get(setting):
            try:
                timestamp = datetime.strptime(settings_data.get(setting), globs.time_format)
            except ValueError:
                to_reset_settings.append(setting)
                print('RESET TIME', setting)
                continue

            # If timestamp is in future
            time_delta = (utc_now - timestamp).total_seconds()
            if time_delta < 0:
                to_reset_settings.append(setting)
                print('TIME', setting, 'IN FUTURE!', time_delta)
            else:
                pass
                # print('TIME', setting, 'IN PAST!', time_delta)

    # If there are settings to reset, reset them
    if to_reset_settings:
        reset_settings(to_reset_settings=to_reset_settings)
        return

    # Save the settings into the unchanged settings in order to know if the settings changed later
    settings_data_unchanged = copy.deepcopy(settings_data)


def save_settings():
    with open(settings_file, 'w', encoding="utf8") as outfile:
        json.dump(settings_data, outfile, ensure_ascii=False, indent=4)


def reset_settings(full_reset=False, to_reset_settings=None):
    if not to_reset_settings:
        full_reset = True

    global settings_data, settings_data_unchanged

    if full_reset:
        settings_data = OrderedDict()
        settings_data['last_supporter_update'] = None

        for setting, value in settings_default.items():
            settings_data[setting] = value[0]

    else:
        for setting in to_reset_settings:
            if setting in settings_default.keys():
                settings_data[setting] = settings_default[setting][0]
            else:
                settings_data[setting] = None

    save_settings()

    settings_data_unchanged = copy.deepcopy(settings_data)
    print('SETTINGS RESET')


def start_apply_settings_timer():
    global lock_settings, settings_threads
    lock_settings = True
    thread = Thread(target=apply_settings, args=[])
    settings_threads.append(thread)
    thread.start()


def stop_apply_settings_threads():
    global settings_threads

    print("Stopping settings threads...")
    for t in settings_threads:
        t.join()
    print("Settings threads stopped.")


def apply_settings():
    applied = False
    while not applied:
        if hasattr(bpy.context, 'scene'):
            try:
                settings_to_reset = []
                for setting in settings_default.keys():
                    try:
                        setattr(bpy.context.scene, setting, settings_data.get(setting))
                    except TypeError:
                        settings_to_reset.append(setting)
                if settings_to_reset:
                    reset_settings(to_reset_settings=settings_to_reset)
                    print("RESET SETTING ON TIMER:", setting)
            except AttributeError:
                time.sleep(0.3)
                continue

            applied = True
            # print('Refreshed Settings!')
        else:
            time.sleep(0.3)

    # Unlock settings
    global lock_settings
    lock_settings = False


def settings_changed():
    for setting, value in settings_default.items():
        if value[1] and settings_data.get(setting) != settings_data_unchanged.get(setting):
            return True
    return False


def update_settings(self, context):
    update_settings_core(self, context)


def update_settings_core(self, context):
    # Use False and None for this variable, because Blender would complain otherwise
    # None means that the settings did change
    settings_changed_tmp = False
    if lock_settings:
        return settings_changed_tmp

    for setting in settings_default.keys():
        old = settings_data[setting]
        new = getattr(bpy.context.scene, setting)
        if old != new:
            settings_data[setting] = getattr(bpy.context.scene, setting)
            settings_changed_tmp = True

    if settings_changed_tmp:
        save_settings()

    return settings_changed_tmp


def set_last_supporter_update(last_supporter_update):
    settings_data['last_supporter_update'] = last_supporter_update
    save_settings()


def get_last_supporter_update():
    return settings_data.get('last_supporter_update')


def get_use_custom_mmd_tools():
    return settings_data.get('use_custom_mmd_tools')


def get_embed_textures():
    return settings_data.get('embed_textures')


def get_ui_lang():
    return settings_data.get('ui_lang')
