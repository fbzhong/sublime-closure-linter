import os
import re
import shutil
import sublime
import sublime_plugin
from const import *
from listener import *
from statusprocess import *
from asyncprocess import *

class ShowClosureLinterResultCommand(sublime_plugin.WindowCommand):
  """show closure linter result"""
  def run(self):
    self.window.run_command("show_panel", {"panel": "output."+RESULT_VIEW_NAME})

class ClosureLinterCommand(sublime_plugin.WindowCommand):
  def run(self):
    s = sublime.load_settings(SETTINGS_FILE)

    file_path = self.window.active_view().file_name()
    file_name = os.path.basename(file_path)

    self.debug = s.get('debug', False)
    self.buffered_data = ''
    self.file_path = file_path
    self.file_name = file_name
    self.is_running = True
    self.tests_panel_showed = False
    self.ignored_error_count = 0
    self.ignore_errors = s.get('ignore_errors', [])

    self.init_tests_panel()

    cmd = '"' + s.get('gjslint_path', 'jslint') + '" ' + s.get('gjslint_flags', '') + ' "' + file_path + '"'
    if self.debug:
      print "DEBUG: " + str(cmd)

    AsyncProcess(cmd, self)
    StatusProcess('Starting Closure Linter for file ' + file_name, self)

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

  def append_data(self, proc, data, end=False):
    self.buffered_data = self.buffered_data + data.decode("utf-8")
    data = self.buffered_data.replace(self.file_path, self.file_name).replace('\r\n', '\n').replace('\r', '\n')

    if end == False:
      rsep_pos = data.rfind('\n')
      if rsep_pos == -1:
        # not found full line.
        return
      self.buffered_data = data[rsep_pos+1:]
      data = data[:rsep_pos+1]

    # ignore error.
    text = data
    if len(self.ignore_errors) > 0:
      text = ''
      for line in data.split('\n'):
        if len(line) == 0:
          continue
        ignored = False
        for rule in self.ignore_errors:
          if re.search(rule, line):
            ignored = True
            self.ignored_error_count += 1
            if self.debug:
              print "text match line "
              print "rule = " + rule
              print "line = " + line
              print "---------"
            break
        if ignored == False:
          text += line + '\n'

    self.show_tests_panel()
    selection_was_at_end = (len(self.output_view.sel()) == 1 and self.output_view.sel()[0] == sublime.Region(self.output_view.size()))
    self.output_view.set_read_only(False)
    edit = self.output_view.begin_edit()
    self.output_view.insert(edit, self.output_view.size(), text)

    if end:
      text = '\nclosure linter: ignored ' + str(self.ignored_error_count) + ' errors.\n'
      self.output_view.insert(edit, self.output_view.size(), text)

    # if selection_was_at_end:
    #   self.output_view.show(self.output_view.size())
    self.output_view.end_edit(edit)
    self.output_view.set_read_only(True)

    # if end:
    #   self.output_view.run_command("goto_line", {"line": 1})

  def update_status(self, msg, progress):
    sublime.status_message(msg + " " + progress)

  def proc_terminated(self, proc):
    if proc.returncode == 0:
      msg = self.file_name + ' lint free!'
    else:
      msg = ''
    self.append_data(proc, msg, True)

    ClosureLinterEventListener.disabled = False
