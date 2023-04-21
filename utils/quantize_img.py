import cv2
import numpy as np
from time import time

# Load image
img: np.ndarray = cv2.imread('storage/dcim/Tasker/TMC/new.jpg')

# convert to grayscale
img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# rotate to portrait if necessary
img_aspect_ratio = img.shape[0] / img.shape[1]
if img_aspect_ratio < 1:
    img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)

# calculate resize scale
pico_shape = [264,176]
pico_dim = [176,264]
pico_aspect_ratio = pico_shape[0] / pico_shape[1] # 1.5
scale = None
if img_aspect_ratio > pico_aspect_ratio: # img is taller
    scale = pico_shape[0] / img.shape[0]
else: # img is wider
    scale = pico_shape[1] / img.shape[1]

# resize image and preserve aspect ratio
new_shape = [round(i * scale) for i in img.shape[:2]]
new_shape.reverse()
img = cv2.resize(img, new_shape, interpolation=cv2.INTER_AREA)

# add black borders to fit pico display
if img_aspect_ratio > pico_aspect_ratio: # img is taller
    border = (pico_shape[0] - img.shape[0]) // 2
    img = cv2.copyMakeBorder(img, 0, 0, border, border, cv2.BORDER_CONSTANT, value=0)
else: # img is wider
    border = (pico_shape[0] - img.shape[0]) // 2
    img = cv2.copyMakeBorder(img, border, border, 0, 0, cv2.BORDER_CONSTANT, value=0)

# resize one more time in case rounding messed it up
img = cv2.resize(img, pico_dim, interpolation=cv2.INTER_AREA)
# cv2.imwrite('storage/dcim/Tasker/resized.jpg', img)

# normalize image values to take full dynamic range
img = img - img.min()
img = img * (255 / img.max())

# quantize image
img = img // 64
img = img.astype(np.uint8)
# print(np.unique(img, return_counts=True))

# for previewing
if 1:
    preview = img * 64
    preview = preview * (255 / 192)
    cv2.imwrite('storage/dcim/Tasker/TMC/quantized_preview.jpg', preview)

# write img to file as raw bytes
with open('storage/dcim/Tasker/TMC/img_bytes', 'wb') as f:
    # 264*176 = 46464 pixels
    # 92928 bits = 11616 bytes if using 2 bits per pixel
    # max python int size is 4 bytes = 32 bits
    # but we want to avoid int overflow bugs which will corrupt data
    # so we can work in 16 bit chunks, which is 8 pixels at a time
    chunk_size = 8
    img = img.reshape((-1, chunk_size))
    for i in range(img.shape[0]):
        binary_sum = 0
        for j in range(chunk_size):
            if j > 0:
                binary_sum <<= 2
            binary_sum += img[i][j]
        binary_sum = int(binary_sum)
        # print(binary_sum)
        # print(bin(binary_sum)[2:].rjust(16, "0"))
        sum_bytes = binary_sum.to_bytes(length=2, signed=False)
        f.write(sum_bytes)