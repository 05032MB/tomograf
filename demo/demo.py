from ..tomograf.tomograf import *
from skimage import io
import numpy as np
import matplotlib.pyplot as plt
import time

start = time.time()

tomograf = ManyEmitterTomograf(receiver_count=180, angular_dist=180, scans_no=380)
#tomograf.setAngle(89)

#tomograf.dbg_print_rc_em(10, 0, 0)
#print(tomograf)

img = skimage.io.imread("tomograf/test/Kwadraty2.jpg", as_gray=True)

tomograf.load_image(img)

fig, (sino, recon) = plt.subplots(1, 2)
sino.imshow(np.array(tomograf.construct_sinogram()), cmap='gray')
recon.imshow(np.array(tomograf.construct_image()), cmap='gray')

end = time.time()
print("Wall time " + str(end - start))
plt.show()
