import os
from os import path
import sys
from multiprocessing import Process, Queue
from threading import Thread
import datetime

import yaml
from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import *

#Own modules
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),".."))
from Spectrum_Processing.SPeDE import SPeDE_wrapper
DEVELOP=True

def main():
    app = QApplication(sys.argv)
    home = Homescreen()
    home.show()

    sys.exit(app.exec_())

class Homescreen(QWidget):
    """Main window of the GSPeDE application."""

    def __init__(self):
        super().__init__()

        # initialize value fields
        self.intervals_input = None
        self.output_directory_input= None
        self.project_directory_input=None
        self.density_input = None
        self.cluster_input = None
        self.cutoff_input = None
        self.local_input = None
        self.i_picker=None
        self.proj_picker=None
        self.folder_out_picker=None
        self.output_group= None
        self.start_button= None
        self.def_button= None
        self.val_button= None
        self.cop_button=None
        self.txt_rb=None
        self.csv_rb=None
        self.krona_button=None
        self.spectrum_process= None
        self.spectrum_process_args= None
        self.process_args= None
        self.waiter= None
        self.affix=None

        #Output files
        self.out_name="SPeDE_output"
        self.out_validation_name="data_validation.csv"
        self.out_krona_name="krona_output.txt"

        #Gui Config
        self.default_value_filename="default_config.yaml"
        self.input_disabled_state={}

        #default peak value of internal SPeDE program
        self.default_peaks=5


        #self.setFixedSize(600, 400)
        self.resize(850,400)
        self.setWindowTitle("SPeDE: Spectral Dereplication")
        self.setWindowIcon(QIcon(path.join(path.dirname(path.abspath(__file__)),"Media/Ghent_University_Temple")))
        self.center()
        self.fill_body()
        self.init_sub_windows()
        self.init_values()

    #prepare all subwindows for future use
    def init_sub_windows(self):
        """Initialize all child windows of the Homescreen class.

        :return: void
        """
        self.waiter=WaitWindow(self.kill_process, lambda: self.enable_input(True))
        self.waiter.ok_button.clicked.connect(lambda: self.start_button.setEnabled(True))
        self.waiter.ok_button.clicked.connect(self.waiter.reset_text)

    def init_values(self):
        """Initialize default values and inputs of the Homescreen class.

        :return: void
        """
        self.enable_param_input(False)
        self.handle_load_config(True)
        self.affix=datetime.datetime.today().strftime("%Y_%m_%d_%H_%M_%S_")

    # Set all buttons needed on the main view of the program
    def fill_body(self):
        """Make the body of the Homescreen class.

        :return: void
        """

        # Make a grid structure
        main_layout = QVBoxLayout()

        # fill top part with required parameters
        self.fill_upper_body(main_layout)

        # fill bottom part with optional parameters + start/stop buttons
        self.fill_bottom_body(main_layout)

    def fill_upper_body(self, main_layout):
        """Fill the upper body of the Homescreen class.

        :param main_layout: A container for all GUI elements
        :type main_layout: QVBoxLayout
        :return: void
        """

        #labels

        reserved_label = QLabel("Reserved text")
        folder_out_label=QLabel("Output directory")
        folder_out_label.setMinimumWidth(100)
        proj_label=QLabel("Project directory")
        proj_label.setMinimumWidth(100)


        #input fields
        self.project_directory_input=QLineEdit()
        self.output_directory_input=QLineEdit()


        #picker buttons
        self.proj_picker = QPushButton("...")
        self.proj_picker.clicked.connect(lambda: self.handle_dir_pick(self.project_directory_input))
        self.proj_picker.setMaximumWidth(50)

        self.folder_out_picker = QPushButton("...")
        self.folder_out_picker.clicked.connect(lambda: self.handle_dir_pick(self.output_directory_input))
        self.folder_out_picker.setMaximumWidth(50)

        #output buttons
        self.csv_rb = QRadioButton("csv")
        self.txt_rb = QRadioButton("txt")
        self.csv_rb.setChecked(True)

        #couples

        proj_box = QHBoxLayout()
        proj_box.addWidget(proj_label)
        proj_box.addWidget(self.project_directory_input)
        proj_box.addWidget(self.proj_picker)

        folder_out_box= QHBoxLayout()
        folder_out_box.addWidget(folder_out_label)
        folder_out_box.addWidget(self.output_directory_input)
        folder_out_box.addWidget(self.folder_out_picker)


        ##button group

        self.output_group = QVBoxLayout()

        self.output_group.addWidget( self.csv_rb, alignment=QtCore.Qt.AlignCenter)
        self.output_group.addWidget(self.txt_rb, alignment=QtCore.Qt.AlignCenter)

        output_box = QGroupBox("Output type")
        output_box.setMinimumWidth(125)
        output_box.setLayout(self.output_group)


        #Boxes

        ##top-explanation box
        explanation_box = QHBoxLayout()  # add some explanation text at the upper left part of the screen
        explanation_box.addWidget(reserved_label, alignment=QtCore.Qt.AlignLeft)

        ##top-left box
        tl_box = QVBoxLayout()
        tl_box.addLayout(explanation_box)
        tl_box.addStretch(0.4)
        tl_box.addLayout(proj_box)
        tl_box.addStretch(0.5)
        tl_box.addLayout(folder_out_box)
        tl_box.addStretch(0.3)

        # top right output box
        tr_box = QVBoxLayout()
        tr_box.addWidget(output_box)

        ##add all to upper box
        upper_box = QHBoxLayout()
        upper_box.addLayout(tl_box)
        upper_box.addLayout(tr_box)

        # add to main layout
        main_layout.addLayout(upper_box)

    def fill_bottom_body(self, main_layout):
        """Fill the bottom body of the Homescreen class.

        :param main_layout: A container for all GUI elements
        :type main_layout: QVBoxLayout
        :return: void
        """

        # Labels
        d_label = QLabel("Density")
        d_label.setMinimumWidth(70)
        cl_label = QLabel("Cluster (%)")
        cl_label.setMinimumWidth(70)
        l_label = QLabel("Local (%)")
        l_label.setMinimumWidth(70)
        cu_label = QLabel("Cutoff (M/Z)")
        cu_label.setMinimumWidth(70)
        def_label=QLabel("Default values")
        def_label.setMinimumWidth(140)
        val_label=QLabel("Validation matrix")
        val_label.setMinimumWidth(140)
        cop_label=QLabel("Copy unique references")
        cop_label.setMinimumWidth(140)
        krona_label=QLabel("Krona output")
        krona_label.setMinimumWidth(140)
        i_label = QLabel("Intervals")
        i_label.setMinimumWidth(70)



        # Input fields
        self.intervals_input = QLineEdit()
        self.density_input = QLineEdit()
        self.cluster_input = QLineEdit()
        self.local_input = QLineEdit()
        self.cutoff_input = QLineEdit()


        # Buttons/checkboxes
        self.start_button = QPushButton('Start', self)
        self.start_button.resize(self.start_button.sizeHint())
        self.start_button.clicked.connect(self.handle_start_processing)  # connect the exit button to the start event
        self.start_button.clicked.connect(lambda: self.enable_input(False))
        exit_button = QPushButton('Exit', self)
        exit_button.resize(exit_button.sizeHint())
        exit_button.clicked.connect(QApplication.instance().closeAllWindows)  # connect the exit button to an exit event
        config_load_button=QPushButton("Load config")
        config_load_button.resize(config_load_button.sizeHint())
        config_load_button.clicked.connect(self.handle_load_config)
        config_store_button=QPushButton('Store config')
        config_store_button.resize(config_store_button.sizeHint())
        config_store_button.clicked.connect(self.handle_store_config)

        self.def_button= QCheckBox()
        self.def_button.setChecked(True)
        self.def_button.stateChanged.connect(self.handle_def_val_change)
        self.val_button=QCheckBox()
        self.val_button.setChecked(False)
        self.cop_button=QCheckBox()
        self.cop_button.setChecked(True)
        self.krona_button=QCheckBox()
        self.krona_button.setChecked(True)


        self.i_picker = QPushButton("...")
        self.i_picker.clicked.connect(lambda: self.handle_file_pick(self.intervals_input))
        self.i_picker.setMaximumWidth(50)

        ##couples
        d_box = QHBoxLayout()  # density
        d_box.addWidget(d_label)
        d_box.addWidget(self.density_input)
        cl_box = QHBoxLayout()  # cluster
        cl_box.addWidget(cl_label)
        cl_box.addWidget(self.cluster_input)
        l_box = QHBoxLayout()  # local
        l_box.addWidget(l_label)
        l_box.addWidget(self.local_input)
        cu_box = QHBoxLayout()  # cutoff
        cu_box.addWidget(cu_label)
        cu_box.addWidget(self.cutoff_input)
        defb_box=QHBoxLayout()
        defb_box.addWidget(def_label)
        defb_box.addWidget(self.def_button)
        valb_box=QHBoxLayout()
        valb_box.addWidget(val_label)
        valb_box.addWidget(self.val_button)
        copb_box=QHBoxLayout()
        copb_box.addWidget(cop_label)
        copb_box.addWidget(self.cop_button)
        kronab_box=QHBoxLayout()
        kronab_box.addWidget(krona_label)
        kronab_box.addWidget(self.krona_button)
        i_box = QHBoxLayout()
        i_box.addWidget(i_label)
        i_box.addWidget(self.intervals_input)
        i_box.addWidget(self.i_picker)

        ## Make vertical groupings

        ### Bottom input left
        bil_box = QVBoxLayout()
        bil_box.addLayout(d_box)
        bil_box.addLayout(cl_box)

        ## Bottom input right
        bir_box = QVBoxLayout()
        bir_box.addLayout(l_box)
        bir_box.addLayout(cu_box)

        ## Config buttons
        conf_buttons=QVBoxLayout()
        conf_buttons.addWidget(config_load_button)
        conf_buttons.addWidget(config_store_button)

        ## Process buttons
        proc_buttons = QVBoxLayout()
        proc_buttons.addWidget(self.start_button)
        proc_buttons.addWidget(exit_button)


        ## Check buttons right
        check_buttons=QVBoxLayout()
        check_buttons.addLayout(valb_box)
        check_buttons.addLayout(copb_box)
        check_buttons.addLayout(defb_box)
        check_buttons.addLayout(kronab_box)


        #Default parameters

        ## Default values
        def_value_container=QHBoxLayout()
        def_value_container.addLayout(bil_box)
        def_value_container.addLayout(bir_box)

        ## (Intervals: i_box)

        param_container=QVBoxLayout()
        param_container.addLayout(def_value_container)
        param_container.addLayout(i_box)


        #Add to main container
        bottom_container = QHBoxLayout()
        bottom_container.addLayout(conf_buttons)
        bottom_container.addLayout(param_container)
        bottom_container.addLayout(proc_buttons)
        bottom_container.addLayout(check_buttons)

        # Add the bottom grid to main layout
        main_layout.addLayout(bottom_container)

        # Set the main layout
        self.setLayout(main_layout)


    # Event handling

    # Intercept the normal close event and ask for confirmation
    def closeEvent(self, QCloseEvent):
        """Handle a close event.

        Any leftover processes must be killed and cleaned before exiting the program.

        :param QCloseEvent: A QCloseEvent to be handled
        :type QCloseEvent: QCloseEvent
        :return:
        """
        warning = QMessageBox.question(self, "Warning", "Are you sure you want to exit?", QMessageBox.Yes | QMessageBox.No)

        if warning == QMessageBox.Yes:
            QCloseEvent.accept()

            #Clean any leftover processes and windows
            self.waiter.close()
            self.clean_subprocess(kill=True)
        else:
            QCloseEvent.ignore()

    def handle_start_processing(self):
        """Start processing the spectra.

        This function must gather all config parameters of the GUI and present them to the SPeDE main function.
        Parameter validation must happen here and any error must be handled accordingly. A Waiter Window must be called
        to present to the user while processing is happening. The start button of the Homescreen window must be disabled
        while processing to avoid duplicate work.

        :return: void
        """


        #Get all input parameters
        params=self.get_config_params().values()
        intervals, projdir, output_directory, density, cluster, local, cutoff, validation, output_format, copy, krona =params


        # Validate input

        ## Check not empty
        if not self.all_exist(params):
            message = QMessageBox.critical(self, "Warning", "Not all values are filled in.", QMessageBox.Ok)
            self.start_button.setEnabled(True)
            return


        ## Validate paths
        for param in [intervals,projdir,output_directory]:
            try:
              self.validate_path(param)

            except AssertionError:
                message = QMessageBox.critical(self, "Warning", "{0} is not a valid path".format(param), QMessageBox.Ok)
                self.start_button.setEnabled(True)
                return


        ## Validate values
        for x in [density, cluster, local, cutoff]:
            try:
                self.validate_and_parse_integer(x)
            except Exception:
                message = QMessageBox.critical(self, "Warning","{0} is not a valid number".format(x), QMessageBox.Ok)
                self.start_button.setEnabled(True)
                return

        #if all goes well

        self.start_button.setEnabled(False)
        qApp.processEvents()
        self.waiter.show()

        thread= Thread(target=self.process_spectra, args=(intervals,projdir,output_directory, density,cluster,local,cutoff,output_format,validation,copy, krona))
        thread.start()

    # Pass arguments to processing module and start spectrum analysis
    def process_spectra(self, intervals, projdir, output_directory, density, cluster, local, cutoff, output_format, validation, copy, krona):
        """Process the spectra in a worker thread.

        All parameters are expected to be valid and sane. Any error arising from the called process should be handled here.
        Clean the process after finishing.

        :param intervals: Path to the intervals file.
        :type intervals: str
        :param projdir: Path to the project directory.
        :type projdir: str
        :param output_directory: Path to the output directory.
        :type output_directory: str
        :param density: The PPM threshold.
        :type density: int
        :param cluster: The PPVM cluster threshold in percentage.
        :type cluster: int
        :param local: The PPMC local threshold in percentage.
        :type local: int
        :param cutoff: The S/N cutoff in M/Z.
        :type cutoff: int
        :param output_format: Output format of the spectra.
        :type output_format: str
        :param validation: Print the validation matrix.
        :type validation: bool
        :param copy: True if you want to copy the unique references to a subfolder.
        :type copy: bool
        :param krona: True if you want to generate a ready-to-go krona output file.
        :type krona: bool
        :return: void
        """

        arguments={"intervals": intervals, "project_directory": projdir, "output_directory": output_directory,
                   "density": density, "cluster":cluster, "local":local, "cutoff": cutoff, "output_format": output_format,
                   "validate": validation, "name": self.out_name, "validation_name": self.out_validation_name,
                   "peaks": self.default_peaks, "affix": self.affix, "copy": copy, "krona": krona}

        args=(intervals,projdir, output_directory, self.default_peaks, density, local,cutoff, validation, self.out_validation_name, cluster, self.out_name, output_format, copy, krona, self.affix)

        self.process_args=arguments

        print(arguments)
        argdict={}

        err_queue=Queue()
        argdict["queue"]=err_queue
        argdict["args"]=args
        self.spectrum_process = Process(target=SPeDE_wrapper, args=(argdict,))
        self.spectrum_process.start()
        self.spectrum_process.join()

        if self.spectrum_process is not None:
            if not err_queue.empty(): #an error occurred
                error= err_queue.get()
                message=self.handle_error(error)
                handler=ProcessedEvent(lambda: self.handle_process_finished(error=True, message=message))
            else:
                handler=ProcessedEvent(self.handle_process_finished)

            handler.handle_signal()
            self.clean_subprocess()

    #Start a file picker
    def handle_file_pick(self, input_field):
        """Initialize a file picker, set the result in `input_field.`

        :param input_field: The field in which the picked file-name must be placed.
        :type input_field: QLineEdit
        :return: void
        """
        file = QFileDialog.getOpenFileName(self, "Select file")[0]
        input_field.setText(file)

    #Start a directory picker
    def handle_dir_pick(self, input_field):
        """Initialize a directory picker, set the result in `input_field.`

        :param input_field: The field in which the picked directory-name must be placed.
        :type input_field: QLineEdit
        :return: void
        """
        file = QFileDialog.getExistingDirectory(self, "Select Directory")
        input_field.setText(file)

    ##processing finished
    def handle_process_finished(self, killed=False, error=False, message=None):
        """Handle the finishing of the spectrum processing process.

        This handler must be called when the process is done processing the spectra. Depending on the outcome of the
        process, set a message in the Waiter window. The message to be set is decided on by the passed parameters.

        :param killed: True if the process was killed abruptly.
        :type killed: bool
        :param error: True if an error occurred while processing.
        :type error: bool
        :param message: An additional message to be set in the Waiter window
        :type message: str
        :return: void
        """
        text=""
        if killed: #abrupt ending of processing
            text+="Processing aborted."
        elif error:
            text+="An error occured:\n"
            text+=message
        else: #processing finished normally
            text+="Data processing finished.\n"
            text+="Output written to \n{2}{0}.{1}\n".format(self.out_name, self.get_output_extension(),self.affix)
            if self.val_button.isChecked():
                text+= "Validation matrix written to \n{0}{1}\n".format(self.affix, self.out_validation_name)
            if self.cop_button.isChecked():
                text+= "Unique references copied to subfolder\n{0}References\n".format(self.affix)
            if self.krona_button.isChecked():
                text+="Krona output written to \n{0}{1}\n".format(self.affix,self.out_krona_name)


        #Let the window jump back to the front #todo: bad code
        self.waiter.to_front()
        self.waiter.set_ok_button(True)

        self.waiter.set_text(text)

    def handle_def_val_change(self):
        """Disable or enable parameter input.

        :return: void
        """
        if self.def_button.isChecked():
            self.enable_param_input(False)
            self.handle_load_config(True)
        else:
            self.enable_param_input(True)

    def handle_load_config(self, load_default):
        """Handle how the loading of a .yaml configuration file should happen.

        Values are assumed to not throw errors when read or put into their respective fields.

        :param load_default: True if the default configuration file should be loaded.
        :type load_default: bool
        :return: void
        """

        if not load_default:
            filename = QFileDialog.getOpenFileName(self, "Select file",filter="*.yaml")[0]
            self.val_button.setChecked(False)
        else:
            if DEVELOP:
                filename= os.path.join(os.path.dirname(os.path.abspath(__file__)), "default_config_develop.yaml")
            else:
                if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), self.default_value_filename)):
                    filename= os.path.join(os.path.dirname(os.path.abspath(__file__)), self.default_value_filename)
                else:
                    filename=""

        #if nothing was chosen: exit
        if filename=="":
            return

        try:
            output=open(filename,"r")
        except IOError:
            warning = QMessageBox.critical(self, "Error", "File {0} unavailable.".format(filename), QMessageBox.Ok)
            return

        params=yaml.load(output)
        output.close()

        if params is None:
            return


        #make dictionary mapping names to items
        func_dict = {"intervals": self.set_intervals, "project_directory": self.set_proj_dir,
                     "density": self.set_density, "cluster": self.set_cluster, "local": self.set_local,
                     "cutoff": self.set_cutoff, "output_directory": self.set_output_directory}

        #set all parameters
        for k,v in params.items():
            func_dict[k](v)

    def handle_store_config(self):
        """Handle the storing of parameters in a configuration .yaml file.

        Semantically wrong values can be stored into a configuration file only after confirming with the user. Values
        shoud still be syntactically correct as they shouldn't produce error when being loaded. Empty field can't be
        stored in the configuration file. Otherwise, values could be accidentally overridden when these are loaded.

        :return: void
        """

        param_dict= self.get_config_params()
        param_dict.pop("validation")
        param_dict.pop("output_type")
        param_dict.pop("copy")
        param_dict.pop("krona")
        params=param_dict.values()
        intervals, projdir, output_directory, density, cluster, local, cutoff=param_dict.values()

        print_anyway=False

        # Validate input
        ##Validate not empty
        if not self.all_exist(params):
            answer=QMessageBox.warning(self, "Warning", "Not all values are filled in, continue anyway?", QMessageBox.Yes | QMessageBox.Cancel)
            if answer==QMessageBox.Yes:
                print_anyway=True
            elif answer==QMessageBox.Cancel:
                return


        ## Validate paths
        for param in [intervals, projdir, output_directory]:
            if print_anyway:
                break
            try:
                self.validate_path(param)

            except AssertionError:
                answer=QMessageBox.warning(self, "Warning", "{0}is not a valid path, continue anyway?".format(param), QMessageBox.Yes | QMessageBox.YesToAll | QMessageBox.Cancel)

                if answer==QMessageBox.YesToAll:
                    print_anyway=True
                elif answer==QMessageBox.Cancel:
                    return

        ## Validate values
        for x in [density, cluster, local, cutoff]:
            if print_anyway:
                break
            try:
                self.validate_and_parse_integer(x)
            except Exception:
                answer=QMessageBox.warning(self, "Warning", "{0} is not a valid number, continue anyway?".format(x), QMessageBox.Yes | QMessageBox.YesToAll | QMessageBox.Cancel)
                if answer==QMessageBox.YesToAll:
                    print_anyway=True
                elif answer==QMessageBox.Cancel:
                    return


        name = (QFileDialog.getSaveFileName(self, 'Save File',filter="*.yaml"))

        # if nothing was chosen: exit
        if name[0]=="":
            return

        # correct the name if necessary
        name=(name[0] if name[0][-5:]==".yaml" else name[0]+name[1])
        try:
            file=open(name, "w+")
        except IOError:
            warning = QMessageBox.critical(self, "Error", "File {0} unavailable, exiting.".format(name), QMessageBox.Ok)
            return

        #remove empty fields
        to_remove=[]
        for k,v in param_dict.items():
            if v=="":
                to_remove.append(k)

        for item in to_remove:
            param_dict.pop(item)

        yaml.dump(param_dict, file)
        file.close()
        return

    def handle_error(self, error):
        """Handle errors generated by the spectrum process.

        Additional error handling should be implemented here. As the error is a string message, error handling happens
        by checking for substrings.

        :param error: The error thrown by the spectrum process.
        :type error: str
        :return: (str) A message to be shown in the waiter window.
        """

        #data missing error
        if "raise DataMissing()" in str(error):
            message ="Error:\nThe project directory has no valid spectra."
        elif "raise IOError" in str(error):
            message="Error:\nPlease make sure all output files are closed \nbefore starting the program."
        elif "raise NameMapMissing()" in str(error):
            message="Error:\nThe project directory has no QualityControlledDBFields files."
        else:
            message= "An unknown error has occurred,\nsee err.txt for details."
            try:
                location=os.path.join(self.output_directory_input.text(),"err.txt")
                err=open(location, "w+")
                err.write("Input arguments:\n"+str(self.process_args)+"\n")
                err.write("Error:\n"+str(error))
                err.close()
            except IOError:
                warning = QMessageBox.critical(self, "Critical", "err.txt unavailable, exiting", QMessageBox.Ok)
                exit()

        return message


    #Data validation
    def validate_and_parse_integer(self, value):
        """Validate the input and return it as an int if validation is successful.

        :param value: Value to be validated as int
        :type value: str
        :raise AssertionError: when an empty str is given
        :raise Exception: when `value` can't be cast to an int
        :return: value cast to an integer
        """
        try:
            res=int(value)
            return res

        except Exception:
            raise Exception

    def validate_path(self, path):
        """Check if `path` exists.

        :param path: parameter to be validated
        :type path: str
        :raise AssertionError: when `path` does not exist
        :return: void
        """
        try:
            assert (os.path.exists(path)==1)
        except AssertionError:
            raise AssertionError

    def all_exist(self, param_array):
        """Check if none of the elements in param_array is the empty string.

        :param param_array: parameter array to be checked
        :type param_array: array[str]
        :return: True if none of the elements in param_array is the empty string, False otherwise
        """

        for i in param_array:
           if i=="":
               return False
        return True

    #Help functions

    def kill_process(self):
        """Kill the ongoing process if there is one.

        :return: void
        """
        if  self.spectrum_process is not None:
            message=QMessageBox.question(self, "Abort", "Are you sure you want to abort processing?", QMessageBox.Yes | QMessageBox.Cancel)
            if message==QMessageBox.Yes:
                self.clean_subprocess(True)
                self.handle_process_finished(killed=True)

    def enable_param_input(self, my_bool):
        """Enable or disable parameter input.

        :param my_bool: True if parameter input is enabled.
        :type my_bool: bool
        :return: void
        """
        self.density_input.setEnabled(my_bool)
        self.cutoff_input.setEnabled(my_bool)
        self.cluster_input.setEnabled(my_bool)
        self.local_input.setEnabled(my_bool)
        self.intervals_input.setEnabled(my_bool)
        self.i_picker.setEnabled(my_bool)

    def enable_input(self, my_bool):
        if not my_bool:
            self.project_directory_input.setEnabled(False)
            self.proj_picker.setEnabled(False)
            self.output_directory_input.setEnabled(False)
            self.folder_out_picker.setEnabled(False)
            self.csv_rb.setEnabled(False)
            self.txt_rb.setEnabled(False)
            self.def_button.setEnabled(False)
            self.val_button.setEnabled(False)
            self.krona_button.setEnabled(False)
            self.cop_button.setEnabled(False)
            if not self.def_button.isChecked(): #also disable param input
                self.enable_param_input(False)
        else:
            self.project_directory_input.setEnabled(True)
            self.proj_picker.setEnabled(True)
            self.output_directory_input.setEnabled(True)
            self.folder_out_picker.setEnabled(True)
            self.csv_rb.setEnabled(True)
            self.txt_rb.setEnabled(True)
            self.def_button.setEnabled(True)
            self.val_button.setEnabled(True)
            self.krona_button.setEnabled(True)
            self.cop_button.setEnabled(True)
            if not self.def_button.isChecked(): #also enable param input
                self.enable_param_input(True)






    def center(self):
        """Center self.

        :return: void
        """
        geo = self.frameGeometry()
        screen_center = QDesktopWidget().availableGeometry().center()
        geo.moveCenter(screen_center)
        self.move(geo.topLeft())

    def clean_subprocess(self, kill=False):
        """Remove the currently assigned spectrum process.

        :param kill: True if the process should also be killed.
        :type kill: bool
        :return: void
        """
        if self.spectrum_process is not None:
            if kill:
                self.spectrum_process.terminate()
            self.spectrum_process=None
            self.spectrum_process_args=None

    def get_config_params(self):
        """Return all config values.

        :return: A dict with all config values and keys: intervals (str), project_directory (str), output_directory (str), density (str), cluster (str), local (str), cutoff (str), validation (bool), output_type (str)
        """

        intervals=self.intervals_input.text()
        project_directory=self.project_directory_input.text()
        output_directory=self.output_directory_input.text()
        density=self.density_input.text()
        cluster=self.cluster_input.text()
        local=self.local_input.text()
        cutoff=self.cutoff_input.text()
        validation=self.val_button.isChecked()
        copy=self.cop_button.isChecked()
        krona=self.krona_button.isChecked()
        output_type=None


        buttons = (self.output_group.itemAt(i).widget() for i in range(self.output_group.count()))
        for button in buttons:
            if button.isChecked():
                output_type=button.text()
                break

        names=["intervals", "project_directory", "output_directory", "density", "cluster", "local", "cutoff", "validation", "output_type", "copy", "krona"]

        res={}

        # add all to dictionary
        for name in names:
            res[name]=eval(name)

        return res

    def get_output_extension(self):
        """Return the output extension without "." (e.g. txt)

        :return: (str) The output extension.
        """
        buttons = (self.output_group.itemAt(i).widget() for i in range(self.output_group.count()))
        for button in buttons:
            if button.isChecked():
                return button.text()

    def set_density(self, density_n):
        self.density_input.setText(density_n)

    def set_cluster(self, cluster_n):
        self.cluster_input.setText(cluster_n)

    def set_local(self, local_n):
        self.local_input.setText(local_n)

    def set_cutoff(self, cutoff_n):
        self.cutoff_input.setText(cutoff_n)

    def set_intervals(self, intervals_n):
        self.intervals_input.setText(intervals_n)

    def set_proj_dir(self, proj_dir_n):
        self.project_directory_input.setText(proj_dir_n)

    def set_output_directory(self, output_dir_n):
        self.output_directory_input.setText(output_dir_n)


class WaitWindow(QWidget):
    """A window that is shown when the user wait for data to be processed."""

    def __init__(self, abort_handler, ok_handler):
        """Make a waiter window.

        :param abort_handler: A handler called when the abort button is clicked.
        :type abort_handler: function_pointer
        """
        super().__init__()

        self.ok_button=None
        self.abort_button=None
        self.wait_label=None
        self.abort_handler=abort_handler
        self.ok_hanlder=ok_handler

        self.setFixedSize(400, 250)
        self.setWindowTitle("Processing")
        self.center()
        self.setWindowIcon(QIcon(path.join(path.dirname(path.abspath(__file__)),"Media/Ghent_University_Temple")))
        self.center()
        self.fill_body()
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.CustomizeWindowHint)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowCloseButtonHint)

    def fill_body(self):
        """Fill the body of the WaitWindow Class.

        :return: void
        """

        #body
        main_layout=QVBoxLayout()

        #label
        self.wait_label=QLabel("Data is being processed")

        #buttons

        ##Abort button
        self.abort_button=QPushButton("Abort")
        self.abort_button.clicked.connect(self.handle_abort)


        ##ok_button
        self.ok_button=QPushButton("OK")
        self.ok_button.setEnabled(False)
        self.ok_button.clicked.connect(self.handle_ok)

        #Group buttons
        bbox=QHBoxLayout()
        bbox.addWidget(self.ok_button)
        bbox.addWidget(self.abort_button)

        #Add everything
        main_layout.addWidget(self.wait_label,alignment=QtCore.Qt.AlignCenter)
        main_layout.addLayout(bbox)

        self.setLayout(main_layout)

    def center(self):
        """Center self.

        :return: void
        """
        geo = self.frameGeometry()
        screen_center = QDesktopWidget().availableGeometry().center()
        geo.moveCenter(screen_center)
        self.move(geo.topLeft())

    def set_ok_button(self, enabled):
        """Disable or enable the ok button.

        :param enabled: True if the ok button should be enabled.
        :type enabled: bool
        :return:
        """
        self.ok_button.setEnabled(enabled)

    def set_text(self,new_text):
        self.wait_label.setText(new_text)

    def reset_text(self):
        """Reset the text of the waiter window.

        Reset the text to "Data is being processed".

        :return: void
        """
        self.wait_label.setText("Data is being processed")

    def to_front(self):
        """Raise self to front.

        :return: void
        """
        self.raise_()

    # Event handling
    def handle_ok(self):
        """Handle a click on the ok button.

        Disable the ok button and close the waiter window.

        :return: void
        """
        self.ok_button.setEnabled(False)
        self.close()
        handler=ProcessedEvent(self.ok_hanlder)
        handler.handle_signal()

    def handle_abort(self):
        """Execute the abort handler attribute.

        :return: Type of `abort_handler`.
        """
        kill_process=ProcessedEvent(self.abort_handler)
        kill_process.handle_signal()


class ProcessedEvent:
    """A Class for cross thread and process communication."""
    def __init__(self, fpointer):
        """Make a ProcessedEvent instance.

        :param fpointer: A function pointer to be executed when handle_signal is called.
        """
        self.processed=pyqtSignal()
        self.fpointer=fpointer

    def signal(self):
        self.processed.emit()

    @pyqtSlot()
    def handle_signal(self):
        self.fpointer()


if __name__ == '__main__':
    main()
