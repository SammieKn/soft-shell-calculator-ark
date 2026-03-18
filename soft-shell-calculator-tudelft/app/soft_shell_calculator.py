# Disclaimer
# Soft Shell Calculator
# © (2025) TU Delft & Gemeente Amsterdam
# Soft shell calculator version v1.1 from Anindya and revised by Michele Mirra


# DISCLAIMER
# De TU Delft heeft met een zo groot mogelijke zorgvuldigheid deze tool
# ontwikkelt maar sluit niet uit dat er fouten in de software zitten.
# De tool is expliciet bedoeld als experimentele versie voor intern gebruik
# van de gemeente Amsterdam om ervaring op te doen met de interpretatie
# van RPD signalen. Dit is geen commerciële versie en de TU Delft beoogd
# ook niet deze tool als commerciële versie te onderhouden.
# Zo’n versie kan eventueel in een later stadium met een professionele
#  software-ontwikkelaar verder geprogrammeerd en onderhouden worden.

# De soft shell calculator kan alleen een betrouwbare waarde voor de
# zachte schil afgeven als het signaal van voldoende kwaliteit is.
# Dit vergt ervaring van de gebruiker om dit te beoordelen


# Import relevant modules


import sys
import matplotlib.pyplot as plt
import json
import os
import pandas as pd
import numpy as np
import xlsxwriter
import wx

import difflib
from matplotlib.image import imread
from scipy.signal import find_peaks, savgol_filter
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_pdf import PdfPages


def pair_similar_names(names, threshold=0.8):
    pairs = []
    used = set()
    for i, file1 in enumerate(names):
        if file1 in used:
            continue
        for file2 in names[i + 1 :]:
            if file2 in used:
                continue
            similarity = difflib.SequenceMatcher(None, file1, file2).ratio()
            if similarity >= threshold:
                pairs.append((file1, file2))
                used.add(file1)
                used.add(file2)
                break
    return pairs


# Define user interface


class MainWindow(wx.Frame):

    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, title=title)

        self.InitUI()
        self.Centre()
        self.Show()

    def InitUI(self):
        # user interface
        vbox = wx.BoxSizer(wx.VERTICAL)
        self.statusbar = self.CreateStatusBar(1)
        self.statusbar.SetStatusText("© (2025) TU Delft & Gemeente Amsterdam")
        #    self.file = "LOGO.png"
        #    self.logo = imread(self.file)
        self.figure = plt.figure(figsize=(10, 3))
        self.axes = self.figure.add_subplot(111)
        #    self.axes.imshow(self.logo)
        self.axes.axis("off")
        self.graph = FigureCanvas(self, -1, self.figure)
        vbox.Add(self.graph, 1, wx.EXPAND)

        vbox.AddSpacer(20)

        self.b1 = wx.Button(self, label="Load single RPD measurement", size=(200, 30))
        self.Bind(wx.EVT_BUTTON, self.OnClickb1, self.b1)
        vbox.Add(self.b1, 0, wx.ALIGN_CENTER_HORIZONTAL)

        vbox.AddSpacer(20)

        self.b2 = wx.Button(
            self, label="Load multiple RPD measurements", size=(200, 30)
        )
        self.Bind(wx.EVT_BUTTON, self.OnClickb2, self.b2)
        vbox.Add(self.b2, 0, wx.ALIGN_CENTER_HORIZONTAL)

        vbox.AddSpacer(20)

        self.check = wx.CheckBox(self, label="Pair RPD measurements")
        vbox.Add(self.check, 0, wx.ALIGN_CENTER_HORIZONTAL)
        self.check.Enable(False)

        vbox.AddSpacer(20)

        self.b3 = wx.Button(self, label="Analyze and generate output", size=(200, 30))
        vbox.Add(self.b3, 0, wx.ALIGN_CENTER_HORIZONTAL)
        self.Bind(wx.EVT_BUTTON, self.OnClickb3, self.b3)
        self.b3.Enable(False)

        vbox.AddSpacer(20)

        self.SetSizerAndFit(vbox)

    def OnClickb1(self, event):

        with wx.FileDialog(
            self,
            "Open RPD file",
            wildcard="RPD files (*.rgp)|*.rgp",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return  # the user changed their mind

            # Proceed loading the file chosen by the user
            self.pathname = fileDialog.GetPath()

            try:
                with open(self.pathname, "r") as file:
                    self.filename = fileDialog.GetFilename()
                    self.statusbar.SetStatusText(
                        "File '%s' loaded correctly" % self.filename
                    )
                    self.b3.Enable(True)
                    self.path_dir = self.filename

            except IOError:
                wx.LogError("Cannot open file '%s'." % file)

    def OnClickb2(self, event):

        with wx.DirDialog(
            self, "Choose a directory", style=wx.DD_DEFAULT_STYLE
        ) as dialog:

            if dialog.ShowModal() == wx.ID_OK:
                self.path_dir = dialog.GetPath()
                self.filename = self.path_dir
                self.statusbar.SetStatusText(f"Selected Directory: {self.path_dir}")
                self.b3.Enable(True)
                self.check.Enable(True)
                self.b1.Enable(False)

    def OnClickb3(self, event):

        self.figure = plt.figure(figsize=(10, 3))
        self.axes = self.figure.add_subplot(111)
        # self.axes.imshow(self.logo)
        self.axes.axis("off")
        self.graph = FigureCanvas(self, -1, self.figure)

        status_text = self.statusbar.GetStatusText()
        if status_text == (f"File '{self.filename}' loaded correctly"):
            # Analysis with single file
            with open(self.pathname, "r") as read_file:
                data = json.load(read_file)
                # RPD analysis
                # Retrieving data from the .rgp files
            meas_year = data["header"]["dateYear"]
            meas_month = data["header"]["dateMonth"]
            meas_day = data["header"]["dateDay"]

            drill_amp = np.array(data["profile"]["drill"])

            resolution = data["header"]["resolutionFeed"]
            depth = np.arange(0, len(drill_amp), 1) / resolution
            threshold1 = 0.01 * np.average(drill_amp)

            # removing too low values
            filtered_signal = drill_amp[(drill_amp > threshold1)]
            threshold_cut = np.min(np.where(drill_amp > threshold1)) / resolution

            pile_signal = []

            i = 0
            while i < len(filtered_signal) - 25:
                window = filtered_signal[i : i + 25]
                if np.var(window) > 0.01:

                    pile_signal.extend(window)
                    i += 25
                else:
                    i += 1

            pile_signal.extend(filtered_signal[i:])

            diameter = len(pile_signal) / resolution
            drilldepth = np.arange(0, len(pile_signal), 1) / resolution

            # overlap original and cut signal

            for p in range(len(drill_amp) - 25):
                window = drill_amp[p : p + 25]
                if np.var(window) > 0.01:
                    overlap_position = p / resolution
                    break

            depth_overlap_position = max(threshold_cut, overlap_position)

            movav = np.empty(len(pile_signal), dtype=object)
            for N in range(len(pile_signal)):
                i = N - 50
                j = N + 50
                k = 100
                if i < 0:
                    i = 0
                    j = N + 1
                    k = j
                elif j > len(pile_signal):
                    j = len(pile_signal)
                    k = j - i

                movav[N] = sum(pile_signal[i:j]) / k
            pile_signal1 = savgol_filter(pile_signal, 15, 11)
            rings = round(
                len(find_peaks(pile_signal1, distance=0.1 * resolution)[0]) / 2, 0
            )

            pith = diameter / 2

            rings_075_left = round(
                len(
                    find_peaks(
                        pile_signal1[int(0) : int(0.75 * diameter / 2 * resolution)],
                        distance=0.1 * resolution,
                    )[0]
                ),
                0,
            )
            rings_075_right = round(
                len(
                    find_peaks(
                        pile_signal1[
                            int(1.25 * diameter / 2 * resolution) : int(
                                diameter * resolution
                            )
                        ],
                        distance=0.1 * resolution,
                    )[0]
                ),
                0,
            )

            growth_rate = (
                (0.75 * diameter / 2) / rings_075_left
                + (0.75 * diameter / 2) / rings_075_right
            ) / 2

            sapwood = round(
                (37.17 * (growth_rate) ** 0.95) / (1 + 5.58 * np.exp(-0.054 * rings)), 0
            )

            ioma_left = []
            ioma_right = []
            array_movav = []
            for i in reversed(movav[: int(pith * resolution)]):
                array_movav.append(i)
                ioma_left.append(sum(array_movav) / len(array_movav))
                array_movav = []
            for i in movav[int(pith * resolution) :]:
                array_movav.append(i)
                ioma_right.append(sum(array_movav) / len(array_movav))
                ioma_left = list(reversed(ioma_left))

            soft_shell_left = (
                np.min(np.where(movav > 0.4 * np.max(ioma_left))) / resolution
            )
            soft_shell_right = (
                np.max(np.where(movav > 0.4 * np.max(ioma_right))) / resolution
            )

            # plot graphs
            self.figure = plt.figure(figsize=(10, 3))
            # plot drilling resistance graph
            self.axes = self.figure.add_subplot(
                121,
                title="%s - Drilling signal" % self.filename,
                xlabel="Drilling depth (mm)",
                ylabel="Drilling resistance (%)",
            )
            self.axes.plot(
                depth - depth_overlap_position,
                drill_amp,
                color="grey",
                label="Drill (original signal)",
                linestyle="dotted",
            )
            self.axes.plot(
                drilldepth, pile_signal, color="blue", label="Drill (after cut-off)"
            )
            self.axes.plot(drilldepth, movav, color="red", label="Moving average")
            self.axes.axvline(x=0, color="black", linestyle="dashed")
            self.axes.axvline(
                x=diameter / 2, color="purple", linestyle="dashed", label="Center"
            )
            self.axes.axvline(
                x=diameter,
                color="black",
                linestyle="dashed",
                label="Estimated diameter (%.1f mm)" % diameter,
            )
            self.axes.axvline(
                x=sapwood,
                color="orange",
                linestyle="dashed",
                label="Estimated sapwood width (%.1f mm)" % sapwood,
            )
            self.axes.axvline(x=diameter - sapwood, color="orange", linestyle="dashed")
            self.axes.axvline(
                x=soft_shell_left,
                color="green",
                linestyle="dashed",
                label="Soft shell (left %.1f mm, right %.1f mm)"
                % (soft_shell_left, diameter - soft_shell_right),
            )
            self.axes.axvline(x=soft_shell_right, color="green", linestyle="dashed")
            self.axes.axvspan(0, diameter, color=(1, 0.7, 0.7))
            self.axes.axvspan(
                soft_shell_left, soft_shell_right, color=(0.753, 1, 0.737)
            )
            self.axes.axvspan(sapwood, diameter - sapwood, color=(0.569, 0.71, 0.51))
            self.axes.legend()
            # plot polar graph
            self.circle = self.figure.add_subplot(122, polar=True)
            self.circle.set_title("%s - Cross section overview" % self.filename)
            self.circle.set_ylim(0, 200)
            r_pile = diameter / 2
            r_soft_left = diameter / 2 - soft_shell_left
            r_soft_right = -diameter / 2 + soft_shell_right
            r_sap = diameter / 2 - sapwood
            theta = [0, np.pi, 0, 0]
            width = [2 * np.pi, np.pi, np.pi, 2 * np.pi]
            radii = [r_pile, r_soft_left, r_soft_right, r_sap]

            bars = self.circle.bar(theta, radii, width=width, bottom=0.0)
            for r, bar in zip(radii, bars):
                bars[0].set_facecolor((1, 0.7, 0.7))
                bars[0].set_label("Soft shell")
                bars[1].set_facecolor((0.753, 1, 0.737))
                bars[2].set_facecolor((0.753, 1, 0.737))
                bars[1].set_label("Sound cross section")
                bars[3].set_facecolor((0.569, 0.71, 0.51))
                bars[3].set_label("Estimated heartwood")

            self.circle.set_xticklabels([])
            self.circle.text(
                0,
                210,
                "Soft shell right (%.1f mm)" % (diameter - soft_shell_right),
                rotation=90,
                ha="center",
                va="center",
                fontsize=10,
            )
            self.circle.text(
                np.pi,
                210,
                "Soft shell left (%.1f mm)" % soft_shell_left,
                rotation=90,
                ha="center",
                va="center",
                fontsize=10,
            )
            self.circle.text(
                1.5 * np.pi,
                210,
                "Pile radius (%.1f mm)" % (diameter / 2),
                rotation=0,
                ha="center",
                va="center",
                fontsize=10,
            )
            self.circle.text(0, 0, "0")
            self.circle.set_rlabel_position(270)
            self.circle.legend(bbox_to_anchor=(0.85, 1.025), loc="upper left")
            # show graph on user interface
            self.figure.tight_layout()
            self.canvas = FigureCanvas(self.graph, -1, self.figure)

            # Saving file dialogue

            with wx.FileDialog(
                self,
                "Save output Excel file",
                defaultFile="Output.xlsx",
                wildcard="Excel files (*.xlsx)|*.xlsx",
                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
            ) as fileDialog:

                if fileDialog.ShowModal() == wx.ID_CANCEL:
                    return  # the user changed their mind
                xls_pathname = fileDialog.GetPath()
                try:
                    wb = xlsxwriter.Workbook(xls_pathname)
                    worksheet = wb.add_worksheet()
                    worksheet.write(0, 0, "Measurement ID")
                    worksheet.write(0, 1, "Measurement date")
                    worksheet.write(0, 2, "Estimated diameter (mm)")
                    worksheet.write(0, 3, "Estimated number of annual rings")
                    worksheet.write(0, 4, "Estimated sapwood width (mm)")
                    worksheet.write(0, 5, "Estimated soft shell left (mm)")
                    worksheet.write(0, 6, "Estimated soft shell right (mm)")

                    worksheet.write(1, 0, f"{self.filename}")
                    worksheet.write(1, 1, f"{meas_day}-{meas_month}-{meas_year}")
                    worksheet.write(1, 2, diameter)
                    worksheet.write(1, 3, rings)
                    worksheet.write(1, 4, sapwood)
                    worksheet.write(1, 5, soft_shell_left)
                    worksheet.write(1, 6, round(diameter - soft_shell_right, 1))
                    wb.close()
                except IOError:
                    wx.LogError("Cannot save current data in file '%s'." % xls_pathname)
            with wx.FileDialog(
                self,
                "Save output PDF file",
                defaultFile="Output.pdf",
                wildcard="PDF files (*.pdf)|*.pdf",
                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
            ) as fileDialog:

                if fileDialog.ShowModal() == wx.ID_CANCEL:
                    return  # the user changed their mind
                pdf_pathname = fileDialog.GetPath()
                try:

                    with PdfPages(pdf_pathname) as pdf:

                        pdf.savefig(
                            self.figure
                        )  # saves the current figure into a pdf page
                except IOError:
                    wx.LogError("Cannot save current data in file '%s'." % pdf_pathname)

            self.statusbar.SetStatusText(
                "Output for file '%s' generated correctly." % self.filename
            )
            self.b3.Enable(False)

        elif status_text == (f"Selected Directory: {self.path_dir}"):

            # analysis of multiple RPD files - saving excel & pdf files
            with wx.FileDialog(
                self,
                "Save output Excel file",
                defaultFile="Output.xlsx",
                wildcard="Excel files (*.xlsx)|*.xlsx",
                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
            ) as fileDialog:

                if fileDialog.ShowModal() == wx.ID_CANCEL:
                    return  # the user changed their mind
                xls_pathname = fileDialog.GetPath()

                try:
                    wb = xlsxwriter.Workbook(xls_pathname)
                    worksheet = wb.add_worksheet()
                    worksheet.write(0, 0, "Measurement ID")
                    worksheet.write(0, 1, "Measurement date")
                    worksheet.write(0, 2, "Estimated diameter (mm)")
                    worksheet.write(0, 3, "Estimated number of annual rings")
                    worksheet.write(0, 4, "Estimated sapwood width (mm)")
                    worksheet.write(0, 5, "Estimated soft shell left (mm)")
                    worksheet.write(0, 6, "Estimated soft shell right (mm)")
                    row = 1

                    for files in os.listdir(self.path_dir):
                        if files.endswith(".rgp"):

                            full_path = os.path.join(self.path_dir, files)
                            with open(full_path) as read_file:

                                #  with open(files) as read_file:
                                data = json.load(read_file)

                            # Retrieving data from the .rgp files
                            meas_year = data["header"]["dateYear"]
                            meas_month = data["header"]["dateMonth"]
                            meas_day = data["header"]["dateDay"]

                            drill_amp = np.array(data["profile"]["drill"])

                            resolution = data["header"]["resolutionFeed"]

                            threshold1 = 0.01 * np.average(drill_amp)

                            # removing too low values
                            filtered_signal = drill_amp[(drill_amp > threshold1)]
                            pile_signal = []
                            i = 0
                            while i < len(filtered_signal) - 25:
                                window = filtered_signal[i : i + 25]
                                if np.var(window) > 0.01:
                                    pile_signal.extend(window)
                                    i += 25
                                else:
                                    i += 1

                            pile_signal.extend(filtered_signal[i:])

                            diameter = len(pile_signal) / resolution
                            drilldepth = np.arange(0, len(pile_signal), 1) / resolution

                            movav = np.empty(len(pile_signal), dtype=object)
                            for N in range(len(pile_signal)):
                                i = N - 50
                                j = N + 50
                                k = 100
                                if i < 0:
                                    i = 0
                                    j = N + 1
                                    k = j
                                elif j > len(pile_signal):
                                    j = len(pile_signal)
                                    k = j - i

                                movav[N] = sum(pile_signal[i:j]) / k
                            pile_signal1 = savgol_filter(pile_signal, 15, 11)
                            rings = round(
                                len(
                                    find_peaks(pile_signal1, distance=0.1 * resolution)[
                                        0
                                    ]
                                )
                                / 2,
                                0,
                            )

                            pith = diameter / 2

                            rings_075_left = round(
                                len(
                                    find_peaks(
                                        pile_signal1[
                                            int(0) : int(
                                                0.75 * diameter / 2 * resolution
                                            )
                                        ],
                                        distance=0.1 * resolution,
                                    )[0]
                                ),
                                0,
                            )
                            rings_075_right = round(
                                len(
                                    find_peaks(
                                        pile_signal1[
                                            int(1.25 * diameter / 2 * resolution) : int(
                                                diameter * resolution
                                            )
                                        ],
                                        distance=0.1 * resolution,
                                    )[0]
                                ),
                                0,
                            )

                            growth_rate = (
                                (0.75 * diameter / 2) / rings_075_left
                                + (0.75 * diameter / 2) / rings_075_right
                            ) / 2

                            sapwood = round(
                                (37.17 * (growth_rate) ** 0.95)
                                / (1 + 5.58 * np.exp(-0.054 * rings)),
                                0,
                            )

                            ioma_left = []
                            ioma_right = []
                            array_movav = []
                            for i in reversed(movav[: int(pith * resolution)]):
                                array_movav.append(i)
                                ioma_left.append(sum(array_movav) / len(array_movav))
                                array_movav = []
                            for i in movav[int(pith * resolution) :]:
                                array_movav.append(i)
                                ioma_right.append(sum(array_movav) / len(array_movav))
                                ioma_left = list(reversed(ioma_left))

                            soft_shell_left = (
                                np.min(np.where(movav > 0.4 * np.max(ioma_left)))
                                / resolution
                            )
                            soft_shell_right = (
                                np.max(np.where(movav > 0.4 * np.max(ioma_right)))
                                / resolution
                            )

                            # preparing excel sheet

                            worksheet.write(row, 0, f"{files}")
                            worksheet.write(
                                row, 1, f"{meas_day}-{meas_month}-{meas_year}"
                            )
                            worksheet.write(row, 2, diameter)
                            worksheet.write(row, 3, rings)
                            worksheet.write(row, 4, sapwood)
                            worksheet.write(row, 5, soft_shell_left)
                            worksheet.write(
                                row, 6, round(diameter - soft_shell_right, 1)
                            )
                            row += 1

                            self.statusbar.SetStatusText(
                                "Generating output Excel file for directory '%s'"
                                % self.path_dir
                            )

                    wb.close()

                    # pair RPD measurements if asked for
                    if self.check.GetValue() == True:

                        df = pd.read_excel(xls_pathname)
                        file_names = df["Measurement ID"].tolist()
                        similar_pairs = pair_similar_names(file_names)

                        # create list to store average values
                        results = []
                        for name1, name2 in similar_pairs:
                            val1 = df.loc[
                                df["Measurement ID"] == name1, "Estimated diameter (mm)"
                            ].values
                            val2 = df.loc[
                                df["Measurement ID"] == name2, "Estimated diameter (mm)"
                            ].values

                            val3 = df.loc[
                                df["Measurement ID"] == name1,
                                "Estimated sapwood width (mm)",
                            ].values
                            val4 = df.loc[
                                df["Measurement ID"] == name2,
                                "Estimated sapwood width (mm)",
                            ].values

                            val5 = df.loc[
                                df["Measurement ID"] == name1,
                                "Estimated soft shell left (mm)",
                            ].values
                            val6 = df.loc[
                                df["Measurement ID"] == name2,
                                "Estimated soft shell left (mm)",
                            ].values

                            val7 = df.loc[
                                df["Measurement ID"] == name1,
                                "Estimated soft shell right (mm)",
                            ].values
                            val8 = df.loc[
                                df["Measurement ID"] == name2,
                                "Estimated soft shell right (mm)",
                            ].values

                            # Ensure both values exist
                            if val1.size > 0 and val2.size > 0:
                                avg_d = (val1[0] + val2[0]) / 2
                            else:
                                avg_d = None

                            if val3.size > 0 and val4.size > 0:
                                avg_sap = (val3[0] + val4[0]) / 2
                            else:
                                avg_sap = None

                            if val5.size > 0 and val6.size > 0:
                                avg_ss_left = (val5[0] + val6[0]) / 2
                            else:
                                avg_ss_left = None

                            if val7.size > 0 and val8.size > 0:
                                avg_ss_right = (val7[0] + val8[0]) / 2
                            else:
                                avg_ss_right = None

                            avg_ss = (avg_ss_left + avg_ss_right) / 2

                            results.append([name1, name2, avg_d, avg_sap, avg_ss])

                        # Save to Excel
                        pairs_df = pd.DataFrame(
                            results,
                            columns=[
                                "Measurement ID 1",
                                "Measurement ID 2",
                                "Average diameter (mm)",
                                "Average sapwood width (mm)",
                                "Average soft shell (mm)",
                            ],
                        )
                        output_path = os.path.join(
                            os.path.dirname(xls_pathname),
                            "Output_grouped_RPD_files.xlsx",
                        )
                        pairs_df.to_excel(output_path, index=False)

                except IOError:
                    wx.LogError("Cannot save current data in file '%s'." % xls_pathname)

            with wx.FileDialog(
                self,
                "Save output PDF file",
                defaultFile="Output.pdf",
                wildcard="PDF files (*.pdf)|*.pdf",
                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
            ) as fileDialog:

                if fileDialog.ShowModal() == wx.ID_CANCEL:
                    return  # the user changed their mind
                pdf_pathname = fileDialog.GetPath()
                try:

                    with PdfPages(pdf_pathname) as pdf:
                        for files in os.listdir(self.path_dir):
                            if files.endswith(".rgp"):

                                full_path = os.path.join(self.path_dir, files)
                                with open(full_path) as read_file:
                                    data = json.load(read_file)

                                # Retrieving data from the .rgp files
                                meas_year = data["header"]["dateYear"]
                                meas_month = data["header"]["dateMonth"]
                                meas_day = data["header"]["dateDay"]

                                drill_amp = np.array(data["profile"]["drill"])

                                resolution = data["header"]["resolutionFeed"]
                                depth = np.arange(0, len(drill_amp), 1) / resolution
                                threshold1 = 0.01 * np.average(drill_amp)

                                # removing too low values
                                filtered_signal = drill_amp[(drill_amp > threshold1)]
                                threshold_cut = (
                                    np.min(np.where(drill_amp > threshold1))
                                    / resolution
                                )

                                pile_signal = []

                                i = 0
                                while i < len(filtered_signal) - 25:
                                    window = filtered_signal[i : i + 25]
                                    if np.var(window) > 0.01:

                                        pile_signal.extend(window)
                                        i += 25
                                    else:
                                        i += 1

                                pile_signal.extend(filtered_signal[i:])

                                diameter = len(pile_signal) / resolution
                                drilldepth = (
                                    np.arange(0, len(pile_signal), 1) / resolution
                                )

                                # overlap original and cut signal

                                for p in range(len(drill_amp) - 25):
                                    window = drill_amp[p : p + 25]
                                    if np.var(window) > 0.01:
                                        overlap_position = p / resolution
                                        break

                                depth_overlap_position = max(
                                    threshold_cut, overlap_position
                                )

                                movav = np.empty(len(pile_signal), dtype=object)
                                for N in range(len(pile_signal)):
                                    i = N - 50
                                    j = N + 50
                                    k = 100
                                    if i < 0:
                                        i = 0
                                        j = N + 1
                                        k = j
                                    elif j > len(pile_signal):
                                        j = len(pile_signal)
                                        k = j - i

                                    movav[N] = sum(pile_signal[i:j]) / k
                                pile_signal1 = savgol_filter(pile_signal, 15, 11)
                                rings = round(
                                    len(
                                        find_peaks(
                                            pile_signal1, distance=0.1 * resolution
                                        )[0]
                                    )
                                    / 2,
                                    0,
                                )

                                pith = diameter / 2

                                rings_075_left = round(
                                    len(
                                        find_peaks(
                                            pile_signal1[
                                                int(0) : int(
                                                    0.75 * diameter / 2 * resolution
                                                )
                                            ],
                                            distance=0.1 * resolution,
                                        )[0]
                                    ),
                                    0,
                                )
                                rings_075_right = round(
                                    len(
                                        find_peaks(
                                            pile_signal1[
                                                int(
                                                    1.25 * diameter / 2 * resolution
                                                ) : int(diameter * resolution)
                                            ],
                                            distance=0.1 * resolution,
                                        )[0]
                                    ),
                                    0,
                                )

                                growth_rate = (
                                    (0.75 * diameter / 2) / rings_075_left
                                    + (0.75 * diameter / 2) / rings_075_right
                                ) / 2

                                sapwood = round(
                                    (37.17 * (growth_rate) ** 0.95)
                                    / (1 + 5.58 * np.exp(-0.054 * rings)),
                                    0,
                                )

                                ioma_left = []
                                ioma_right = []
                                array_movav = []
                                for i in reversed(movav[: int(pith * resolution)]):
                                    array_movav.append(i)
                                    ioma_left.append(
                                        sum(array_movav) / len(array_movav)
                                    )
                                    array_movav = []
                                for i in movav[int(pith * resolution) :]:
                                    array_movav.append(i)
                                    ioma_right.append(
                                        sum(array_movav) / len(array_movav)
                                    )
                                    ioma_left = list(reversed(ioma_left))

                                soft_shell_left = (
                                    np.min(np.where(movav > 0.4 * np.max(ioma_left)))
                                    / resolution
                                )
                                soft_shell_right = (
                                    np.max(np.where(movav > 0.4 * np.max(ioma_right)))
                                    / resolution
                                )

                                # plot graphs
                                figure = plt.figure(figsize=(10, 3))
                                # plot drilling resistance graph
                                axes = figure.add_subplot(
                                    121,
                                    title="%s - Drilling signal" % files,
                                    xlabel="Drilling depth (mm)",
                                    ylabel="Drilling resistance (%)",
                                )
                                axes.plot(
                                    depth - depth_overlap_position,
                                    drill_amp,
                                    color="grey",
                                    label="Drill (original signal)",
                                    linestyle="dotted",
                                )
                                axes.plot(
                                    drilldepth,
                                    pile_signal,
                                    color="blue",
                                    label="Drill (after cut-off)",
                                )
                                axes.plot(
                                    drilldepth,
                                    movav,
                                    color="red",
                                    label="Moving average",
                                )
                                axes.axvline(x=0, color="black", linestyle="dashed")
                                axes.axvline(
                                    x=diameter / 2,
                                    color="purple",
                                    linestyle="dashed",
                                    label="Center",
                                )
                                axes.axvline(
                                    x=diameter,
                                    color="black",
                                    linestyle="dashed",
                                    label="Estimated diameter (%.1f mm)" % diameter,
                                )
                                axes.axvline(
                                    x=sapwood,
                                    color="orange",
                                    linestyle="dashed",
                                    label="Estimated sapwood width (%.1f mm)" % sapwood,
                                )
                                axes.axvline(
                                    x=diameter - sapwood,
                                    color="orange",
                                    linestyle="dashed",
                                )
                                axes.axvline(
                                    x=soft_shell_left,
                                    color="green",
                                    linestyle="dashed",
                                    label="Soft shell (left %.1f mm, right %.1f mm)"
                                    % (soft_shell_left, diameter - soft_shell_right),
                                )
                                axes.axvline(
                                    x=soft_shell_right,
                                    color="green",
                                    linestyle="dashed",
                                )
                                axes.axvspan(0, diameter, color=(1, 0.7, 0.7))
                                axes.axvspan(
                                    soft_shell_left,
                                    soft_shell_right,
                                    color=(0.753, 1, 0.737),
                                )
                                axes.axvspan(
                                    sapwood,
                                    diameter - sapwood,
                                    color=(0.569, 0.71, 0.51),
                                )
                                axes.legend()
                                # plot polar graph
                                circle = figure.add_subplot(122, polar=True)
                                circle.set_title("%s - Cross section overview" % files)
                                circle.set_ylim(0, 200)
                                r_pile = diameter / 2
                                r_soft_left = diameter / 2 - soft_shell_left
                                r_soft_right = -diameter / 2 + soft_shell_right
                                r_sap = diameter / 2 - sapwood
                                theta = [0, np.pi, 0, 0]
                                width = [2 * np.pi, np.pi, np.pi, 2 * np.pi]
                                radii = [r_pile, r_soft_left, r_soft_right, r_sap]

                                bars = circle.bar(theta, radii, width=width, bottom=0.0)
                                for r, bar in zip(radii, bars):
                                    bars[0].set_facecolor((1, 0.7, 0.7))
                                    bars[0].set_label("Soft shell")
                                    bars[1].set_facecolor((0.753, 1, 0.737))
                                    bars[2].set_facecolor((0.753, 1, 0.737))
                                    bars[1].set_label("Sound cross section")
                                    bars[3].set_facecolor((0.569, 0.71, 0.51))
                                    bars[3].set_label("Estimated heartwood")

                                circle.set_xticklabels([])
                                circle.text(
                                    0,
                                    210,
                                    "Soft shell right (%.1f mm)"
                                    % (diameter - soft_shell_right),
                                    rotation=90,
                                    ha="center",
                                    va="center",
                                    fontsize=10,
                                )
                                circle.text(
                                    np.pi,
                                    210,
                                    "Soft shell left (%.1f mm)" % soft_shell_left,
                                    rotation=90,
                                    ha="center",
                                    va="center",
                                    fontsize=10,
                                )
                                circle.text(
                                    1.5 * np.pi,
                                    210,
                                    "Pile radius (%.1f mm)" % (diameter / 2),
                                    rotation=0,
                                    ha="center",
                                    va="center",
                                    fontsize=10,
                                )
                                circle.text(0, 0, "0")
                                circle.set_rlabel_position(270)
                                circle.legend(
                                    bbox_to_anchor=(0.85, 1.025), loc="upper left"
                                )
                                # show graph on user interface
                                figure.tight_layout()
                                #  self.canvas = FigureCanvas(self.graph, -1, self.figure)

                                # preparing pdf

                                pdf.savefig(
                                    figure
                                )  # saves the current figure into a pdf page
                                plt.close(figure)

                                self.statusbar.SetStatusText(
                                    "Generating output PDF file for directory '%s'"
                                    % self.path_dir
                                )

                    # pair RPD files if asked for
                    if self.check.GetValue() == True:

                        groupedPDF_path = os.path.join(
                            os.path.dirname(pdf_pathname),
                            "Output_grouped_RPD_files.PDF",
                        )
                        with PdfPages(groupedPDF_path) as pdf:

                            df = pd.read_excel(xls_pathname)
                            file_names = df["Measurement ID"].tolist()
                            similar_pairs = pair_similar_names(file_names)

                            # create list to store average values

                            for name1, name2 in similar_pairs:
                                val1 = df.loc[
                                    df["Measurement ID"] == name1,
                                    "Estimated diameter (mm)",
                                ].values
                                val2 = df.loc[
                                    df["Measurement ID"] == name2,
                                    "Estimated diameter (mm)",
                                ].values

                                val3 = df.loc[
                                    df["Measurement ID"] == name1,
                                    "Estimated sapwood width (mm)",
                                ].values
                                val4 = df.loc[
                                    df["Measurement ID"] == name2,
                                    "Estimated sapwood width (mm)",
                                ].values

                                val5 = df.loc[
                                    df["Measurement ID"] == name1,
                                    "Estimated soft shell left (mm)",
                                ].values
                                val6 = df.loc[
                                    df["Measurement ID"] == name2,
                                    "Estimated soft shell left (mm)",
                                ].values

                                val7 = df.loc[
                                    df["Measurement ID"] == name1,
                                    "Estimated soft shell right (mm)",
                                ].values
                                val8 = df.loc[
                                    df["Measurement ID"] == name2,
                                    "Estimated soft shell right (mm)",
                                ].values

                                # Ensure both values exist
                                if val1.size > 0 and val2.size > 0:
                                    avg_d = (val1[0] + val2[0]) / 2
                                else:
                                    avg_d = None

                                if val3.size > 0 and val4.size > 0:
                                    avg_sap = (val3[0] + val4[0]) / 2
                                else:
                                    avg_sap = None

                                if val5.size > 0 and val6.size > 0:
                                    avg_ss_left = (val5[0] + val6[0]) / 2
                                else:
                                    avg_ss_left = None

                                if val7.size > 0 and val8.size > 0:
                                    avg_ss_right = (val7[0] + val8[0]) / 2
                                else:
                                    avg_ss_right = None

                                avg_ss = (avg_ss_left + avg_ss_right) / 2

                                # plot graphs
                                figure = plt.figure(figsize=(10, 3))
                                # plot polar graph
                                circle = figure.add_subplot(111, polar=True)
                                circle.set_title(
                                    f"{name1} and {name2} - Cross section overview"
                                )
                                circle.set_ylim(0, 200)
                                r_pile_1 = val1[0] / 2
                                r_pile_2 = val2[0] / 2
                                r_soft_left_1 = r_pile_1 - val5[0]
                                r_soft_left_2 = r_pile_2 - val6[0]
                                r_soft_right_1 = r_pile_1 - val7[0]
                                r_soft_right_2 = r_pile_2 - val8[0]
                                r_sap_1 = r_pile_1 - val3[0]
                                r_sap_2 = r_pile_2 - val4[0]

                                theta = [
                                    5 * np.pi / 4,
                                    5 * np.pi / 4,
                                    np.pi / 4,
                                    np.pi / 4,
                                    5 * np.pi / 4,
                                    np.pi / 4,
                                    3 * np.pi / 4,
                                    3 * np.pi / 4,
                                    7 * np.pi / 4,
                                    7 * np.pi / 4,
                                    3 * np.pi / 4,
                                    7 * np.pi / 4,
                                ]
                                width = [
                                    0.5 * np.pi,
                                    0.5 * np.pi,
                                    0.5 * np.pi,
                                    0.5 * np.pi,
                                    0.5 * np.pi,
                                    0.5 * np.pi,
                                    0.5 * np.pi,
                                    0.5 * np.pi,
                                    0.5 * np.pi,
                                    0.5 * np.pi,
                                    0.5 * np.pi,
                                    0.5 * np.pi,
                                ]
                                radii = [
                                    r_pile_1,
                                    r_soft_left_1,
                                    r_pile_1,
                                    r_soft_right_1,
                                    r_sap_1,
                                    r_sap_1,
                                    r_pile_2,
                                    r_soft_left_2,
                                    r_pile_2,
                                    r_soft_right_2,
                                    r_sap_2,
                                    r_sap_2,
                                ]

                                bars = circle.bar(theta, radii, width=width, bottom=0.0)
                                for r, bar in zip(radii, bars):
                                    bars[0].set_facecolor((1, 0.7, 0.7))
                                    bars[2].set_facecolor((1, 0.7, 0.7))
                                    bars[6].set_facecolor((1, 0.7, 0.7))
                                    bars[8].set_facecolor((1, 0.7, 0.7))
                                    bars[0].set_label("Soft shell")
                                    bars[1].set_facecolor((0.753, 1, 0.737))
                                    bars[3].set_facecolor((0.753, 1, 0.737))
                                    bars[7].set_facecolor((0.753, 1, 0.737))
                                    bars[9].set_facecolor((0.753, 1, 0.737))
                                    bars[1].set_label("Sound cross section")
                                    bars[4].set_facecolor((0.569, 0.71, 0.51))
                                    bars[5].set_facecolor((0.569, 0.71, 0.51))
                                    bars[10].set_facecolor((0.569, 0.71, 0.51))
                                    bars[11].set_facecolor((0.569, 0.71, 0.51))
                                    bars[4].set_facecolor((0.569, 0.71, 0.51))
                                    bars[4].set_label("Estimated heartwood")

                                circle.set_xticklabels([])
                                circle.text(
                                    np.pi / 4,
                                    max(r_pile_1, r_pile_2)
                                    + 0.05 * max(r_pile_1, r_pile_2),
                                    f"{name1} - soft shell right = {val7[0]} mm, pile radius = {r_pile_1} mm, sapwood width = {val3[0]} mm",
                                    rotation=0,
                                    ha="left",
                                    va="center",
                                    fontsize=10,
                                )
                                circle.text(
                                    7 * np.pi / 4,
                                    max(r_pile_1, r_pile_2)
                                    + 0.05 * max(r_pile_1, r_pile_2),
                                    f"{name2} - soft shell right = {val8[0]} mm, pile radius = {r_pile_2} mm, sapwood width = {val4[0]} mm",
                                    rotation=0,
                                    ha="left",
                                    va="center",
                                    fontsize=10,
                                )
                                circle.text(
                                    3 * np.pi / 4,
                                    max(r_pile_1, r_pile_2)
                                    + 0.05 * max(r_pile_1, r_pile_2),
                                    f"{name2} - soft shell left = {val6[0]} mm, pile radius = {r_pile_2} mm, sapwood width = {val4[0]} mm",
                                    rotation=0,
                                    ha="right",
                                    va="center",
                                    fontsize=10,
                                )
                                circle.text(
                                    5 * np.pi / 4,
                                    max(r_pile_1, r_pile_2)
                                    + 0.05 * max(r_pile_1, r_pile_2),
                                    f"{name1} - soft shell left = {val5[0]} mm, pile radius = {r_pile_1} mm, sapwood width = {val3[0]} mm",
                                    rotation=0,
                                    ha="right",
                                    va="center",
                                    fontsize=10,
                                )

                                circle.text(0, 0, "0")
                                circle.set_rlabel_position(270)
                                circle.legend(
                                    bbox_to_anchor=(0.85, 1.025), loc="upper left"
                                )

                                figure.tight_layout()
                                pdf.savefig(
                                    figure
                                )  # saves the current figure into a pdf page
                                plt.close(figure)

                except IOError:
                    wx.LogError("Cannot save current data in file '%s'." % pdf_pathname)

            self.statusbar.SetStatusText(
                "Output for directory '%s' generated correctly." % self.path_dir
            )
            self.b3.Enable(False)
            self.check.SetValue(False)
            self.check.Enable(False)
            self.b1.Enable(True)

    def on_close(self, event):
        self.Destroy()
        sys.exit(0)


app = wx.App(False)
frame = MainWindow(None, "Soft shell calculator")
frame.SetIcon(wx.Icon("Icon.ico"))
frame.Show()
app.MainLoop()
