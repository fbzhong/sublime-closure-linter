import os
import re
import shutil
import tempfile
import sublime
import sublime_plugin
from const import *
from listener import *
from statusprocess import *
from asyncprocess import *

class FixJsStyleCommand(sublime_plugin.WindowCommand):
  def run(self):
    file_path = self.window.active_view().file_name()
    file_name = os.path.basename(file_path)

    self.buffered_data = ''
    self.file_path = file_path
    self.file_name = file_name
    self.is_running = True
    self.tests_panel_showed = False
    self.file_view = self.window.active_view()

    self.init_tests_panel()

    if file_name.endswith('.js') == False:
      self.append_data(None, "fixjslint can only be used for JavaScript file.", True)
      return

    # save file.
    self.file_view.run_command('save')

    # make a copy.
    self.target_file_path = os.path.join(tempfile.gettempdir(), self.file_name)
    shutil.copyfile(self.file_path, self.target_file_path)

    s = sublime.load_settings(SETTINGS_FILE)
    cmd = s.get('fixjsstyle_path', 'fixjsstyle') + ' ' + s.get('fixjsstyle_flags', '') + ' "' + self.target_file_path + '"'

    if s.get('debug', False) == True:
      print "DEBUG: " + str(cmd)

    AsyncProcess(cmd, self)
    StatusProcess('Starting Fix Javascript Style for file ' + file_name, self)

    ClosureLinterEventListener.disabled = True

  def init_tests_panel(self):
    if not hasattr(self, 'output_view'):
      self.output_view = self.window.get_output_panel(RESULT_VIEW_NAME)
      self.output_view.set_name(RESULT_VIEW_NAME)
    self.clear_test_view()
    self.output_view.settings().set("file_path", self.file_path)

  def show_tests_panel(self):
    if self.tests_panel_showed:
      return
    self.window.run_command("show_panel", {"panel": "output."+RESULT_VIEW_NAME})
    self.tests_panel_showed = True

  def clear_test_view(self):
    self.output_view.set_read_only(False)
    edit = self.output_view.begin_edit()
    self.output_view.erase(edit, sublime.Region(0, self.output_view.size()))
    self.output_view.end_edit(edit)
    self.output_view.set_read_only(True)

  def append_data(self, proc, data, flush=False):
    self.buffered_data = self.buffered_data + data.decode("utf-8")
    str = self.buffered_data.replace(self.target_file_path, self.file_name).replace('\r\n', '\n').replace('\r', '\n')

    if flush == False:
      rsep_pos = str.rfind('\n')
      if rsep_pos == -1:
        # not found full line.
        return
      self.buffered_data = str[rsep_pos+1:]
      str = str[:rsep_pos+1]

    self.show_tests_panel()
    selection_was_at_end = (len(self.output_view.sel()) == 1 and self.output_view.sel()[0] == sublime.Region(self.output_view.size()))
    self.output_view.set_read_only(False)
    edit = self.output_view.begin_edit()
    self.output_view.insert(edit, self.output_view.size(), str)
    if selection_was_at_end:
      self.output_view.show(self.output_view.size())
    self.output_view.end_edit(edit)
    self.output_view.set_read_only(True)

    if flush:
      self.output_view.run_command("goto_line", {"line": 1})

  def update_status(self, msg, progress):
    sublime.status_message(msg + " " + progress)

  def proc_terminated(self, proc):
    if proc.returncode == 0:
      msg = self.file_name + ' fixjsstyle done!'
      self.replace_file_content()
    else:
      msg = ''
    self.append_data(proc, msg, True)

    # remove file.
    os.remove(self.target_file_path)

    ClosureLinterEventListener.disabled = False

  def replace_file_content(self):
    # open target file.
    f = open(self.target_file_path, 'r')

    # start to replace
    sel_region = self.file_view.sel()[0]

    edit = self.file_view.begin_edit()
    self.file_view.erase(edit, sublime.Region(0, self.file_view.size()))
    self.file_view.insert(edit, self.file_view.size(), f.read())
    self.file_view.end_edit(edit)

    self.file_view.show_at_center(sel_region)

    self.file_view.run_command('save')

    # done.
    f.close()

