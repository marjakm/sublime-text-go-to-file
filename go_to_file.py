import sublime, sublime_plugin
import os, string, subprocess
import re

class GoToFile(sublime_plugin.TextCommand):
    def run(self, edit):
        for region in self.view.sel():
            # Collect the texts that may possibly be filenames
            quoted_text = self.get_quoted_selection(region).split(os.sep)[-1]
            selected_text = self.get_selection(region)
            text_on_cursor = None
            if region.begin() == region.end():
                word = self.view.word(region)
                if not word.empty():
                    text_on_cursor = self.view.substr(word)
                # view.run_command("expand_selection", {"to": "word"})
                # selected_text = self.get_selection(region)
            whole_line = self.get_line(region)
            candidates = [selected_text, self.extract_candidate_from_line(), quoted_text, text_on_cursor, whole_line]
            self.try_open(candidates)

    def try_open(self, candidates):
        for text in candidates:
            if text is None or len(text) == 0:
                continue

            self.potential_files = self.get_filename(text)
            if len(self.potential_files) > 0:
                break

        if len(self.potential_files) > 1:
            self.view.window().show_quick_panel(self.potential_files, self.open_file)
        elif len(self.potential_files) == 1:
            print("Opening file '%s'" % (self.potential_files[0]))
            self.view.window().open_file(self.potential_files[0])
        else:
            sublime.error_message("No file found")


    def open_file(self, selected_index):
        if selected_index != -1:
            file = self.potential_files[selected_index]
            print("Opening file '%s'" % (file))
            self.view.window().open_file(file)


    def get_selection(self, region):
        return self.view.substr(region).strip()


    def get_line(self, region):
        return self.view.substr(self.view.line(region)).strip()


    def get_quoted_selection(self, region):
        text = self.view.substr(self.view.line(region))
        position = self.view.rowcol(region.begin())[1]
        quoted_text = self.expand_within_quotes(text, position, '"')
        if not quoted_text:
            quoted_text = self.expand_within_quotes(text, position, '\'')
        return quoted_text


    def expand_within_quotes(self, text, position, quote_character):
        open_quote = text.rfind(quote_character, 0, position)
        close_quote = text.find(quote_character, position)
        return text[open_quote+1:close_quote] if (open_quote > 0 and close_quote > 0) else ''

    @property
    def envdct(self):
        if "_envdct" not in dir(self) or not self._envdct:
            var_frmt = re.compile("^(\w*)[\s=]*([\w/\.]*)\s*$")
            varstr = str( subprocess.check_output(["zsh", "-li", "-c", "env"]), encoding='utf8' )
            self._envdct = dict()
            for line in varstr.split("\n"):
                m = var_frmt.match(line)
                if m:
                    self._envdct[m.group(1)] = m.group(2)
        return self._envdct

    def handle_env_variables(self, text):
        def repl(m):
            var = m.group(1)
            if var in self.envdct:
                return self.envdct[var]
            else:
                return m.group(0)
        pattern = re.compile("\$\(*(\w*)\)*")
        return re.sub(pattern, repl, text)

    def get_filename(self, text):
        results = []
        text = text.replace('\\', os.sep).replace(os.sep+os.sep, os.sep).replace('import ', '').replace('use ', '').replace(';', '').strip()
        text = self.handle_env_variables(text)
        print("get filename " + text)
        if text[0] == "/":
            if os.path.exists(text):
                results += [text]
        else:
            directories = self.view.window().folders()
            for directory in directories:
                for dirname, _, files in self.walk(directory):
                    for file in files:
                        fileName = dirname + os.sep + file
                        if re.search(text, fileName):
                            results += [fileName]
        print(results)
        return results


    def walk(self, directory):
        for dir, dirnames, files in os.walk(directory):
            dirnames[:] = [dirname for dirname in dirnames]
            yield dir, dirnames, files


    def extract_candidate_from_line(self):
        view = sublime.active_window().active_view()
        for sel in view.sel():
            patternStr = view.substr(view.word(sel)).strip()
            lineStr = view.substr(view.line(sel)).strip()
            result = re.search( '(([^(\s|=|\+|\.)|,]*)'+patternStr+'[^(\s|:|;|,|\.|\(]*)', lineStr )
            if result != None:
                return result.group()

class FileInfo(sublime_plugin.WindowCommand):
    def run(self):
        path = self.current_file()
        sublime.set_clipboard(path)
        sublime.status_message(path)

    def current_file(self):
        return self.window.active_view().file_name()
