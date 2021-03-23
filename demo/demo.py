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
def simulate(receiverCount, angularDist, scansNo, link, filteringA, gif_step):
    tomograf = ManyEmitterTomograf(receiverCount, angularDist, scansNo)
    if fnmatch(link, "*.jpg"):
        image = skimage.io.imread(link, as_gray=True)
        tomograf.load_image(image)
        sinogram = tomograf.construct_sinogram(filteringA)
        constructedImage, ms, gif = tomograf.construct_image(gif_step=gif_step)
        return image, sinogram, constructedImage, ms, "", gif

    else:
        ds = dcmread(link)
        image = ds.pixel_array
        tomograf.load_image(image)
        sinogram = tomograf.construct_sinogram(filteringA)
        constructedImage, ms, gif = tomograf.construct_image(gif_step=gif_step)
        return image, sinogram, constructedImage, ms, ds, gif


def makeDicom(image, filename, patientName, patientID, comms):
    file = open(filename + ".dcm", "wb")

    # From scratch
    ########################
    file_meta = FileMetaDataset()
    file_meta.FileMetaInformationGroupLength = 206
    file_meta.FileMetaInformationVersion = b'\x00\x01'
    file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.2'
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = '1.2.840.10008.1.2.1'
    file_meta.ImplementationClassUID = '1.2.826.0.1.3680043.8.498.1'
    file_meta.ImplementationVersionName = 'PYDICOM 2.0.0'
    file_meta.SourceApplicationEntityTitle = 'CLUNIE1'

    # Main data elements
    ds = Dataset()
    ds.SpecificCharacterSet = 'ISO_IR 100'
    ds.ImageType = ['ORIGINAL', 'PRIMARY', 'AXIAL']
    ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.2'
    ds.SOPInstanceUID = '1.2.826.0.1.3680043.8.498.85187553111147486799609087725966020886'
    ds.Modality = 'CT'
    ds.StudyInstanceUID = '1.2.826.0.1.3680043.8.498.83372727452805475953983834969996366401'
    ds.SeriesInstanceUID = '1.2.826.0.1.3680043.8.498.20930702201105245310253873616838208732'
    ds.InstanceNumber = "1"
    ds.FrameOfReferenceUID = '1.2.826.0.1.3680043.8.498.22208733695040770099055783779457592590'
    ds.ImagesInAcquisition = "1"
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = 'MONOCHROME2'
    ds.BitsAllocated = 8
    ds.BitsStored = 8
    ds.HighBit = 7
    ds.PixelRepresentation = 0

    savedImg = image / np.max(image) * (256 - 1)
    savedImg[savedImg < 0] = 0
    savedImg = savedImg.astype(np.uint8)

    ds.PixelData = savedImg
    ds.Rows = savedImg.shape[0]
    ds.Columns = savedImg.shape[1]

    ds.PatientName = patientName
    ds.PatientID = patientID
    ds.ImageComments = comms

    dt = datetime.datetime.now()
    ds.ContentDate = dt.strftime('%Y%m%d')
    timeStr = dt.strftime('%H%M%S.%f')  # long format with micro seconds
    ds.ContentTime = timeStr

    ds.file_meta = file_meta
    ds.is_implicit_VR = False
    ds.is_little_endian = True
    ds.save_as(file, write_like_original=False)

    print("File saved.")
    file.close()


st.title("Tomograf")
st.sidebar.title('Options')
receiver_count = st.sidebar.number_input('Receiver Count', value=180, min_value=1, max_value=720)
angular_dist = st.sidebar.number_input('Angular Distance', value=180, min_value=1, max_value=720)
scans_no = st.sidebar.number_input('Scans number', value=180, min_value=1, max_value=720)
filtering = st.sidebar.checkbox('Use basic filter?', value=True)
gifStep = st.sidebar.number_input('Step', value=10, min_value=1, max_value=500)

dir = [
    "."
]
link = st.selectbox("Dej linka", findJPG(dir))

image, sinogram, constructedImage, ms, dsOld, gifOld = simulate(receiver_count, angular_dist,
                                                                scans_no, link, filtering, gifStep)

dsNew = copy.deepcopy(dsOld)
gif = copy.deepcopy(gifOld)

if not isinstance(dsNew, str):
    patientName = copy.deepcopy(dsNew.PatientName)
    patientID = copy.deepcopy(dsNew.PatientID)
    comms = copy.deepcopy(dsNew.ImageComments)
else:
    patientName = ""
    patientID = ""
    comms = ""

patientName = st.text_input('Imie i nazwisko', value=patientName)
patientID = st.text_input('Id', value=patientID)
comms = st.text_input('Komentarz ', value=comms)

st.write("min: {}, max: {}".format(np.min(image), np.max(image)))
col1, col2, col3, col4 = st.beta_columns(4)

with col1:
    st.header("Initial image")
    st.image(image, use_column_width=True, clamp=True)
with col2:
    st.header("Sinogram")
    st.image(sinogram, use_column_width=True, clamp=True)
with col3:
    st.header("Progress")
    s = st.slider('Progress?', 0, len(gif) - 1, 0)
    st.image(gif[s], use_column_width=True, clamp=True)
with col4:
    st.header("Processed image")
    st.image(constructedImage, use_column_width=True, clamp=True)
st.write("MSE: {}".format(ms))

filename = st.text_input('Nazwa pliku ')

if st.button("Save to file"):
    makeDicom(constructedImage, filename, patientName, patientID, comms)
