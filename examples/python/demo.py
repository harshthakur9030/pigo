from ctypes import *

import subprocess
import numpy
import os
import cv2
import time

os.system('go build -o pigo.so -buildmode=c-shared pigo.go')
pigo = cdll.LoadLibrary('./pigo.so')
os.system('rm pigo.so')

MAX_NDETS = 2048

# define class GoPixelSlice to map to:
# C type struct { void *data; GoInt len; GoInt cap; }
class GoPixelSlice(Structure):
	_fields_ = [
		("pixels", POINTER(c_ubyte)), ("len", c_longlong), ("cap", c_longlong),
	]

def process_frame(pixs):
	dets = numpy.zeros(3*MAX_NDETS, dtype=numpy.float32)
	pixs = pixs.flatten()
	pixels = cast((c_ubyte * len(pixs))(*pixs), POINTER(c_ubyte))
	
	# call FindFaces
	faces = GoPixelSlice(pixels, len(pixs), len(pixs))
	pigo.FindFaces.argtypes = [GoPixelSlice]
	pigo.FindFaces.restype = c_void_p

	# Call the exported FindFaces function from Go. 
	ndets = pigo.FindFaces(faces)
	data_pointer = cast(ndets, POINTER((c_longlong * 3) * MAX_NDETS))
	
	if data_pointer :
		buffarr = ((c_longlong * 3) * MAX_NDETS).from_address(addressof(data_pointer.contents))
		res = numpy.ndarray(buffer=buffarr, dtype=c_longlong, shape=(MAX_NDETS, 3,))

		# The first value of the buffer aray represents the buffer length.
		dets_len = res[0][0]
		res = numpy.delete(res, 0, 0) # delete the first element from the array
		dets = list(res.reshape(-1, 3))[0:dets_len]

		return dets

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

while(True):
	ret, frame = cap.read()
	pixs = numpy.ascontiguousarray(frame[:, :, 1].reshape((frame.shape[0], frame.shape[1])))

	# Check if camera is intialized by checking if pixel array is not empty.
	if not numpy.any(pixs):
		continue

	dets = process_frame(pixs) # pixs needs to be numpy.uint8 array
	if dets is not None:
		for det in dets:
			cv2.circle(frame, (int(det[1]), int(det[0])), int(det[2]/2.0), (0, 0, 255), 2)

	cv2.imshow('', frame)
	
	if cv2.waitKey(5) & 0xFF == ord('q'):
		break

cap.release()
cv2.destroyAllWindows()