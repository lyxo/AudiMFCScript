import curses
from datetime import datetime
from time import sleep
import webbrowser


import AbstractPrinter
from Watchdog import Watchdog
from WebCrawler import WebCrawler
from Database import Database
from AbstractPrinter import ConsoleLineData

AUTO_SCREEN_REFRESH_RATE = 2
AUTO_LOG_REFRESH_RATE = 5

LOG_LINES = 2
HEADER_INDENT = 5

STATE_NORMAL = 0
STATE_QUIT = 1
STATE_INPUT = 2

class CursesPrinter():


    color_map = dict()

    def init_colors():
        curses.start_color()
        curses.use_default_colors() 
        curses.init_pair(1, curses.COLOR_GREEN, -1)
        CursesPrinter.color_map[AbstractPrinter.colors.OKGREEN] = 1
        curses.init_pair(2, curses.COLOR_CYAN, -1)
        CursesPrinter.color_map[AbstractPrinter.colors.OKCYAN] = 2
        curses.init_pair(5, curses.COLOR_RED, -1)
        CursesPrinter.color_map[AbstractPrinter.colors.FAIL] = 5
        curses.init_pair(6, 8, -1)
        CursesPrinter.color_map[AbstractPrinter.colors.GREY] = 6

    def add_colored_string(window:curses.window, text_touple:tuple, color_overwrite = None):
        if color_overwrite == None:
            color_pair_id = CursesPrinter.color_map.get(text_touple[1])
            if color_pair_id != None:
                window.addstr(text_touple[0], curses.color_pair( color_pair_id))
            else:
                window.addstr(text_touple[0])
        else:
            window.addstr(text_touple[0], color_overwrite)
    

    def __init__(self, watchdog:Watchdog) -> None:
        self.screen:curses.window = None
        self.pad_quit = None
        self.window_header = None # TODO: make this a pad to make it easily resizable
        self.pad_vehicles = None
        self.pad_log = None
        self.pad_input = None
        self.display_row = 0
        self.selected_entry = 0
        self.log_lines = list()
        self.state = STATE_NORMAL

        self.pad_vehicles_timestamp = datetime.now()
        self.pad_log_timestamp = datetime.now()
        self.last_screen_status = -1

        self.watchdog = watchdog
        self.watchdog.start()

        self.input = ''
        self.search_string = ''

    def curses_main(self, screen):
        # screen gets initialized by curses wrapper
        self.screen = screen
        curses.noecho()
        curses.start_color()
        curses.use_default_colors()
        CursesPrinter.init_colors()
        self.pad_quit = curses.newpad(100,100)
        self.window_header = curses.newwin(0, 0, 0, HEADER_INDENT)
        self.pad_vehicles = curses.newpad(100,100)
        self.pad_log = curses.newpad(100,100)
        self.pad_input = curses.newpad(1,1)
        self.screen.keypad(True)
        self.screen.nodelay(True)
        curses.curs_set(0)
        self.screen.border(0)
        self.screen.refresh()
        self.print_all()
        
        while self.watchdog.run:
            try:
                c = self.screen.getch()

                if c == curses.KEY_RESIZE:
                    self.screen.clear()
                    self.screen.border(0)
                    self.screen.refresh()
                    self.print_all()
                
                elif self.state == STATE_NORMAL:
                    if c == 27 or c == ord('q'): # 27 = Escape character.
                        self.last_screen_status = 1
                        c = self.screen.getch()
                        if c == -1:
                            # Escape character was really pressed, not a escape sequence.
                            self.state = STATE_QUIT
                            self.print_all()

                    elif c == curses.KEY_UP or c == 450: # 450: keycode for from within vscode
                        self.selected_entry -= 1
                        self.print_vehicles()

                    elif c == curses.KEY_DOWN or c == 456: # 450: keycode for from within vscode
                        self.selected_entry += 1
                        self.print_vehicles()
                    
                    elif c == curses.KEY_ENTER or c == 10:
                        car = self.watchdog.database.cars.get(self.selected_car_id)
                        if car:
                            # mfchome_link = 'https://weare.audi/501_mfc/web/guest/jump?target=poolleas'
                            # webbrowser.open(mfchome_link,2)
                            car_link:str = car['web_data']['productInfo']['productURL'] # mynet-link
                            car_link = car_link.replace('https://vtp.audi.com/','https://weare.audi/001_vtpmfc4we/') # weareaudi link
                            webbrowser.open(car_link,2)
                    
                    elif c == 47:
                        self.input = "/"
                        self.state = STATE_INPUT
                        self.print_input()
                    
                    elif c == 58:
                        self.input = ":"
                        self.state = STATE_INPUT
                        self.print_input()

                    elif c > 0:
                        #c = self.screen.getch()
                        self.print_log([ConsoleLineData([(str(c),None)])])

                    # elif c == ord('p'):
                    #     if self.watchdog.run:
                    #         self.watchdog.stop()
                    #     else:
                    #         self.watchdog.start()
                    #     # TODO: update GUI to show status

                    else:
                        timediff_vehicles = datetime.now() - self.pad_vehicles_timestamp
                        if timediff_vehicles.seconds >= AUTO_SCREEN_REFRESH_RATE:
                            self.print_vehicles()
                        timediff_log = datetime.now() - self.pad_log_timestamp
                        if timediff_log.seconds >= AUTO_LOG_REFRESH_RATE:
                            self.print_log()
                
                elif self.state == STATE_INPUT:
                    if c == curses.KEY_ENTER or c == 10:
                        self.state = STATE_NORMAL
                        if self.input == ':a':
                            self.watchdog.database.audio = not self.watchdog.database.audio
                            self.print_log([ConsoleLineData([(f'Audio notification: {self.watchdog.database.audio}\n', None)])])
                        if self.input.startswith('/'):
                            self.search_string = self.input[1:]
                            self.watchdog.database.users['local']['search'] = self.search_string
                            self.print_all()
                        
                    elif c == 27:
                        c = self.screen.getch()
                        if c == -1:
                            self.input = ''
                            self.search_string = ''
                            self.state = STATE_NORMAL
                            self.print_all()
                    elif c == curses.KEY_BACKSPACE or c == 8:
                        if len(self.input) > 1:
                            self.input = self.input[:-1]
                            if self.input.startswith('/'):
                                self.search_string = self.input[1:]
                                self.print_vehicles()
                            self.print_input()

                    elif c >= 32 and c <= 126:
                        self.input += chr(c)
                        if self.input.startswith('/'):
                            self.search_string = self.input[1:]
                            self.print_vehicles()
                        self.print_input()           

                    else:
                        timediff_vehicles = datetime.now() - self.pad_vehicles_timestamp
                        if timediff_vehicles.seconds >= AUTO_SCREEN_REFRESH_RATE:
                            self.print_vehicles()
                        timediff_log = datetime.now() - self.pad_log_timestamp
                        if timediff_log.seconds >= AUTO_LOG_REFRESH_RATE:
                            self.print_log()
                            self.print_input()

                elif self.state == STATE_QUIT:
                    if c == ord('q'):
                        break
                    elif c == ord('c') or c == 10:
                        self.state = STATE_NORMAL
                        self.print_all()

                sleep(0.02)

            except KeyboardInterrupt:
                self.last_screen_status = 1
                if self.state == STATE_QUIT:
                    break
                else:
                    self.state = STATE_QUIT
                    self.print_all()

    def print_all(self):
        if self.state == STATE_NORMAL:
            self.print_header()
            self.print_vehicles()
            self.print_log()
        elif self.state == STATE_INPUT:
            self.print_header()
            self.print_vehicles()
            self.print_log()
            self.print_input()
        elif self.state == STATE_QUIT:
            self.print_quit() 

    def print_header(self):

         # Clear contents of this window
        self.window_header.erase()
        # Resize if screen size changed
        screen_size_y, screen_size_x = self.screen.getmaxyx()
        header_size_y, header_size_x = self.window_header.getmaxyx()
        header_size_x_desired = screen_size_x - HEADER_INDENT * 2
        if header_size_x != header_size_x_desired:
            self.window_header.resize(1, header_size_x_desired)
            header_size_x = header_size_x_desired
        line = " [©LyxoMFCScript] "
        str_last_update = "[Last Update: - ]" if self.watchdog.database.last_update == None else " [Last Update: " + self.watchdog.database.last_update.strftime("%H:%M:%S]")
        int_spaces = max(1, header_size_x - len(line) - len(str_last_update) - 1)
        if int_spaces > 0:
            line += "─" * int_spaces + str_last_update
        CursesPrinter.add_colored_string(self.window_header, (line, None))
        self.window_header.refresh()
        

    def print_vehicles(self):
        search_strings = ['']
        if len(self.search_string) > 0:
            search_strings = filter(None, self.search_string.split())
        lines_list = AbstractPrinter.generate_text_touples(self.watchdog.database.cars, self.watchdog.database.last_update, search_strings)

        self.pad_vehicles.clear()
        # Calculate position of pad on the screen
        max_screen_size_y, max_screen_size_x = self.screen.getmaxyx() # Returns height and witdh, not maximum indices (which are len() - 1!)
        pad_idx_start_y = 1 # 1 border
        pad_idx_start_x = 1 # 1 border
        pad_idx_end_y = max_screen_size_y - 2 - LOG_LINES - 1 # 1 for max_index=len()-1, 1 for border, # TODO: 1 for space?
        pad_idx_end_x = max_screen_size_x - 2  # 1 for max_index=len()-1, 1 for border
        max_displayable_lines = (pad_idx_end_y - pad_idx_start_y) + 1 # 1 for diff=0 means we have one index to print one line

        # Calculate needed size of pad to be able to contain all lines
        desired_pad_size_y = max(len(lines_list) + 1, max_displayable_lines)
        desired_pad_size_x = 0 # TODO: this calculation is nasty af
        for entry in lines_list:
            x_entry = 0
            for text_touple in entry.text_touples:
                x_entry += len(text_touple[0])
            desired_pad_size_x = max(x_entry, desired_pad_size_x) 
        desired_pad_size_x = max(desired_pad_size_x, pad_idx_end_x - pad_idx_start_x)
        pad_size_y,pad_size_x = self.pad_vehicles.getmaxyx()

        # Resize if necessary
        if pad_size_y != desired_pad_size_y or pad_size_x != desired_pad_size_x:
            self.pad_vehicles.resize(desired_pad_size_y, desired_pad_size_x)

        # Set selected entry accordingly
        if self.selected_entry > len(lines_list) - 1:
            self.selected_entry = len(lines_list) - 1
        elif self.selected_entry < 0:
            self.selected_entry = 0

        # Set display row accordingly so selected entry is visible
        if self.selected_entry > self.display_row + max_displayable_lines - 1:
            self.display_row = self.selected_entry - max_displayable_lines + 1
        if self.selected_entry < self.display_row:
            self.display_row = self.selected_entry

        if self.display_row > len(lines_list):
            self.display_row = len(lines_list) - 1
        if self.display_row < 0:
            self.display_row = 0

        for idx,console_line_data in enumerate(lines_list):
            if self.selected_entry == idx:
                self.selected_car_id = console_line_data.extra
                for text_touple in console_line_data.text_touples:
                    CursesPrinter.add_colored_string(self.pad_vehicles, text_touple, curses.A_REVERSE)
            else:
                for text_touple in console_line_data.text_touples:
                    CursesPrinter.add_colored_string(self.pad_vehicles, text_touple)


        self.pad_vehicles.refresh(self.display_row, 0, pad_idx_start_y, pad_idx_start_x , pad_idx_end_y, pad_idx_end_x)
        self.pad_vehicles_timestamp = datetime.now()

    def print_log(self, console_log_lines=[]):

        self.pad_log.erase()

        log_lines = list()

        #log_lines.append(ConsoleLineData([(str(self.selected_entry),None)]))

        if self.watchdog.exception_status != None:
            log_lines = log_lines + (AbstractPrinter.generate_error_touples(self.watchdog.exception_status))

        log_lines = log_lines + console_log_lines
        
        # Calculate position of pad on the screen
        max_screen_size_y, max_screen_size_x = self.screen.getmaxyx() # Returns height and witdh, not maximum indices (which are len() - 1!)
        pad_idx_end_y = max_screen_size_y - 2 # 1 for max_index = len -1, 1 for border 
        pad_idx_end_x = max_screen_size_x - 2 # 1 for max_index = len -1, 1 for border
        # pad_idx_start_y = max(pad_idx_end_y - 1, 1) # -1 for at least two lines, 1 for top border
        pad_idx_start_y = pad_idx_end_y - 1
        pad_idx_start_x = 1 # 1 for border
        max_displayable_lines = (pad_idx_end_y - pad_idx_start_y) + 1 # 1 for diff=0 means we have one index to print one line
        max_line_length = (pad_idx_end_x - pad_idx_start_x) + 1 # 1 for diff=0 means we have one index to print one line

        if len(log_lines) > 0:
            # Calculate needed size of pad to be able to contain all lines
            max_y = max(len(log_lines), max_displayable_lines)
            pad_y,pad_x = self.pad_log.getmaxyx()
            # Resize pad if it changed in size
            if pad_x != max_screen_size_x or pad_y != max_y:
                self.pad_log.resize(max_y, max_screen_size_x)
            
            for console_line_data in log_lines:
                for text_touple in console_line_data.text_touples:
                    # TODO: set cursor to modify where the text is printed
                    printed_string = (text_touple[0][:max_line_length - 2] + '..') if len(text_touple[0]) > max_line_length else text_touple[0]
                    CursesPrinter.add_colored_string(self.pad_log, (printed_string, text_touple[1]))

        self.pad_log.refresh(0, 0, pad_idx_start_y, 1, pad_idx_end_y, max_screen_size_x - 2)
        self.pad_log_timestamp = datetime.now()

    def print_input(self):
        self.pad_input.erase()
        
        max_screen_size_y, max_screen_size_x = self.screen.getmaxyx() # Returns height and witdh, not maximum indices (which are len() - 1!)
        pad_size_y, pad_size_x = self.pad_input.getmaxyx()
        if pad_size_y != 1 or pad_size_x != max_screen_size_x -2:
            self.pad_input.resize(1, max_screen_size_x - 2)
        CursesPrinter.add_colored_string(self.pad_input, (self.input, None))
        self.pad_input.refresh(0, 0, max_screen_size_y - 2, 1, max_screen_size_y - 2, max_screen_size_x - 2)


    def print_quit(self):
        self.pad_quit.erase()
        output_string = '(C)ontinue, (q)uit'
        screen_max_y, screen_max_x = self.screen.getmaxyx()
        pad_max_y, pad_max_x = self.pad_quit.getmaxyx()
        if screen_max_y != pad_max_y - 2 or screen_max_x != pad_max_x - 2:
            self.pad_quit.resize(screen_max_y - 2, max(len(output_string) + 1, screen_max_x - 2))
        self.pad_quit.addstr(output_string)
        self.pad_quit.refresh(0, 0, 1, 1, screen_max_y - 2, screen_max_x - 2)

    def start_wrapper(self):
        curses.wrapper(self.curses_main)