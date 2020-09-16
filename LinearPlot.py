#  Copyright (c) 2020 David Young.
#  All rights reserved.
#

from math import log10, floor
from tkinter import Scrollbar, Frame, Canvas, Label, StringVar, Checkbutton, BooleanVar, Entry, Tk, Menu, filedialog, \
    font, Listbox, Button, Scale, messagebox
from matplotlib import use

use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
import matplotlib.font_manager as font_manager
import numpy as np


# from numpy import array, ones, vstack, dot, linalg, sqrt, cov, mean, asarray, sum


# AFTER RELEASE
# TODO Add data point weighting for u(x) and u(y) (What is the point of this in LinearFit???)
# TODO Add ability to find the standard error in the y-intercept (Is this even possible? Why does LinearFit have it???)
# TODO Hide scrollbar when not in use
# TODO Allow user to have the graph results below the graph itself
# TODO Decrease lag when resizing the window - Almost impossible
# TODO Remove glitches when enabling custom graph labels
# TODO Allow user to save the results
# TODO Figure out why when the user imports a data point file larger than about 5 points the graph lags behind
#  the inputs by one row

# BEFORE RELEASE
# TODO Make the How-To-Use page
# TODO Make about page
# TODO Decide whether "Save As" should us a cascade or just be part of file_menu
# TODO Add function to check github if a new version of the program is available
# TODO Fix custom plot labels remaining when user imports a new graph


def significant_figures(value, figs):
    return value if value == 0 else round(value, -int(floor(log10(abs(value)))) + (figs - 1))


def get_graph_data(x=None, y=None, initial=True, sigfigs=6):
    if not initial:
        slope, intercept, rvalue, stderr = linregress_custom(x, y)
        return f'm = {significant_figures(slope, sigfigs)} ± {significant_figures(stderr, sigfigs)}', \
               f'c = {significant_figures(intercept, sigfigs)}', \
               f'R\u00b2 = {significant_figures(rvalue, sigfigs)}'
    else:
        return 'm = 0.0 ± 0.0', 'c = 0.0', 'R\u00b2 = 0.0'


def add_to_xy(a_dict):
    x, y = {}, {}
    for k, v in a_dict.items():
        if 'x' in k:
            x.update({k: v})
        else:
            y.update({k: v})

    return x, y


# KEEP FOR NOW
'''def pearson_corr_coef(x_values, y_values):
    """
    If not using linregress from scipy.stats use this and the following code:

    # Use this for the y-intercept and gradient
    v = np.polyfit(xs, ys, 1)
    m, c = v[0], v[1]
    # Custom correlation
    r = pearson_corr_coef(xs, ys)
    """
    # Get sample size
    sample_size = len(x_values)

    # Calculate sigma(x)
    sigma_x = np.sum(x_values)

    # Calculate sigma(y)
    sigma_y = np.sum(y_values)

    # Calculate sigma(xy)
    x, y = iter(x_values), iter(y_values)
    sigma_xy = 0
    for i in range(sample_size):
        sigma_xy += next(x) * next(y)

    # Calculate sigma(x^2)
    x = iter(x_values)
    sigma_x_squared = 0
    for i in range(sample_size):
        sigma_x_squared += next(x) ** 2

    # Calculate sigma(x^2)
    y = iter(y_values)
    sigma_y_squared = 0
    for i in range(sample_size):
        sigma_y_squared += next(y) ** 2

    result = (sample_size * sigma_xy - sigma_x * sigma_y) / (((sample_size * sigma_x_squared - sigma_x ** 2) *
                                                              (sample_size * sigma_y_squared - sigma_y ** 2)) ** 0.5)

    return result'''


def linregress_custom(x_arr, y_arr):
    """
    Code copied from scipy.stats._stats_mstats_common.py

    I copied this code because I have no need of the entire scipy package, only the one section for calculating
    information about the line.
    """
    if y_arr is None:
        x = np.asarray(x_arr)
        if x.shape[0] == 2:
            x, y = x
        elif x.shape[1] == 2:
            x, y = x.T
        else:
            msg = (f"If only `x` is given as input, it has to be of shape (2, N) or (N, 2), "
                   f"provided shape was {str(x.shape)}")
            raise ValueError(msg)
    else:
        x = np.asarray(x_arr)
        y = np.asarray(y_arr)

    if x.size == 0 or y.size == 0:
        raise ValueError("Inputs must not be empty.")

    n = len(x)
    xmean = np.mean(x, None)
    ymean = np.mean(y, None)

    # average sum of squares:
    ssxm, ssxym, ssyxm, ssym = np.cov(x, y, bias=True).flat
    r_num = ssxym
    r_den = np.sqrt(ssxm * ssym)
    if r_den == 0.0:
        r = 0.0
    else:
        r = r_num / r_den
        # test for numerical error propagation
        if r > 1.0:
            r = 1.0
        elif r < -1.0:
            r = -1.0

    df = n - 2
    slope = r_num / ssxm
    intercept = ymean - slope * xmean
    if n == 2:
        sterrest = 0.0
    else:
        sterrest = np.sqrt((1 - r ** 2) * ssym / ssxm / df)

    return slope, intercept, r, sterrest


# noinspection PyMethodMayBeStatic
class Main:
    def __init__(self):
        self.shown_y = False
        self.shown_x = False
        self.root = Tk()
        self.root.title("Linear Plot")
        self.inputs = {}
        self.x_array, self.y_array = [], []
        self.plot_title = 'Linear Plot'
        self.row_number_tracker, self.number_of_sigfigs, self.lowest_row_after_deletion = 0, 6, 0
        self.axis_label_pady = 51
        self.ready_to_plot = False
        self.global_font = StringVar()
        self.global_font.set("Arial")
        self.matplotlib_font = FontProperties()
        self.matplotlib_font.set_name(self.global_font.get())
        self.label_font = font.Font(family=self.global_font.get(), size=18, underline=1)
        self.button_font = font.Font(family=self.global_font.get())
        self.result_font = font.Font(family=self.global_font.get(), size=20, underline=1)
        self.result_value_font = font.Font(family=self.global_font.get(), size=18)

        self.menubar = Menu(self.root)

        # Title
        self.title_frame = Frame(self.root)
        self.title = Label(self.title_frame, text="Linear Plot", font=font.Font(family=self.global_font.get(), size=20))
        self.title.pack(pady=(3, 0))

        # Adds small separation bar between the title and the rest of the window
        self.title_separation = Frame(self.root, bg='grey')

        # Graph on the left
        self.graph_area = Canvas(self.root, width=625, height=625)

        self.graph_figure = Figure(figsize=(7, 7), dpi=100)
        self.sub_plot = self.graph_figure.add_subplot(111)
        self.sub_plot.set_ylabel("Y", fontproperties=self.matplotlib_font)
        self.sub_plot.set_xlabel("X", fontproperties=self.matplotlib_font)
        self.sub_plot.set_title("Linear Plot", fontproperties=self.matplotlib_font, fontsize=14)
        self.sub_plot.grid(which='major', color='#999999', linestyle='-')
        self.sub_plot.minorticks_on()
        self.sub_plot.grid(which='minor', color='#999999', linestyle='-', alpha=0.2)
        self.graph_canvas = FigureCanvasTkAgg(self.graph_figure, self.graph_area)

        # Adds the copyright notice to the bottom of the window
        self.copyright_label = Label(self.root, text="Copyright \u00A9 2020  David Young  All rights reserved.",
                                     font='Helvetica 8')

        # Creates the custom header frame
        self.custom_header_frame = Frame(self.root, width=390)
        self.custom_header_label = Label(self.custom_header_frame, text='Graph Labels:', font=self.label_font, width=18)
        self.x_entry_label_var = StringVar()
        self.y_entry_label_var = StringVar()
        self.x_entry_label_var.set('X')
        self.y_entry_label_var.set('Y')
        self.x_entry_label = Entry(self.custom_header_frame, textvariable=self.x_entry_label_var, width=20,
                                   justify='center')
        self.y_entry_label = Entry(self.custom_header_frame, textvariable=self.y_entry_label_var, width=20,
                                   justify='center')

        self.already_clicked_x = False
        self.already_clicked_y = False
        self.x_entry_label.bind("<FocusIn>", self.handle_custom_headers)
        self.y_entry_label.bind("<FocusIn>", self.handle_custom_headers)

        # Adds the custom header entries to the grid
        self.custom_header_label.grid(row=0, column=0, columnspan=2, sticky='n')
        self.x_entry_label.grid(row=1, column=0, sticky='n')
        self.y_entry_label.grid(row=1, column=1, sticky='n')

        # Creates the input labels X and Y
        self.input_labels = Frame(self.root, width=390)
        self.x_label = Label(self.input_labels, text="X Axis", font=self.label_font, width=18)
        self.y_label = Label(self.input_labels, text="Y Axis", font=self.label_font, width=14)

        # Adds the X and Y labels to the grid
        self.x_label.grid(row=0, column=0, sticky='n')
        self.y_label.grid(row=0, column=1, sticky='n')

        # Blank frame for keeping the input area in line with teh top of the graph area
        self.blank_frame = Frame(self.root, width=390, height=1)

        # Input area and result area
        self.input_area = ScrollFrame(self.root, width=390, height=392)
        self.result_area = Frame(self.root, width=400)

        # Creates the first input boxes
        self.x_input = Entry(self.input_area.viewPort, name='x0', justify='center')
        self.y_input = Entry(self.input_area.viewPort, name='y0', justify='center')

        # Binds the input handling function to the entry boxes
        self.x_input.bind("<FocusOut>", self.handle_inputs)
        self.y_input.bind("<FocusOut>", self.handle_inputs)

        # Adds the first inputs to the grid
        self.x_input.grid(row=0, column=0, sticky='n')
        self.y_input.grid(row=0, column=1, sticky='n')

        # Creates the graph and entry options frame
        self.option_area = Frame(self.root, width=390)
        self.grid_lines = BooleanVar()
        self.custom_headers = BooleanVar()
        self.custom_headers_currently_enabled = False
        self.enable_grid_lines = Checkbutton(self.option_area, text='Disable Grid Lines', onvalue=True, offvalue=False,
                                             variable=self.grid_lines, selectcolor='blue',
                                             command=self.grid_lines_button, font=self.button_font)
        self.enable_custom_headers = Checkbutton(self.option_area, text='Enable Custom Graph Labels', onvalue=True,
                                                 offvalue=False, variable=self.custom_headers, selectcolor='blue',
                                                 command=self.custom_headers_button, font=self.button_font)

        self.enable_grid_lines.grid(row=0, column=0)
        self.enable_custom_headers.grid(row=0, column=1)

        # Creates the "Best Fit Values:" text with a underline
        self.best_fit = Label(self.result_area, text="Best Fit values:", font=self.result_font)

        # Creates the results text for m and c
        m, c, r = get_graph_data(initial=True)
        self.m_var, self.c_var, self.r_var = StringVar(), StringVar(), StringVar()
        self.m_var.set(m), self.c_var.set(c), self.r_var.set(r)

        self.m = Label(self.result_area, textvariable=self.m_var, font=self.result_value_font)
        self.c = Label(self.result_area, textvariable=self.c_var, font=self.result_value_font)

        # Creates the correlation text
        self.correlation = Label(self.result_area, text="Correlation:", font=self.result_font)

        # Creates the correlation result
        self.r = Label(self.result_area, textvariable=self.r_var, font=self.result_value_font)

        # Packs the result area
        self.best_fit.pack(side='top', anchor='nw')
        self.m.pack(side='top', anchor='nw')
        self.c.pack(side='top', anchor='nw')
        self.correlation.pack(side='top', anchor='nw')
        self.r.pack(side='top', anchor='nw')

        def handle_window_size(event=None):
            """
            Handles the size of the input area based on the size of the window
            :param event:
            :return:
            """
            h = self.root.winfo_height()
            # This equation was found using this program :)
            if self.custom_headers_currently_enabled:
                self.input_area.canvas.config(height=(0.875 * h - 336.625))
                self.blank_frame.config(height=(0.113553 * h - 79.5275))
            else:
                self.input_area.canvas.config(height=(0.875 * h - 275.625))
                self.blank_frame.config(height=(0.120879 * h - 91.1099))

            self.root.update_idletasks()

        # Assigns the function which changes the size of the input area to the window
        self.root.bind("<Configure>", handle_window_size)
        # self.root.protocol(name="WM_SIZE", func=handle_window_size)

        # Packs all of the frames, labels, and graph into the window
        self.title_frame.pack(side='top')
        self.copyright_label.pack(side='top')
        self.title_separation.pack(side='top', padx=(5, 5), pady=(10, 0), fill='x')
        self.graph_canvas.get_tk_widget().pack(fill='both', expand=True)
        self.graph_area.pack(side='left', anchor='ne', fill='both', expand=True)
        self.blank_frame.pack(anchor='w', padx=(0, 3), pady=(44, 2))
        self.input_labels.pack(anchor='w', padx=(0, 3), pady=(2, 2))
        self.input_area.pack(anchor='w', padx=(0, 3), pady=(2, 2))
        self.option_area.pack(anchor='w', padx=(0, 3), pady=(2, 2))
        self.result_area.pack(anchor='w', padx=(0, 3), pady=(2, 3))

        self.root.config(menu=self.menubar)

        self.make_menu()
        # Sets the minimum size for the window
        self.root.update_idletasks()
        self.root.minsize(self.root.winfo_width(), self.root.winfo_height())

        '''def on_closing():
            if messagebox.askokcancel("Quit", "Do you want to quit?"):
                self.root.quit()

        self.root.protocol("WM_DELETE_WINDOW", on_closing)'''

        # Runs the window
        self.root.mainloop()

    # COMPLETE
    def handle_inputs(self, event):
        # Automatically scrolls to the bottom of the input area
        self.input_area.canvas.yview_moveto(1)
        name = str(event.widget).split(".")[-1]
        # Updates the inputs dictionary
        if event.widget.get() != '':
            self.inputs.update({name: event.widget.get()})

            # Only allows a new entry row to be created once the x-entry (or y-entry) field has been completed
            # And prevents the GUI from creating more rows just by clicking on a x-entry field
            if ('x' in name or 'y' in name) and int(name[1:]) == self.row_number_tracker:
                self.row_number_tracker += 1

                # Creates the next row of entry areas
                self.x_input = Entry(self.input_area.viewPort, name=f'x{self.row_number_tracker}', justify='center')
                self.y_input = Entry(self.input_area.viewPort, name=f'y{self.row_number_tracker}', justify='center')

                # Binds the handle_inputs function to a FocusOut event
                self.x_input.bind("<FocusOut>", self.handle_inputs)
                self.y_input.bind("<FocusOut>", self.handle_inputs)

                # Slots the entry fields into the grid
                self.x_input.grid(row=self.row_number_tracker + 1, column=0, sticky='n')
                self.y_input.grid(row=self.row_number_tracker + 1, column=1, sticky='n')

            if self.row_number_tracker >= 2 and self.graphing():
                self.ready_to_plot = True
                self.graph_line(self.graph_canvas, self.sub_plot, self.grid_lines.get())
                # Using a double invoke of the grid_lines button command to update the plot
                # Very crude I know, may fix later
                self.enable_grid_lines.invoke()
                self.enable_grid_lines.invoke()

        elif name in self.inputs.keys():
            del self.inputs[name]
            self.lowest_row_after_deletion = int(name[1:])
            if self.row_number_tracker >= 2 and self.graphing() and self.lowest_row_after_deletion >= 2:
                self.ready_to_plot = True
                self.graph_line(self.graph_canvas, self.sub_plot, self.grid_lines.get())

    # INCOMPLETE
    def make_menu(self):

        # Creates and adds the menu cascade for saving the current graph
        file_menu = Menu(self.menubar, tearoff=0)
        save_menu = Menu(self.menubar, tearoff=0)
        save_menu.add_command(label="Plain Text File", command=lambda: self.save_graph_data('txt'))
        save_menu.add_command(label="CSV File", command=lambda: self.save_graph_data('csv'))
        file_menu.add_cascade(label="Save As", menu=save_menu)
        # file_menu.add_command(label="Plain Text File", command=lambda: self.save_graph_data('txt'))
        # file_menu.add_command(label="CSV File", command=lambda: self.save_graph_data('csv'))
        file_menu.add_separator()
        file_menu.add_command(label="Import Graph", command=self.import_graph)
        file_menu.add_separator()
        file_menu.add_command(label="Screenshot Graph - TBA", command=self.save_fig)
        # file_menu.add_command(label="Screenshot Results", command=self.save_results)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.destroy)
        self.menubar.add_cascade(label="File", menu=file_menu)

        edit_menu = Menu(self.menubar, tearoff=0)
        edit_menu.add_command(label="Change Font", command=self.change_fonts)
        edit_menu.add_command(label="Change Graph Title", command=self.change_plot_title)
        edit_menu.add_command(label="Change Significant Figures of Results", command=self.change_number_of_sigfigs)
        self.menubar.add_cascade(label="Edit", menu=edit_menu)

        help_menu = Menu(self.menubar, tearoff=0)
        help_menu.add_command(label="How to Use", command=None)
        help_menu.add_command(label="About Linear Plot", command=None)
        self.menubar.add_cascade(label="Help", menu=help_menu)

        self.root.update_idletasks()

    # COMPLETE
    def import_graph(self):

        def make_entry_row():
            # Creates the next row of entry areas
            self.x_input = Entry(self.input_area.viewPort, name=f'x{self.row_number_tracker}', justify='center')
            self.y_input = Entry(self.input_area.viewPort, name=f'y{self.row_number_tracker}', justify='center')

            # Binds the handle_inputs function to a FocusOut event
            self.x_input.bind("<FocusOut>", self.handle_inputs)
            self.y_input.bind("<FocusOut>", self.handle_inputs)

            # Slots the entry fields into the grid
            self.x_input.grid(row=self.row_number_tracker + 1, column=0, sticky='n')
            self.y_input.grid(row=self.row_number_tracker + 1, column=1, sticky='n')

        # Dunno if I should use this: filetypes=(("Text file", "*.txt"), ("Comma-separated values", "*.csv"))
        f = filedialog.askopenfile(title='Select a File', parent=self.root)
        # Reads the file lines
        if f is not None:
            file_lines = f.readlines()
            if len(file_lines) < 2:
                messagebox.showwarning(message="There are too few values in this file to graph")
            else:
                if not file_lines[0].isnumeric():
                    if not self.custom_headers_currently_enabled:
                        self.enable_custom_headers.invoke()
                    self.custom_headers_currently_enabled = True
                    self.y_entry_label_var.set(file_lines[0][file_lines[0].find(',') + 1:])
                    self.y_entry_label_var.set(file_lines[0][file_lines[0].find(',') + 1:])
                    self.enable_grid_lines.invoke()
                    self.already_clicked_y = True
                    self.x_entry_label_var.set(file_lines[0][:file_lines[0].find(',')])
                    self.enable_grid_lines.invoke()
                    self.already_clicked_x = True

                    self.y_entry_label_var.set(self.y_entry_label_var.get()[:-1])

                highest_current_row = 0
                try:
                    # Finds the highest row number that has already
                    # been completed (allows previous rows to be overwritten)
                    x, y = add_to_xy(self.inputs)
                    x = sorted(x.items(), key=lambda l: int(l[0][1:]))
                    y = sorted(y.items(), key=lambda l: int(l[0][1:]))
                    if x[-1][0][1:] == y[-1][0][1:]:
                        highest_current_row = x[-1][0][1:]
                except IndexError:
                    pass

                # Removes any remaining rows which have been already inputted
                # but have a number of rows larger than the file
                current_rows = iter(self.input_area.viewPort.winfo_children())
                # Loops through the file lines
                for line_index in range(len(file_lines) if file_lines[0].isnumeric() else len(file_lines[1:])):
                    # Gets the current data on the line in the file
                    line = file_lines[line_index].rstrip() \
                        if file_lines[0].isnumeric() \
                        else file_lines[line_index + 1].rstrip()

                    # Assigns the corresponding values to their respective variable
                    x_val = line[:line.find(',')]
                    y_val = line[line.find(',') + 1:]

                    # If the user imports data when only the first row exists
                    if highest_current_row == 0 and self.row_number_tracker == 0:
                        # We must add the first line of data points to the existing first row of entries
                        x_row = next(current_rows)
                        y_row = next(current_rows)
                        # Delete old data in the row
                        x_row.delete(0, 'end')
                        x_row.insert(0, x_val)
                        # Add new data to the row
                        y_row.delete(0, 'end')
                        y_row.insert(0, y_val)
                        # Add values to the input dictionary
                        self.inputs.update({f'x0': x_val, f'y0': y_val})
                        # Update the number of rows available
                        self.row_number_tracker += 1

                    # If the current line has already been created in the GUI
                    elif highest_current_row != 0 and line_index <= int(highest_current_row):
                        # We must add the first line of data points to the existing first row of entries
                        x_row = next(current_rows)
                        y_row = next(current_rows)
                        # Delete old data in the row
                        x_row.delete(0, 'end')
                        x_row.insert(0, x_val)
                        # Add new data to the row
                        y_row.delete(0, 'end')
                        y_row.insert(0, y_val)
                        # Add values to the input dictionary
                        self.inputs.update({f'x{self.row_number_tracker}': x_val, f'y{self.row_number_tracker}': y_val})
                        # Not updating the number of rows available because we do not want the graphing function to get
                        # confused by having jumps in row indexes.

                    # If the row does not exist yet
                    elif int(highest_current_row) <= len(file_lines):
                        # Create new row
                        make_entry_row()
                        # Insert values into the corresponding cells
                        self.x_input.insert(0, x_val)
                        self.y_input.insert(0, y_val)
                        # Add the values to the input dictionary
                        self.inputs.update({f'x{self.row_number_tracker}': x_val, f'y{self.row_number_tracker}': y_val})
                        # Update the number of rows available
                        self.row_number_tracker += 1

                try:
                    # Finds the highest row number that has already
                    # been completed (allows previous rows to be overwritten)
                    x, y = add_to_xy(self.inputs)
                    x = sorted(x.items(), key=lambda l: int(l[0][1:]))
                    y = sorted(y.items(), key=lambda l: int(l[0][1:]))
                    if x[-1][0][1:] == y[-1][0][1:]:
                        highest_current_row = x[-1][0][1:]

                    # Removes any rows that are not included in the imported data points
                    # This only occurs when there are more data points being graphed than what are being imported
                    if int(highest_current_row) >= len(file_lines):
                        remaining_rows = iter(self.input_area.viewPort.winfo_children()[len(file_lines) * 2:])
                        while True:
                            current_cell = next(remaining_rows)
                            if int(current_cell.winfo_name()[1:]) == int(highest_current_row):
                                del self.inputs[current_cell.winfo_name()]
                                current_cell.destroy()
                                current_cell = next(remaining_rows)
                                del self.inputs[current_cell.winfo_name()]
                                current_cell.destroy()
                                self.row_number_tracker = int(
                                    self.input_area.viewPort.winfo_children()[-1].winfo_name()[1:]) + 1
                                make_entry_row()
                                break
                            else:
                                try:
                                    del self.inputs[current_cell.winfo_name()]
                                    current_cell.destroy()
                                except KeyError:
                                    current_cell.destroy()

                except IndexError:
                    pass

                # Creates the last empty row
                make_entry_row()

                if self.graphing():
                    self.ready_to_plot = True
                    self.graph_line(self.graph_canvas, self.sub_plot, self.grid_lines.get())

    # COMPLETE
    def change_number_of_sigfigs(self):
        sigfigs_root = Tk()
        sigfigs_root.title('Number of Significant Figures')

        def ok_clicked_event(event):
            self.number_of_sigfigs = sigfigs_slider.get()
            self.graph_line(self.graph_canvas, self.sub_plot, self.grid_lines.get())
            sigfigs_root.destroy()

        def ok_clicked():
            self.number_of_sigfigs = sigfigs_slider.get()
            self.graph_line(self.graph_canvas, self.sub_plot, self.grid_lines.get())
            sigfigs_root.destroy()

        sigfigs_slider = Scale(sigfigs_root, from_=6, to=50, orient='horizontal', length=200)
        sigfigs_slider.set(self.number_of_sigfigs)
        sigfigs_slider.grid(column=0, row=0, columnspan=2)

        cancel_button = Button(sigfigs_root, text="Cancel", command=lambda: sigfigs_root.destroy())
        cancel_button.grid(column=0, row=1)

        ok_button = Button(sigfigs_root, text="OK", command=ok_clicked)
        ok_button.grid(column=1, row=1)

        sigfigs_root.bind('<Return>', ok_clicked_event)
        sigfigs_root.resizable(False, False)
        sigfigs_root.mainloop()

    # COMPLETE
    def change_plot_title(self):
        title_root = Tk()
        title_root.title('Change Plot Title')

        def change_ok_state(event):
            ok_button['state'] = 'normal'

        def ok_clicked_event(event):
            self.plot_title = title_entry.get()
            self.graph_line(self.graph_canvas, self.sub_plot, self.grid_lines.get())
            title_root.destroy()

        def ok_clicked():
            self.plot_title = title_entry.get()
            self.graph_line(self.graph_canvas, self.sub_plot, self.grid_lines.get())
            title_root.destroy()

        title_entry = Entry(title_root)
        title_entry.bind('<FocusIn>', change_ok_state)
        title_entry.insert(0, self.plot_title)
        title_entry.grid(column=0, row=0, columnspan=2)

        cancel_button = Button(title_root, text="Cancel", command=lambda: title_root.destroy())
        cancel_button.grid(column=0, row=1)

        ok_button = Button(title_root, text="OK", state='disabled', command=ok_clicked)
        ok_button.grid(column=1, row=1)

        title_root.bind('<Return>', ok_clicked_event)
        title_root.resizable(False, False)
        title_root.mainloop()

    # COMPLETE
    def change_fonts(self):

        def font_changer(new_font='Arial'):
            self.r.config(font=self.result_value_font.config(family=new_font))
            self.m.config(font=self.result_value_font.config(family=new_font))
            self.c.config(font=self.result_value_font.config(family=new_font))
            self.best_fit.config(font=self.result_font.config(family=new_font))
            self.correlation.config(font=self.result_font.config(family=new_font))
            self.enable_grid_lines.config(font=self.button_font.config(family=new_font))
            self.enable_custom_headers.config(font=self.button_font.config(family=new_font))
            self.title.config(font=font.Font(family=new_font, size=20))
            self.custom_header_label.config(font=self.label_font.config(family=new_font, size=18))
            self.x_label.config(font=self.label_font.config(family=new_font))
            self.y_label.config(font=self.label_font.config(family=new_font))
            self.matplotlib_font.set_name(new_font)
            self.graph_line(self.graph_canvas, self.sub_plot, self.grid_lines.get())

        def double_click_font(event):
            try:
                new_font = font_listbox.selection_get()
                font_changer(new_font)
                self.global_font.set(new_font)
                font_root.destroy()
            except Exception:
                font_changer()
                font_root.destroy()

        def single_click_font(event):
            new_font = font_listbox.selection_get()
            font_changer(new_font)
            ok_button['state'] = 'normal'

        def ok_clicked():
            self.global_font.set(font_listbox.selection_get())
            font_root.destroy()

        def cancel():
            font_changer(self.global_font.get())
            font_root.destroy()

        font_root = Tk()
        font_root.title('Fonts')
        fonts = list(font.families())
        fonts.sort()
        # Eliminates all fonts which are not compatible with matplotlib
        fonts = [f for f in sorted(set([f.name for f in font_manager.fontManager.ttflist])) if f in fonts]
        font_frame = ScrollFrame(font_root, width=40, height=20)

        font_listbox = Listbox(font_frame, width=40, height=20, exportselection=True)
        font_listbox.select_set(fonts.index('Arial'))
        font_listbox.bind("<Double-1>", double_click_font)
        font_listbox.bind("<ButtonRelease-1>", single_click_font)
        font_listbox.pack(side='top', fill='both', expand=True)

        font_frame.grid(columnspan=2)

        # Removed all fonts which cause missing character or are not compatible with the window size
        invalid_fonts = ['wingdings', 'airplanes in the night sky', 'applegothic', 'applemyungjo', 'bodoni ornaments',
                         'djb jacked up kinda luv', 'diwan thuluth', 'farisi', 'janda curlygirl', 'janda happy day',
                         'khmer sangam mn', 'kokonor', 'noto sans javanese', 'stix', 'trattatello', 'webdings',
                         'zapfino', '{hazel grace}', 'anyk', 'lao sangam mn', 'mishafi', 'wizards magic', 'arial black',
                         'apple chancery', 'curlystars', 'din condensed', 'gurmukhi', 'krungthep', 'one starry',
                         'apple symbols', 'arial narrow', 'betty', 'brush script mt', 'chalkduster', 'curlyshirley',
                         'din alternate', 'dk jambo', 'pretty girls script demo', 'silom', 'skia', 'spinnenkop demo',
                         'symbol', 'give me some sugar']
        for item in fonts:
            if any(invalid_font in item.lower() for invalid_font in invalid_fonts):
                pass
            else:
                font_listbox.insert('end', item)

        cancel_button = Button(font_root, text="Cancel", command=cancel)
        cancel_button.grid(column=0, row=1)

        ok_button = Button(font_root, text="OK", state='disabled', command=ok_clicked)
        ok_button.grid(column=1, row=1)

        font_root.bind('<Return>', double_click_font)
        font_root.resizable(False, False)
        font_root.mainloop()

    # COMPLETE
    def save_fig(self):
        if self.graphing():
            f = filedialog.asksaveasfile(mode="w", defaultextension=".png",
                                         title="Save an image of your plot", parent=self.root)
            if f is not None:
                self.graph_figure.savefig(f.name)
        else:
            messagebox.showwarning(message="Please complete the data points "
                                           "before trying to save an image of the graph.")

    # INCOMPLETE
    '''def save_results(self):
        img = Image.new('RGB', (390, 300), color=(255, 255, 255))
        drawer = ImageDraw.Draw(img)
        font_name = self.global_font.get()
        drawer_font = ImageFont.truetype(font=font_name)
        drawer.text((10, 10), "Best Fit Values", fill=(0, 0, 0), font=drawer_font, size=20)
        f = filedialog.asksaveasfile(mode="w", defaultextension=".png",
                                     title="Save an image of your plot results", parent=self.root)
        img.save(f.name)'''

    # COMPLETE
    def save_graph_data(self, file_type):
        def write_data(x_values, y_values, headers=False):
            text = ""
            if headers:
                text = f"{self.x_entry_label_var.get()},{self.y_entry_label_var.get()}\n"

            x_value = iter(x_values)
            y_value = iter(y_values)
            for i in range(len(x_values) if len(x_values) >= len(y_values) else len(y_values)):
                try:
                    text += str(next(x_value)) + ","
                except StopIteration:
                    text += ","
                try:
                    text += str(next(y_value)) + '\n'
                except StopIteration:
                    text += '\n'

            return text

        # TODO Fix the following:
        #  Stills saves the data points if the user enters more than 2 rows and then deletes the rows
        # x_points, y_points = self.graphing(graphing_check=False)
        x, y = add_to_xy(self.inputs)
        number_of_x_rows = len(x.keys())
        number_of_y_rows = len(y.keys())
        x_points = self.row_sorter(x, number_of_x_rows)
        y_points = self.row_sorter(y, number_of_y_rows)
        x, y = np.array(x_points, dtype=float), np.array(y_points, dtype=float)

        if len(x) >= 2 and len(y) >= 2:
            if file_type == 'txt':
                f = filedialog.asksaveasfile(mode='w', defaultextension=".txt", title="Save as plain text file",
                                             initialfile="Graph Data Points", parent=self.root)
            else:
                f = filedialog.asksaveasfile(mode='w', defaultextension=".csv", title="Save as CSV",
                                             initialfile="Graph Data Points", parent=self.root)
            if f is None:
                return
            elif self.custom_headers_currently_enabled:
                f.write(write_data(x, y, headers=True))
            else:
                f.write(write_data(x, y))
                f.close()
        else:
            messagebox.showwarning(message="There are too few data points to save.")

    # COMPLETE
    def custom_plot_labels(self, event):
        self.graphing()
        self.enable_grid_lines.invoke()
        self.enable_grid_lines.invoke()

    # COMPLETE
    def handle_custom_headers(self, event):
        """
        Reacts to when the custom header entry field is entered by the user
        :param event: FocusIn event
        :return: None
        """
        name = str(event.widget).split(".")[-1]
        if name == '!entry':
            if not self.already_clicked_x:
                self.x_entry_label.delete('0', 'end')
                self.already_clicked_x = True

            self.x_entry_label.bind('<FocusOut>', self.custom_plot_labels)
        elif name == '!entry2':
            if not self.already_clicked_y:
                self.y_entry_label.delete('0', 'end')
                self.already_clicked_y = True

            self.y_entry_label.bind('<FocusOut>', self.custom_plot_labels)

    # COMPLETE
    def custom_headers_button(self):
        """
        Handles whether the custom headers frame will show or not
        :return: None
        """

        # Checks whether the custom headers checkbox has been checked
        if self.custom_headers.get():
            self.input_labels.pack(before=self.input_area, anchor='w', padx=(0, 3), pady=(2, 2))
            self.custom_header_frame.pack(before=self.input_labels, anchor='w', padx=(0, 3), pady=(2, 2))
            self.custom_headers_currently_enabled = True
            self.root.update_idletasks()
        else:
            # Removes the custom headers and labels from the window
            self.custom_header_frame.forget()
            # Resets the graph labels
            self.x_entry_label_var.set('X')
            self.y_entry_label_var.set('Y')
            # Using .graphing() in case the user has not completed all of the data points
            self.graphing()
            self.enable_grid_lines.invoke()  # TODO Fix lag when disabling custom headers
            self.enable_grid_lines.invoke()
            # Sets the size of the input area to a comfortable 392 pixels
            self.input_area.canvas.config(height=392)
            # Places the input labels a good distance below the top bar in the window
            self.input_labels.pack(before=self.input_area, anchor='w', padx=(0, 3), pady=(2, 2))
            self.custom_headers_currently_enabled = False
            self.already_clicked_x = False
            self.already_clicked_y = False
            self.root.update_idletasks()

    # COMPLETE @ Before check
    def grid_lines_button(self):
        if self.inputs:
            # Attempts to prevent the application freezing when the user tries
            # to disable/enable the grid lines while one or more data points are incomplete
            try:
                x, y = add_to_xy(self.inputs)
                x = sorted(x.items(), key=lambda l: int(l[0][1:]))
                y = sorted(y.items(), key=lambda l: int(l[0][1:]))
                if x[-1][0][1:] == y[-1][0][1:]:
                    self.graph_line(self.graph_canvas, self.sub_plot, self.grid_lines.get())
                else:
                    # TODO Decide whether this is the best way to go about the error
                    messagebox.showwarning(message="Please complete the remaining x- and y- data points.")
                    self.enable_grid_lines.deselect()
            except IndexError:
                pass
        else:
            self.graph_line(self.graph_canvas, self.sub_plot, self.grid_lines.get())

    # COMPLETE @ Before check
    def graph_line(self, canvas, ax, gridlines, passed_by_graphing=None):
        """
        Graphs the canvas either with the data points or just the grid
        :param passed_by_graphing:
        :param canvas: Graph canvas (tkinter.Canvas)
        :param ax: Graph axes (tkinter.figure.Figure)
        :param gridlines: Boolean (whether gridlines are active, False=On, True=Off)
        :return: None
        """
        ax.clear()
        clean_x_text = self.x_entry_label_var.get().replace(" ", "\/")
        clean_y_text = self.y_entry_label_var.get().replace(" ", "\/")
        plot_title = self.plot_title.replace(" ", "\/")
        ax.set_xlabel(r"$\mathregular{" + clean_x_text + "}$", fontproperties=self.matplotlib_font)
        ax.set_ylabel(r"$\mathregular{" + clean_y_text + "}$", fontproperties=self.matplotlib_font)
        ax.set_title(r'$\mathregular{' + plot_title + '}$', fontproperties=self.matplotlib_font, fontsize=14)

        if self.ready_to_plot:
            if passed_by_graphing:
                x_points, y_points = passed_by_graphing[0], passed_by_graphing[1]
            else:
                x_points, y_points = self.graphing(graphing_check=False)

            if '' in x_points and '' in y_points and not (self.shown_y or self.shown_x):
                messagebox.showwarning(message="Please complete both columns of data points.")
                self.shown_x = True
                self.shown_y = True
            elif '' in x_points and not self.shown_x:
                message = f"Please complete the x data point in row {x_points.index('') + 1}"
                occurrences = [i for i, n in enumerate(x_points) if n == '']
                if len(occurrences) == 2:
                    message += f" and in row {[i for i, n in enumerate(x_points) if n == ''][1] + 1}."
                elif len(occurrences) > 2:
                    occurrences = [i for i, n in enumerate(x_points) if n == ''][1:]
                    for i in range(len(occurrences[:-1])):
                        message += f", row {occurrences[i] + 1}"

                    message += f", and row {occurrences[-1] + 1}."

                messagebox.showwarning(message=message)
                self.shown_x = True
            elif '' in y_points and not self.shown_y:
                message = f"Please complete the y data point in row {y_points.index('') + 1}"
                if y_points.count('') == 2:
                    message += f" and in row {[i for i, n in enumerate(y_points) if n == ''][1] + 1}."
                elif y_points.count('') > 2:
                    occurrences = [i for i, n in enumerate(y_points) if n == ''][1:]
                    for i in range(len(occurrences[:-1])):
                        message += f", row {occurrences[i] + 1}"

                    message += f", and row {occurrences[-1] + 1}."

                messagebox.showwarning(message=message)
                self.shown_y = True
            else:
                try:
                    x, y = np.array(x_points, dtype=float), np.array(y_points, dtype=float)
                except ValueError:
                    pass
                else:
                    m, c, r = get_graph_data(x, y, initial=False, sigfigs=self.number_of_sigfigs)
                    self.m_var.set(m), self.c_var.set(c), self.r_var.set(r)

                    line = self.give_me_a_straight_line_without_polyfit(x, y)

                    if not gridlines:
                        ax.grid(which='major', color='#999999', linestyle='-')
                        ax.minorticks_on()
                        ax.grid(which='minor', color='#999999', linestyle='-', alpha=0.2)

                    if any(number for number in x if number < 0):
                        ax.axvline(x=0, color='k')

                    if any(number for number in y if number < 0):
                        ax.axhline(y=0, color='k')

                    ax.plot(x, y, 'yo', marker='x', mec='black', markersize=8)
                    ax.plot(x, line, color='blue')
                    self.shown_x = False
                    self.shown_y = False

        elif not gridlines:
            ax.grid(which='major', color='#999999', linestyle='-')
            ax.minorticks_on()
            ax.grid(which='minor', color='#999999', linestyle='-', alpha=0.2)

        canvas.draw()

    # COMPLETE @ Before check
    def give_me_a_straight_line_without_polyfit(self, x, y):
        # first augment the x vector with np.ones
        ones_vec = np.ones(x.shape)
        x_value = np.vstack([x, ones_vec]).T  # .T as we want two columns
        # now plugin our least squares "solution"
        xx = np.linalg.inv(np.dot(x_value.T, x_value))
        xt_y = np.dot(x_value.T, y.T)  # y.T as we want column vector
        beta = np.dot(xx, xt_y)

        line = beta[0] * x + beta[1]
        return line

    # COMPLETE @ Before check
    def row_sorter(self, column, number_of_rows):
        """
        Sorts the given column of data points by the grid/row coordinate it belongs to
        :param number_of_rows: self-explanatory
        :param column: the dictionary of data point values for either x or y
        :return: the sorted column of values
        """

        values, row = [], 0
        while True:
            for k, v in column.items():
                if len(values) == number_of_rows:
                    break
                elif str(row) in k:
                    values.append(v)
                    row += 1

            if len(values) == number_of_rows:
                return values

    def graph_highest_row(self, highest_row):
        x, y = add_to_xy(self.inputs)
        # Sorts the x and y inputs by row number
        x = sorted(x.items(), key=lambda l: int(l[0][1:]))
        y = sorted(y.items(), key=lambda l: int(l[0][1:]))
        x_values, y_values = [], []
        for x_item in x:
            if int(x_item[0][1]) <= int(highest_row[1:]):
                x_values.append(x_item[1])

        for y_item in y:
            if int(y_item[0][1]) <= int(highest_row[1:]):
                y_values.append(y_item[1])

        return x_values, y_values

    # COMPLETE @ Before check
    def graphing(self, graphing_check=True):
        """
        If graphing_check is true, the function will check whether it is okay to graph the data points.
        If graphing_check is false, the function will sort the x-values and the y-values into their correct order
            (i.e. x0 will be "paired" with y0, and so on for all values)
        :param graphing_check: Boolean (default of True)
        :return: Boolean (if graphing check) or sorted x-values and y-values (if not graphing check)
        """
        x, y = add_to_xy(self.inputs)
        if graphing_check:
            entry_labels = [[], []]
            for kx in x.keys():
                entry_labels[0].append(kx[1:])

            for ky in y.keys():
                entry_labels[1].append(ky[1:])

            entry_labels[0] = sorted(entry_labels[0], key=lambda l: int(l))
            entry_labels[1] = sorted(entry_labels[1], key=lambda l: int(l))

            try:
                # If this fails, try and find the lowest complete row and return it
                last_x_entry_label = entry_labels[0][-1]
                if last_x_entry_label == entry_labels[1][-1]:
                    x = sorted(x.items(), key=lambda l: int(l[0][1:]))
                    y = sorted(y.items(), key=lambda l: int(l[0][1:]))
                    x_values, x_rows, y_values, y_rows = [], [], [], []
                    y_iter = iter(y)
                    for x_item in x:
                        if int(x_item[0][1:]) <= int(last_x_entry_label):
                            x_rows.append(x_item[0][1:])
                            try:
                                y_rows.append(next(y_iter)[0][1:])
                            except StopIteration:
                                return False

                    if x_rows == y_rows and x_rows == [str(i) for i in range(0, int(x_rows[-1]) + 1)] \
                            and y_rows == [str(i) for i in range(0, int(y_rows[-1]) + 1)]:
                        return True
                    else:
                        return False
                else:
                    lowest_row = ''
                    for x_val in reversed(entry_labels[0]):
                        for y_val in reversed(entry_labels[1]):
                            if y_val == x_val and int(y_val) >= 1:
                                lowest_row = f'x{x_val}'
                                break

                        if lowest_row:
                            break
                    if lowest_row:
                        x = sorted(x.items(), key=lambda l: int(l[0][1:]))
                        y = sorted(y.items(), key=lambda l: int(l[0][1:]))
                        x_values, x_rows, y_values, y_rows = [], [], [], []
                        for x_item in x:
                            if int(x_item[0][1:]) <= int(lowest_row[1:]):
                                x_values.append(x_item[1])
                                x_rows.append(x_item[0][1:])

                        for y_item in y:
                            if int(y_item[0][1:]) <= int(lowest_row[1:]):
                                y_values.append(y_item[1])
                                y_rows.append(y_item[0][1:])

                        if x_rows == y_rows and x_rows == [str(i) for i in range(0, int(x_rows[-1]) + 1)] \
                                and y_rows == [str(i) for i in range(0, int(y_rows[-1]) + 1)]:
                            self.ready_to_plot = True
                            self.graph_line(self.graph_canvas, self.sub_plot, self.grid_lines.get(),
                                            passed_by_graphing=[x_values, y_values])
                        else:
                            return False
                    return False
            except IndexError:
                return False
        else:
            number_of_rows = len(x.keys())
            x_values = self.row_sorter(x, number_of_rows)
            y_values = self.row_sorter(y, number_of_rows)
            return x_values, y_values


class ScrollFrame(Frame):
    def __init__(self, parent, width=None, height=None):
        super().__init__(parent)

        if width and height:
            self.canvas = Canvas(self, width=width, height=height, highlightthickness=0, background="#ffffff")
        elif width:
            self.canvas = Canvas(self, width=width, highlightthickness=0, background="#ffffff")
        elif height:
            self.canvas = Canvas(self, height=height, highlightthickness=0, background="#ffffff")
        else:
            self.canvas = Canvas(self, highlightthickness=0, background="#ffffff")

        self.viewPort = Frame(self.canvas, background="#ffffff")
        self.vsb = Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)

        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas_window = self.canvas.create_window((4, 4), window=self.viewPort, anchor="nw", tags="self.viewPort")

        self.viewPort.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind("<Configure>", self.on_canvas_configure)

        # Allows the scroll wheel to be used on the scrollbar
        # TODO Allow the mouse to be anywhere inside the canvas to allow scrolling
        self.canvas.bind('<MouseWheel>', lambda event: self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units"))

        self.on_frame_configure(None)

    def on_frame_configure(self, event):
        """
        Reset the scroll region to encompass the inner frame
        :param event:
        :return: None
        """
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_canvas_configure(self, event):
        """
        Reset the canvas window to encompass inner frame when required
        :param event:
        :return: None
        """
        canvas_width = event.width
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)


if __name__ == '__main__':
    Main()

    '''xs = np.array([0.450, 0.813, 1.32, 1.877, 2.377, 2.887, 3.427, 4.010])
    ys = np.array([0.023, 0.046, 0.069, 0.092, 0.115, 0.138, 0.161, 0.184])'''
