import os
import math


class ComponentInfo:
    """
    Internal class used to store information on parameters of components
    """

    def __init__(self):
        self.name = ""
        self.category = ""
        self.parameter_names = []
        self.parameter_defaults = {}
        self.parameter_types = {}
        self.parameter_comments = {}
        self.parameter_units = {}


class ComponentReader:
    """
    Class for retrieving information on available McStas components

    Recursively reads all component files in hardcoded list of
    folders that represents the component categories in McStas.
    The results are stored in a dictionary with ComponentInfo
    instances, the keys are the names of the components. After
    the components in the McStas installation are read, any
    components present in the current work directory is read,
    and these will overwrite existing information, consistent
    with how McStas reads component definitions.

    """

    def __init__(self, mcstas_path, input_path="."):
        """
        Reads all component files in standard folders. Recursive, so
        subfolders of these folders are included.

        Parameters
        ----------
        mcstas_path : str
            Path to McStas folder, used to find the installed components

        keyword arguments:
            input_path : str
                Path to work directory, most often current directory

        """

        # Hardcoded whitelist of foldernames
        folder_list = ["sources",
                       "optics",
                       "samples",
                       "monitors",
                       "misc",
                       "contrib",
                       "obsolete",
                       "union"]

        self.component_path = {}
        self.component_category = {}

        for folder in folder_list:
            abs_path = os.path.join(mcstas_path, folder)
            abs_path = os.path.abspath(abs_path)
            self._find_components(abs_path)

        # Will overwrite McStas components with definitions in input_folder
        current_directory = os.getcwd()

        # Set up absolute input_path
        if os.path.isabs(input_path):
            input_directory = input_path
        else:
            if input_path == ".":
                # Default case, avoid having /./ in absolute path
                input_directory = current_directory
            else:
                input_directory = os.path.join(current_directory, input_path)

        if not os.path.isdir(input_directory):
            print("input_path: ", input_directory)
            raise ValueError("Can't find given input_path,"
                             + " directory must exist.")
        """
        If components are present both in the McStas install and the
        work directory, the version in the work directory is used. The user
        is informed of this behavior when the instrument object is created.
        """
        overwritten_components = []
        for file in os.listdir(input_directory):
            if file.endswith(".comp"):
                abs_path = os.path.join(input_directory, file)
                component_name = os.path.split(abs_path)[1].split(".")[-2]

                if component_name in self.component_path:
                    overwritten_components.append(file)

                self.component_path[component_name] = abs_path
                self.component_category[component_name] = "work directory"

        # Report components found in the work directory and install to the user
        if len(overwritten_components) > 0:
            print("The following components are found in the work_directory"
                  + " / input_path:")
            for name in overwritten_components:
                print("    ", name)

            print("These definitions will be used instead of the installed "
                  + "versions.")

    def show_categories(self):
        """
        Method that will show all component categories available

        Sorted alphabetically for easier readability and consistency
        """
        categories = []
        for component, category in self.component_category.items():
            if category not in categories:
                categories.append(category)

        categories.sort()
        for category in categories:
            print(" " + category)

    def show_components_in_category(self, category_input, **kwargs):
        """
        Method that will show all components in given category

        """
        if "line_length" in kwargs:
            line_limit = int(kwargs["line_length"])
            if line_limit < 20:
                raise ValueError("line_length should be more than 20 "
                                 + "characters, was " + str(line_limit))
        else:
            line_limit = 100

        empty_category = True
        to_print = []
        for component, category in self.component_category.items():
            if category == category_input:
                to_print.append(component)
                empty_category = False

        to_print.sort()
        if empty_category:
            print("No components found in this category! "
                  + "Available categories:")
            self.show_categories()

        elif len(to_print) < 10:
            for component in to_print:
                print(" " + component)
        else:
            # Prints in columns, maximum 4 and maximum line length line_limit
            columns = 5
            total_line_length = 1000
            while(total_line_length > line_limit):
                columns = columns - 1

                c_length = math.ceil(len(to_print)/columns)
                last_length = len(to_print) - (columns-1)*c_length

                column = []
                longest_name = []
                for col in range(0, columns-1):
                    current_list = to_print[c_length*col:c_length*(col+1)]
                    column.append(current_list)
                    longest_name.append(len(max(current_list, key=len)))

                column.append(to_print[c_length*(columns-1):])
                longest_name.append(len(max(column[columns-1], key=len)))

                total_line_length = 1 + sum(longest_name) + (columns-1)*3

            for line_nr in range(c_length):
                print(" ", end="")
                for col in range(columns-1):
                    this_name = column[col][line_nr]
                    print(this_name
                          + " "*(longest_name[col] - len(this_name))
                          + "   ", end="")  # More columns left, dont break
                if line_nr < last_length:
                    this_name = column[columns-1][line_nr]
                    print(this_name)
                else:
                    print("")

    def load_all_components(self):
        """
        Method that loads information on all components into memory.

        """

        return_dict = {}
        for comp_name, abs_path in self.component_path.items():
            return_dict[comp_name] = self.read_component_file(abs_path)

        return return_dict

    def read_name(self, component_name):
        """
        Returns ComponentInfo of component with name component_name.

        Uses table of absolute paths to all known components, and
        reads the appropriate file in order to generate the information.

        """

        if component_name not in self.component_path:
            raise NameError("No component named "
                            + component_name
                            + " in McStas installation or "
                            + "current work directory.")

        output = self.read_component_file(self.component_path[component_name])

        # Category loaded using path, in case of Work directory it fails
        if self.component_category[component_name] == "work directory":
            output.category = "work directory"  # Corrects category

        return output

    def _find_components(self, absolute_path):
        """
        Recursive read function, can read either file or entire folder

        Updates the component_info_dict with the findings that are
        stored as ComoponentInfo instances.

        """

        if not os.path.isabs(absolute_path):
            raise RuntimeError("_find_components received non absolute path")

        if not os.path.isdir(absolute_path):
            if absolute_path.endswith(".comp"):
                # read this file
                component_name = os.path.split(absolute_path)[1].split(".")[-2]
                self.component_path[component_name] = absolute_path

                head = os.path.split(absolute_path)[0]
                component_category = os.path.split(head)[1]
                self.component_category[component_name] = component_category
        else:
            for file in os.listdir(absolute_path):
                absolute_file_path = os.path.join(absolute_path, file)
                self._find_components(absolute_file_path)

    def read_component_file(self, absolute_path):
        """
        Reads a component file and expands component_info_dict

        The information is stored as ComponentClass instances.

        """

        result = ComponentInfo()

        file_o = open(absolute_path, "r")

        line_number = 0
        while True:
            line_number += 1
            line = file_o.readline()

            # find parameter comments
            if line.startswith("* %P"):

                while True:
                    this_line = file_o.readline()

                    if this_line.startswith("DEFINE COMPONENT"):
                        # No more comments to read through
                        break

                    if ":" in this_line:
                        tokens = this_line.split(":")

                        variable_name = tokens[0]
                        variable_name = variable_name.replace("*", "")
                        variable_name = variable_name.strip()
                        if " " in variable_name:
                            name_tokens = variable_name.split(" ")
                            variable_name = name_tokens[0]

                        if len(tokens[1]) > 2:
                            comment = tokens[1].strip()

                            if "[" in comment:  # Search for unit
                                # If found, store it and remove from string
                                unit = comment[comment.find("[") + 1:
                                               comment.find("]")]
                                result.parameter_units[variable_name] = unit
                                comment = comment[comment.find("]") + 1:]
                                comment = comment.strip()

                            # Store the comment
                            result.parameter_comments[variable_name] = comment
                    elif "[" in this_line and "]" in this_line:
                        tokens = this_line.split("[")

                        variable_name = tokens[0]
                        variable_name = variable_name.replace("*", "")
                        variable_name = variable_name.strip()

                        unit = this_line[this_line.find("[") + 1:
                                         this_line.find("]")]
                        result.parameter_units[variable_name] = unit

                        comment = this_line[this_line.find("]") + 1:]
                        comment = comment.strip()
                        result.parameter_comments[variable_name] = comment

            # find definition parameters and their values
            if (line.strip().startswith("DEFINITION PARAMETERS")
                    or line.strip().startswith("SETTING PARAMETERS")):

                line = line.split("//")[0]  # Remove comments
                parts = line.split("(")
                parameter_parts = parts[1].split(",")
                parameter_parts = self.correct_for_brackets(parameter_parts)
                parameter_parts = list(filter(("\n").__ne__, parameter_parts))

                break_now = False
                while True:
                    # Read all definition parameters

                    for part in parameter_parts:

                        temp_par_type = "double"

                        part = part.strip()

                        # remove trailing )
                        if ")" in part:
                            part = part.replace(")", "")
                            break_now = True

                        possible_declare = part.split(" ")
                        possible_type = possible_declare[0].strip()
                        if "int" == possible_type:
                            temp_par_type = "int"
                            # remove int from part
                            part = "".join(possible_declare[1:])
                        if "string" == possible_type:
                            temp_par_type = "string"
                            # remove string from part
                            part = "".join(possible_declare[1:])
                        if "double" == possible_type:
                            temp_par_type = "double"
                            # remove double from part
                            part = "".join(possible_declare[1:])

                        part = part.replace(" ", "")
                        if part == "":
                            continue

                        if part.startswith("//"):
                            break_now = True
                            continue

                        if part.startswith("/*"):
                            break_now = True
                            continue

                        if "=" not in part:
                            # no default value, required parameter
                            result.parameter_names.append(part)
                            result.parameter_defaults[part] = None
                            result.parameter_types[part] = temp_par_type
                        else:
                            # default value available
                            name_value = part.split("=")
                            par_name = name_value[0].strip()
                            par_value = name_value[1].strip()

                            if temp_par_type == "double":
                                try:
                                    par_value = float(par_value)
                                except ValueError:
                                    # value could be parameter name
                                    par_value = par_value
                            elif temp_par_type == "int":
                                par_value = int(par_value)

                            result.parameter_names.append(par_name)
                            result.parameter_defaults[par_name] = par_value
                            result.parameter_types[par_name] = temp_par_type

                    if break_now:
                        break

                    new_line = file_o.readline().split("//")[0]
                    new_line = new_line.split(",")
                    new_line = self.correct_for_brackets(new_line)
                    parameter_parts = new_line

            if line.startswith("DECLARE"):
                break

            if line.startswith("TRACE"):
                break

            if line_number == 4000:
                break

        file_o.close()

        result.name = os.path.split(absolute_path)[1].split(".")[-2]

        tail = os.path.split(absolute_path)[0]
        result.category = os.path.split(tail)[1]

        """
        To lower memory use one could remove all comments and units that
        does not correspond to a found parameter name.
        """

        return result

    def correct_for_brackets(self, parameter_parts):
        """
        Given list of string elements, correct for brackets will
        combine terms until curly brackets are balanced, for example:

        ["A", "{B", "C", "D}", "E"] would return ["A", "{B,C,D}", "E"]

        Default values of vectors can be given in such a manner in
        McStas components, and without this each part would be recognized
        as different parameters.
        """
        corrected_parts = []
        index = 0
        while True:

            current_part = parameter_parts[index]
            inner_index = 0
            while True:
                if current_part.count("{") == current_part.count("}"):
                    corrected_parts.append(current_part)
                    index += inner_index
                    break
                else:
                    inner_index += 1
                    current_part += "," + parameter_parts[index+inner_index]

            index += 1

            if index >= len(parameter_parts):
                break

        return corrected_parts
