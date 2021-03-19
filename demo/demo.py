import copy
import sys
import os
import skimage.io
from pydicom import dcmread, uid
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
import datetime
from fnmatch import fnmatch

from pydicom.uid import generate_uid

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))

from tomograf.tomograf import *
import streamlit as st


@st.cache
def findJPG(comp):
    found = []
    for directory_in_str in comp:
        directory = os.fsencode(directory_in_str)
        for path, _, files in os.walk(directory):
            for name in files:
                if fnmatch(name.decode("utf-8"), "*.jpg") or fnmatch(name.decode("utf-8"), "*.dcm"):
                    found.append(os.path.join(path, name).decode("utf-8"))

    return found


@st.cache
def simulate(receiverCount, angularDist, scansNo, link, filteringA):

    tomograf = ManyEmitterTomograf(receiverCount, angularDist, scansNo)
    imie_pacjenta = ""
    id_pacjenta = ""
    comms = ""
    if fnmatch(link, "*.jpg"):
        image = skimage.io.imread(link, as_gray=True)

    else:
        ds = dcmread(link)
        image = ds.pixel_array
        imie_pacjenta = ds.PatientName
        id_pacjenta = ds.PatientID
        comms = ds.ImageComments

    tomograf.load_image(image)
    sinogram = tomograf.construct_sinogram(filteringA)
    constructedImage, ms, gif = tomograf.construct_image()
    return image, sinogram, constructedImage, ms, ds, gif

st.title("Tomograf")
st.sidebar.title('Options')
receiver_count = st.sidebar.number_input('Receiver Count', value=180, min_value=1, max_value=360)
angular_dist = st.sidebar.number_input('Angular Distance', value=180, min_value=1, max_value=360)
scans_no = st.sidebar.number_input('Scans number', value=380, min_value=1, max_value=500)
filtering = st.sidebar.checkbox('Use basic filter?', value=True)
gifStep = st.sidebar.number_input('Step', value=10, min_value=1, max_value=500)

dir = [
    "."
]
link = st.selectbox("Dej linka", findJPG(dir))

image, sinogram, constructedImage, ms, dsOld, gifOld = simulate(receiver_count, angular_dist,
                                                                                   scans_no,
                                                                                   link, filtering)
patientName = copy.deepcopy(dsOld.PatientName)
patientID = copy.deepcopy(dsOld.PatientID)
comms = copy.deepcopy(dsOld.ImageComments)
gif = copy.deepcopy(gifOld)
gif = gif[::gifStep]

patientName = st.text_input('Imie i nazwisko', value=patientName)
patientID = st.text_input('Id', value=patientID)
comms = st.text_input('Komentarz ', value=comms)

col1, col2, col3,col4 = st.beta_columns(4)
with col1:
    st.header("Initial image")
    st.image(image, use_column_width=True)
with col2:
    st.header("Sinogram")
    st.image(sinogram, use_column_width=True)
with col3:
    st.header("Progress")
    s = st.slider('Progress?', 0, len(gif) - 1, 0)
    st.image(gif[s], use_column_width=True)
with col4:
    st.header("Processed image")
    st.image(constructedImage, use_column_width=True)
st.write("MSE: {}".format(ms))

filename = st.text_input('Nazwa pliku ')

if st.button("Save to file"):
    file = open(filename + ".dcm", "wb")

    #From scratch
    # Populate required values for file meta information
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.2'

    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.ImplementationClassUID = '1.2.826.0.1.3680043.8.498.'

    file_meta.ImplementationVersionName = "PYDICOM 2.0.0"
    file_meta.FileMetaInformationGroupLength = 206

    ds = FileDataset(file, {}, file_meta=file_meta, preamble=b"\0" * 128)

    ds.PatientName = patientName
    ds.PatientID = patientID
    ds.ImageComments = comms
    ds.file_meta.TransferSyntaxUID = uid.ImplicitVRLittleEndian
    ds.PixelData = bytes(image)
    ds.PixelRepresentation = dsOld.PixelRepresentation
    ds.BitsAllocated = dsOld.BitsAllocated
    ds.Rows = dsOld.Rows
    ds.Columns = dsOld.Columns
    ds.SamplesPerPixel = dsOld.SamplesPerPixel
    ds.PhotometricInterpretation = dsOld.PhotometricInterpretation
    # Set the transfer syntax
    ds.is_little_endian = True
    ds.is_implicit_VR = True

    #with template

    #ds = copy.deepcopy(dsOld)
    #ds.PatientName = patientName
    #ds.PatientID = patientID
    #ds.ImageComments = comms


    # Set creation date/time
    dt = datetime.datetime.now()
    ds.ContentDate = dt.strftime('%Y%m%d')
    timeStr = dt.strftime('%H%M%S.%f')  # long format with micro seconds
    ds.ContentTime = timeStr

    ds.save_as(file)
    print("File saved.")
    file.close()
